#include "response_action_client.h"

#include <Arduino.h>
#include <limits.h>
#include <HTTPClient.h>
#include <Preferences.h>
#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <esp_sntp.h>
#include <sys/time.h>

#include "secrets.h"

namespace
{
constexpr uint32_t POLL_INTERVAL_MS = 5000;
constexpr uint32_t HTTP_TIMEOUT_MS = 5000;
constexpr uint32_t INITIAL_ACK_RETRY_MS = 1000;
constexpr uint32_t MAX_ACK_RETRY_MS = 8000;
constexpr size_t MAX_RESPONSE_BYTES = 2048;
constexpr size_t MAX_COMMAND_ID_LENGTH = 64;
constexpr size_t MAX_EVENT_ID_LENGTH = 128;
constexpr size_t MAX_DEVICE_ID_LENGTH = 128;
constexpr size_t MAX_ACTION_LENGTH = 32;
constexpr size_t MAX_SEVERITY_LENGTH = 16;
constexpr size_t MAX_EXPIRES_AT_LENGTH = 40;

String nextCommandUrl;
String apiBaseUrl;
String lastCommandId;
String lastAckBody;
bool ackPending = false;
bool enabled = false;
uint8_t ackRetryCount = 0;
uint32_t nextActionAt = 0;

struct ResponseCommand
{
    String commandId;
    String eventId;
    String deviceId;
    String action;
    String severity;
    String expiresAt;
    int riskScore = -1;
    int policyVersion = 0;
};

bool due(uint32_t target)
{
    return target == 0 || static_cast<int32_t>(millis() - target) >= 0;
}

String jsonEscape(const String &value)
{
    String escaped;
    escaped.reserve(value.length() + 8);
    for (size_t index = 0; index < value.length(); ++index)
    {
        const char character = value[index];
        if (character == '"' || character == '\\')
            escaped += '\\';
        if (static_cast<uint8_t>(character) >= 0x20)
            escaped += character;
    }
    return escaped;
}

bool validateAndBuildEndpoints()
{
    String base = API_BASE_URL;
    base.trim();
    String lower = base;
    lower.toLowerCase();
    if (base.length() == 0 || !lower.startsWith("https://") ||
        lower.indexOf("localhost") >= 0 || lower.indexOf("127.0.0.1") >= 0)
    {
        Serial.println("[RESPONSE] Disabled: invalid HTTPS API base URL");
        return false;
    }
    while (base.endsWith("/"))
        base.remove(base.length() - 1);
    apiBaseUrl = base;
    nextCommandUrl = apiBaseUrl + "/api/iot/commands/next?device_id=" + DEVICE_ID;
    return true;
}

bool validateTlsConfiguration()
{
    if (ALLOW_INSECURE_TLS)
    {
        Serial.println("[RESPONSE] WARNING: development TLS mode");
        return true;
    }
    if (strlen(TLS_ROOT_CA) == 0)
    {
        Serial.println("[RESPONSE] Disabled: TLS CA not configured");
        return false;
    }
    return true;
}

void configureTls(WiFiClientSecure &client)
{
    if (ALLOW_INSECURE_TLS)
        client.setInsecure();
    else
        client.setCACert(TLS_ROOT_CA);
}

bool readUtcTimestamp(String &timestamp)
{
    if (sntp_get_sync_status() != SNTP_SYNC_STATUS_COMPLETED)
        return false;
    timeval currentTime;
    gettimeofday(&currentTime, nullptr);
    tm utc;
    const time_t seconds = currentTime.tv_sec;
    gmtime_r(&seconds, &utc);
    const int year = utc.tm_year + 1900;
    if (year < 2024 || year > 2100)
        return false;
    char buffer[25];
    strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%SZ", &utc);
    timestamp = buffer;
    return true;
}

bool locateValue(const String &json, const char *key, int &position)
{
    const String marker = String("\"") + key + "\"";
    position = json.indexOf(marker);
    if (position < 0)
        return false;
    position = json.indexOf(':', position + marker.length());
    if (position < 0)
        return false;
    ++position;
    while (position < static_cast<int>(json.length()) &&
           (json[position] == ' ' || json[position] == '\r' ||
            json[position] == '\n' || json[position] == '\t'))
        ++position;
    return position < static_cast<int>(json.length());
}

bool readJsonString(
    const String &json,
    const char *key,
    String &output,
    size_t maximumLength)
{
    int position;
    if (!locateValue(json, key, position) || json[position] != '"')
        return false;
    ++position;
    output = "";
    output.reserve(maximumLength);
    bool escaped = false;
    for (; position < static_cast<int>(json.length()); ++position)
    {
        const char character = json[position];
        if (escaped)
        {
            if (character != '"' && character != '\\' && character != '/')
                return false;
            output += character;
            escaped = false;
        }
        else if (character == '\\')
            escaped = true;
        else if (character == '"')
            return output.length() > 0 && output.length() <= maximumLength;
        else if (static_cast<uint8_t>(character) < 0x20)
            return false;
        else
            output += character;
        if (output.length() > maximumLength)
            return false;
    }
    return false;
}

bool readJsonInteger(const String &json, const char *key, int &output)
{
    int position;
    if (!locateValue(json, key, position))
        return false;
    bool negative = false;
    if (json[position] == '-')
    {
        negative = true;
        ++position;
    }
    if (position >= static_cast<int>(json.length()) || !isDigit(json[position]))
        return false;
    long value = 0;
    while (position < static_cast<int>(json.length()) && isDigit(json[position]))
    {
        value = value * 10 + (json[position] - '0');
        if (value > INT_MAX)
            return false;
        ++position;
    }
    output = negative ? -static_cast<int>(value) : static_cast<int>(value);
    return true;
}

bool parseCommand(const String &json, ResponseCommand &command)
{
    if (json.length() == 0 || json.length() > MAX_RESPONSE_BYTES)
        return false;
    return readJsonString(json, "command_id", command.commandId, MAX_COMMAND_ID_LENGTH) &&
           readJsonString(json, "event_id", command.eventId, MAX_EVENT_ID_LENGTH) &&
           readJsonString(json, "device_id", command.deviceId, MAX_DEVICE_ID_LENGTH) &&
           readJsonString(json, "action", command.action, MAX_ACTION_LENGTH) &&
           readJsonString(json, "severity", command.severity, MAX_SEVERITY_LENGTH) &&
           readJsonInteger(json, "risk_score", command.riskScore) &&
           readJsonString(json, "expires_at", command.expiresAt, MAX_EXPIRES_AT_LENGTH) &&
           readJsonInteger(json, "policy_version", command.policyVersion) &&
           command.riskScore >= 0 && command.riskScore <= 100 &&
           command.policyVersion > 0;
}

void loadPersistentState()
{
    Preferences preferences;
    if (!preferences.begin("response", true))
    {
        Serial.println("[RESPONSE] Preferences read unavailable");
        return;
    }
    lastCommandId = preferences.getString("last_cmd", "");
    lastAckBody = preferences.getString("last_ack", "");
    ackPending = preferences.getBool("ack_pending", false);
    preferences.end();
    if (ackPending && (lastCommandId.length() == 0 || lastAckBody.length() == 0))
    {
        Serial.println("[RESPONSE] Invalid pending ACK state ignored");
        ackPending = false;
        lastAckBody = "";
    }
}

bool saveProcessedCommand(const String &commandId, const String &ackBody)
{
    Preferences preferences;
    if (!preferences.begin("response", false))
        return false;
    const size_t commandBytes = preferences.putString("last_cmd", commandId);
    const size_t ackBytes = preferences.putString("last_ack", ackBody);
    const size_t pendingBytes = preferences.putBool("ack_pending", true);
    preferences.end();
    if (commandBytes == 0 || ackBytes == 0 || pendingBytes != sizeof(bool))
        return false;
    lastCommandId = commandId;
    lastAckBody = ackBody;
    ackPending = true;
    return true;
}

void markAckDelivered()
{
    Preferences preferences;
    if (preferences.begin("response", false))
    {
        preferences.putBool("ack_pending", false);
        preferences.end();
    }
    ackPending = false;
    ackRetryCount = 0;
    nextActionAt = millis() + POLL_INTERVAL_MS;
}

void scheduleAckRetry()
{
    const uint8_t shift = ackRetryCount < 3 ? ackRetryCount : 3;
    uint32_t backoff = INITIAL_ACK_RETRY_MS << shift;
    if (backoff > MAX_ACK_RETRY_MS)
        backoff = MAX_ACK_RETRY_MS;
    if (ackRetryCount < 3)
        ++ackRetryCount;
    nextActionAt = millis() + backoff;
    Serial.printf("[RESPONSE] ACK retry scheduled in %lu ms\n", static_cast<unsigned long>(backoff));
}

void sendStoredAck()
{
    WiFiClientSecure client;
    configureTls(client);
    HTTPClient request;
    request.setTimeout(HTTP_TIMEOUT_MS);
    const String url = apiBaseUrl + "/api/iot/commands/" + lastCommandId + "/ack";
    if (!request.begin(client, url))
    {
        Serial.println("[RESPONSE] ACK connection error");
        scheduleAckRetry();
        return;
    }
    request.addHeader("Content-Type", "application/json");
    // Production TODO: add device HMAC, timestamp, sequence and nonce headers.
    const int statusCode = request.POST(lastAckBody);
    request.end();
    if (statusCode == 200)
    {
        Serial.println("[RESPONSE] ACK gönderildi");
        markAckDelivered();
        return;
    }
    Serial.printf("[RESPONSE] ACK failed | HTTP %d\n", statusCode);
    scheduleAckRetry();
}

String buildAckBody(const char *result, const char *relayState, const char *message)
{
    String timestamp;
    if (!readUtcTimestamp(timestamp))
        return "";
    return String("{\"device_id\":\"") + jsonEscape(DEVICE_ID) +
           "\",\"result\":\"" + result + "\",\"executed_at\":\"" + timestamp +
           "\",\"relay_state\":\"" + relayState + "\",\"ack_message\":\"" +
           jsonEscape(message) + "\"}";
}

void handleCommand(const ResponseCommand &command)
{
    if (command.deviceId != DEVICE_ID)
    {
        Serial.println("[RESPONSE] Komut reddedildi: device_id uyuşmuyor");
        return;
    }
    if (command.commandId == lastCommandId)
    {
        Serial.println("[RESPONSE] Duplicate command_id; fiziksel işlem tekrarlanmadı");
        if (lastAckBody.length() > 0)
        {
            if (saveProcessedCommand(lastCommandId, lastAckBody))
                sendStoredAck();
            else
                Serial.println("[RESPONSE] Duplicate ACK state could not be persisted");
        }
        return;
    }

    Serial.println("[RESPONSE] Komut alındı");
    Serial.printf("[RESPONSE] command_id: %s\n", command.commandId.c_str());
    Serial.printf("[RESPONSE] event_id: %s\n", command.eventId.c_str());
    Serial.printf("[RESPONSE] action: %s\n", command.action.c_str());
    Serial.printf("[RESPONSE] severity: %s\n", command.severity.c_str());
    Serial.printf("[RESPONSE] risk_score: %d\n", command.riskScore);
    Serial.printf("[RESPONSE] expires_at: %s\n", command.expiresAt.c_str());
    Serial.printf("[RESPONSE] policy_version: %d\n", command.policyVersion);
    Serial.println("[RESPONSE] Expiry yalnız görüntülendi; yerel expiry kararı uygulanmadı");

    const bool supported = command.action == "isolate_device";
    if (supported)
        Serial.println("[RESPONSE] DRY-RUN: Fiziksel röle değiştirilmedi");
    else
        Serial.println("[RESPONSE] Bilinmeyen action uygulanmadı");

    const String ackBody = supported
                               ? buildAckBody(
                                     "executed",
                                     "simulated_isolated",
                                     "ESP32 dry-run command completed")
                               : buildAckBody(
                                     "failed",
                                     "not_changed",
                                     "Unsupported response action");
    if (ackBody.length() == 0)
    {
        Serial.println("[RESPONSE] UTC unavailable; command was not recorded or applied");
        nextActionAt = millis() + POLL_INTERVAL_MS;
        return;
    }
    // Persist before ACK: reboot/retry must never apply the same command twice.
    if (!saveProcessedCommand(command.commandId, ackBody))
    {
        Serial.println("[RESPONSE] Preferences write failed; command not acknowledged");
        nextActionAt = millis() + POLL_INTERVAL_MS;
        return;
    }
    sendStoredAck();
}

void pollNextCommand()
{
    String timestamp;
    if (!readUtcTimestamp(timestamp))
    {
        Serial.println("[RESPONSE] Poll deferred: reliable UTC unavailable");
        nextActionAt = millis() + POLL_INTERVAL_MS;
        return;
    }

    WiFiClientSecure client;
    configureTls(client);
    HTTPClient request;
    request.setTimeout(HTTP_TIMEOUT_MS);
    if (!request.begin(client, nextCommandUrl))
    {
        Serial.println("[RESPONSE] Poll connection error");
        nextActionAt = millis() + POLL_INTERVAL_MS;
        return;
    }
    // Production TODO: add device HMAC, timestamp, sequence and nonce headers.
    const int statusCode = request.GET();
    if (statusCode == 204)
    {
        request.end();
        Serial.println("[RESPONSE] Bekleyen response action yok");
        nextActionAt = millis() + POLL_INTERVAL_MS;
        return;
    }
    if (statusCode != 200)
    {
        request.end();
        Serial.printf("[RESPONSE] Poll failed | HTTP %d\n", statusCode);
        nextActionAt = millis() + POLL_INTERVAL_MS;
        return;
    }
    const int announcedSize = request.getSize();
    if (announcedSize > static_cast<int>(MAX_RESPONSE_BYTES))
    {
        request.end();
        Serial.println("[RESPONSE] Response body too large");
        nextActionAt = millis() + POLL_INTERVAL_MS;
        return;
    }
    const String body = request.getString();
    request.end();
    ResponseCommand command;
    if (!parseCommand(body, command))
    {
        Serial.println("[RESPONSE] Invalid command JSON");
        nextActionAt = millis() + POLL_INTERVAL_MS;
        return;
    }
    handleCommand(command);
}
} // namespace

void responseActionClientBegin()
{
    if (!validateAndBuildEndpoints() || !validateTlsConfiguration())
        return;
    if (strlen(DEVICE_ID) == 0 || strlen(DEVICE_ID) > MAX_DEVICE_ID_LENGTH)
    {
        Serial.println("[RESPONSE] Disabled: invalid DEVICE_ID length");
        return;
    }
    loadPersistentState();
    enabled = true;
    nextActionAt = 0;
    Serial.println("[RESPONSE] Dry-run response action client ready");
    Serial.println("[RESPONSE] HMAC/replay protection required before relay integration");
}

void responseActionClientPoll()
{
    if (!enabled || WiFi.status() != WL_CONNECTED || !due(nextActionAt))
        return;
    if (ackPending)
        sendStoredAck();
    else
        pollNextCommand();
}
