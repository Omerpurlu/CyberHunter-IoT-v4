#include "heartbeat_client.h"

#include <HTTPClient.h>
#include <Preferences.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <esp_sntp.h>
#include <sys/time.h>

#include "secrets.h"

namespace
{
constexpr uint32_t HEARTBEAT_INTERVAL_MS = 10000;
constexpr uint32_t HTTP_TIMEOUT_MS = 5000;
constexpr uint32_t INITIAL_RETRY_MS = 1000;
constexpr uint32_t MAX_RETRY_MS = 8000;
constexpr uint32_t CHECKPOINT_INTERVAL_MS = 600000;
constexpr uint16_t CHECKPOINT_SUCCESS_COUNT = 60;
constexpr uint32_t HEARTBEAT_TASK_STACK = 12288;

String heartbeatUrl;
String pendingPayload;
int64_t lastSequence = 0;
int64_t pendingSequence = 0;
uint32_t nextActionAt = 0;
uint32_t lastCheckpointAt = 0;
uint16_t acceptedSinceCheckpoint = 0;
uint8_t retryCount = 0;

bool due(uint32_t target)
{
    return target == 0 || static_cast<int32_t>(millis() - target) >= 0;
}

String int64String(int64_t value)
{
    char buffer[24];
    snprintf(buffer, sizeof(buffer), "%lld", static_cast<long long>(value));
    return String(buffer);
}

String jsonEscape(const String &value)
{
    String escaped;
    escaped.reserve(value.length() + 8);
    for (size_t index = 0; index < value.length(); ++index)
    {
        const uint8_t byteValue = static_cast<uint8_t>(value[index]);
        switch (byteValue)
        {
        case '"':
            escaped += "\\\"";
            break;
        case '\\':
            escaped += "\\\\";
            break;
        case '\b':
            escaped += "\\b";
            break;
        case '\f':
            escaped += "\\f";
            break;
        case '\n':
            escaped += "\\n";
            break;
        case '\r':
            escaped += "\\r";
            break;
        case '\t':
            escaped += "\\t";
            break;
        default:
            if (byteValue < 0x20)
            {
                char unicodeEscape[7];
                snprintf(unicodeEscape, sizeof(unicodeEscape), "\\u%04x", byteValue);
                escaped += unicodeEscape;
            }
            else
            {
                escaped += static_cast<char>(byteValue);
            }
        }
    }
    return escaped;
}

bool validateAndBuildEndpoint()
{
    String base = API_BASE_URL;
    base.trim();
    String lower = base;
    lower.toLowerCase();
    if (base.length() == 0 || !lower.startsWith("https://") ||
        lower.indexOf("localhost") >= 0 || lower.indexOf("127.0.0.1") >= 0)
    {
        Serial.println("HEARTBEAT disabled: invalid HTTPS API base URL");
        return false;
    }
    while (base.endsWith("/"))
        base.remove(base.length() - 1);
    const String endpoint = "/api/system/heartbeat";
    heartbeatUrl = base.endsWith(endpoint) ? base : base + endpoint;
    return true;
}

bool validateTlsConfiguration()
{
    if (ALLOW_INSECURE_TLS)
    {
        Serial.println("HEARTBEAT WARNING: development TLS mode");
        return true;
    }
    if (strlen(TLS_ROOT_CA) == 0)
    {
        Serial.println("HEARTBEAT disabled: TLS CA not configured");
        return false;
    }
    return true;
}

bool readValidatedUtc(timeval &currentTime, tm &utc)
{
    if (sntp_get_sync_status() != SNTP_SYNC_STATUS_COMPLETED)
        return false;
    gettimeofday(&currentTime, nullptr);
    const time_t seconds = currentTime.tv_sec;
    gmtime_r(&seconds, &utc);
    const int year = utc.tm_year + 1900;
    return year >= 2024 && year <= 2100;
}

int64_t epochMilliseconds(const timeval &currentTime)
{
    return static_cast<int64_t>(currentTime.tv_sec) * 1000LL + currentTime.tv_usec / 1000LL;
}

int64_t nextSequence(int64_t epochMs)
{
    int64_t sequence = epochMs;
    if (sequence <= lastSequence)
        sequence = lastSequence + 1;
    return sequence;
}

void loadSequenceCheckpoint()
{
    Preferences preferences;
    if (!preferences.begin("heartbeat", true))
    {
        Serial.println("HEARTBEAT NVS checkpoint unavailable");
        return;
    }
    if (preferences.isKey("sequence"))
    {
        const uint64_t stored = preferences.getULong64("sequence", 0);
        if (stored <= static_cast<uint64_t>(INT64_MAX))
            lastSequence = static_cast<int64_t>(stored);
        else
            Serial.println("HEARTBEAT NVS checkpoint invalid");
    }
    preferences.end();
}

void saveSequenceCheckpoint()
{
    Preferences preferences;
    if (!preferences.begin("heartbeat", false))
    {
        Serial.println("HEARTBEAT NVS checkpoint write unavailable");
        return;
    }
    const size_t written = preferences.putULong64("sequence", static_cast<uint64_t>(lastSequence));
    preferences.end();
    if (written != sizeof(uint64_t))
    {
        Serial.println("HEARTBEAT NVS checkpoint write failed");
        return;
    }
    acceptedSinceCheckpoint = 0;
    lastCheckpointAt = millis();
}

void checkpointIfDue()
{
    ++acceptedSinceCheckpoint;
    if (acceptedSinceCheckpoint >= CHECKPOINT_SUCCESS_COUNT ||
        static_cast<uint32_t>(millis() - lastCheckpointAt) >= CHECKPOINT_INTERVAL_MS)
        saveSequenceCheckpoint();
}

void createPendingHeartbeat(const timeval &currentTime, const tm &utc)
{
    pendingSequence = nextSequence(epochMilliseconds(currentTime));
    char timestamp[25];
    strftime(timestamp, sizeof(timestamp), "%Y-%m-%dT%H:%M:%SZ", &utc);
    pendingPayload = String("{\"component_type\":\"esp32\",\"component_id\":\"") +
                     jsonEscape(DEVICE_ID) + "\",\"reported_status\":\"healthy\",\"sequence\":" +
                     int64String(pendingSequence) +
                     ",\"reported_by\":\"esp32-firmware\",\"software_version\":\"" +
                     jsonEscape(FIRMWARE_VERSION) + "\",\"device_timestamp\":\"" + timestamp +
                     "\",\"metadata\":{\"uptime_ms\":" + int64String(millis()) +
                     ",\"free_heap\":" + int64String(ESP.getFreeHeap()) +
                     ",\"wifi_rssi\":" + String(WiFi.RSSI()) + "}}";
    lastSequence = pendingSequence;
    retryCount = 0;
}

void clearPendingHeartbeat()
{
    pendingPayload = "";
    pendingSequence = 0;
    retryCount = 0;
    nextActionAt = millis() + HEARTBEAT_INTERVAL_MS;
}

void scheduleRetry()
{
    const uint8_t shift = retryCount < 3 ? retryCount : 3;
    uint32_t backoff = INITIAL_RETRY_MS << shift;
    if (backoff > MAX_RETRY_MS)
        backoff = MAX_RETRY_MS;
    if (retryCount < 3)
        ++retryCount;
    nextActionAt = millis() + backoff;
}

void sendPendingHeartbeat()
{
    WiFiClientSecure client;
    if (ALLOW_INSECURE_TLS)
        client.setInsecure();
    else
        client.setCACert(TLS_ROOT_CA);

    HTTPClient request;
    request.setTimeout(HTTP_TIMEOUT_MS);
    if (!request.begin(client, heartbeatUrl))
    {
        Serial.printf("HEARTBEAT connection error | SEQ %s\n", int64String(pendingSequence).c_str());
        scheduleRetry();
        return;
    }
    request.addHeader("Content-Type", "application/json");
    const int statusCode = request.POST(pendingPayload);
    request.end();

    if (statusCode == 200 || statusCode == 201)
    {
        Serial.printf("HEARTBEAT accepted | HTTP %d | SEQ %s\n", statusCode, int64String(pendingSequence).c_str());
        checkpointIfDue();
        clearPendingHeartbeat();
        return;
    }
    if (statusCode == 409)
    {
        Serial.printf("HEARTBEAT sequence conflict | HTTP 409 | SEQ %s\n", int64String(pendingSequence).c_str());
        clearPendingHeartbeat();
        return;
    }
    Serial.printf("HEARTBEAT request failed | HTTP %d | SEQ %s\n", statusCode, int64String(pendingSequence).c_str());
    scheduleRetry();
}

void heartbeatTask(void *)
{
    for (;;)
    {
        if (WiFi.status() == WL_CONNECTED && due(nextActionAt))
        {
            if (pendingPayload.length() == 0)
            {
                timeval currentTime;
                tm utc;
                if (readValidatedUtc(currentTime, utc))
                    createPendingHeartbeat(currentTime, utc);
            }
            if (pendingPayload.length() > 0)
                sendPendingHeartbeat();
        }
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}
} // namespace

void heartbeatClientBegin()
{
    if (!validateAndBuildEndpoint() || !validateTlsConfiguration())
        return;
    loadSequenceCheckpoint();
    lastCheckpointAt = millis();
    const BaseType_t created = xTaskCreate(
        heartbeatTask,
        "Heartbeat",
        HEARTBEAT_TASK_STACK,
        nullptr,
        1,
        nullptr);
    if (created != pdPASS)
        Serial.println("HEARTBEAT task could not be started");
}
