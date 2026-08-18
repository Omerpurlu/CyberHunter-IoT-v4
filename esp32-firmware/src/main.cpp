#include <Arduino.h>
#include <WiFi.h>
#include <WiFiClient.h>
#include <HTTPClient.h>
#include <Preferences.h>
#include <mbedtls/md.h>
#include <sys/time.h>
#include "secrets.h"
#include "heartbeat_client.h"
#include "response_action_client.h"

constexpr int BUTTON = 18, BLUE = 4, RED = 5, GREEN = 19;
const char *WIFI = WIFI_SSID, *ID = DEVICE_ID;
const char *SECRET = DEVICE_SECRET;

// Backend bilgisayarının yerel ağ adresi ve portu.
const char *STATE = "http://10.143.203.195:5000/api/iot/led-state";
const char *COMMAND = "http://10.143.203.195:5000/api/iot/commands/pending/esp32-led-01";
const char *COMPLETE = "http://10.143.203.195:5000/api/iot/commands/complete/";

volatile bool red = true, dirty = true;
volatile uint32_t nextTry = 0;
bool lastButton = HIGH;
uint32_t lastPress = 0, sequence = 0;
Preferences prefs;

String u64(uint64_t n)
{
    char b[24];
    snprintf(b, sizeof(b), "%llu", (unsigned long long)n);
    return b;
}

String sign(const String &s)
{
    byte out[32];
    char hex[65];
    auto *info = mbedtls_md_info_from_type(MBEDTLS_MD_SHA256);
    mbedtls_md_hmac(info, (const byte *)SECRET, strlen(SECRET), (const byte *)s.c_str(), s.length(), out);
    for (int i = 0; i < 32; i++)
        sprintf(hex + i * 2, "%02x", out[i]);
    hex[64] = 0;
    return hex;
}

String value(const String &json, const String &key)
{
    int p = json.indexOf("\"" + key + "\"");
    if (p < 0)
        return "";
    p = json.indexOf(':', p) + 1;
    if (!p || p >= json.length())
        return "";
    while (p < json.length() && json[p] == ' ')
        p++;
    if (json[p] == '"')
    {
        int e = json.indexOf('"', p + 1);
        return e < 0 ? "" : json.substring(p + 1, e);
    }
    int e = json.indexOf(',', p);
    if (e < 0)
        e = json.indexOf('}', p);
    return e < 0 ? "" : json.substring(p, e);
}

void setLed(bool r)
{
    red = r;
    digitalWrite(RED, r);
    digitalWrite(BLUE, !r);
}

void changed()
{
    dirty = true;
    nextTry = 0;
}

bool sendState(bool state)
{
    timeval tv;
    gettimeofday(&tv, nullptr);
    if (WiFi.status() != WL_CONNECTED || tv.tv_sec < 1700000000)
        return false;
    String led = state ? "red" : "blue", ts = u64((uint64_t)tv.tv_sec * 1000ULL + tv.tv_usec / 1000ULL);
    String nonce = String((uint32_t)esp_random(), HEX);
    uint32_t seq = sequence + 1;
    String raw = String(ID) + "|" + led + "|" + seq + "|" + ts + "|" + nonce;
    String body = String("{\"deviceId\":\"") + ID + "\",\"led\":\"" + led + "\",\"sequence\":" + String(seq) +
                  ",\"timestamp\":" + ts + ",\"nonce\":\"" + nonce + "\",\"signature\":\"" + sign(raw) + "\"}";

    WiFiClient c;
    HTTPClient h;
    h.setTimeout(5000);
    if (!h.begin(c, STATE))
        return false;
    h.addHeader("Content-Type", "application/json");
    h.addHeader("X-Device-Id", ID);
    int code = h.POST(body);
    h.end();
    Serial.printf("STATE %s | HTTP %d | SEQ %lu\n", led.c_str(), code, (unsigned long)seq);
    if (code < 200 || code >= 300)
        return false;
    sequence = seq;
    prefs.putULong("sequence", sequence);
    return true;
}

void complete(const String &id)
{
    String body = String("{\"device_id\":\"") + ID + "\"}";

    WiFiClient c;
    HTTPClient h;
    h.setTimeout(5000);
    if (!h.begin(c, String(COMPLETE) + id))
        return;
    h.addHeader("Content-Type", "application/json");
    h.addHeader("X-Device-Id", ID);
    h.addHeader("X-Signature", sign(body));
    int code = h.POST(body);
    h.end();
    Serial.printf("COMPLETE %s | HTTP %d\n", id.c_str(), code);
}

void checkCommand()
{
    WiFiClient c;
    HTTPClient h;
    h.setTimeout(3000);
    if (!h.begin(c, COMMAND))
        return;
    h.addHeader("X-Device-Id", ID);
    h.addHeader("X-Signature", sign(ID));
    int code = h.GET();
    if (code != 200)
    {
        h.end();
        return;
    }
    String json = h.getString();
    h.end();
    if (json == "null" || json.length() < 3)
        return;
    String id = value(json, "id"), cmd = value(json, "komut");
    bool target;
    if (cmd == "KIRMIZI_YAK")
        target = true;
    else if (cmd == "MAVI_YAK")
        target = false;
    else
        return;
    if (red != target)
    {
        setLed(target);
        changed();
    }
    complete(id);
}

void network(void *)
{
    uint32_t poll = 0;
    bool online = false;
    for (;;)
    {
        bool ok = WiFi.status() == WL_CONNECTED;
        digitalWrite(GREEN, ok);
        if (!ok)
        {
            online = false;
            vTaskDelay(pdMS_TO_TICKS(100));
            continue;
        }
        if (!online)
        {
            online = true;
            changed();
            Serial.println("WiFi baglandi");
        }
        if (dirty && (nextTry == 0 || (int32_t)(millis() - nextTry) >= 0))
        {
            bool sent = red;
            if (sendState(sent))
            {
                if (red == sent)
                    dirty = false;
                else
                    nextTry = 0;
            }
            else
                nextTry = millis() + 3000;
        }

        if (millis() - poll >= 100)
        {
            poll = millis();
            checkCommand();
            responseActionClientPoll();
        }
        vTaskDelay(pdMS_TO_TICKS(10));
    }
}

void setup()
{
    Serial.begin(115200);
    prefs.begin("iot", false);
    sequence = prefs.getULong("sequence", 0);
    if (sequence < 46)
    {
        sequence = 46;
        prefs.putULong("sequence", 46);
    }
    pinMode(BUTTON, INPUT_PULLUP);
    pinMode(BLUE, OUTPUT);
    pinMode(RED, OUTPUT);
    pinMode(GREEN, OUTPUT);
    setLed(true);
    WiFi.mode(WIFI_STA);
    WiFi.setAutoReconnect(true);
    WiFi.begin(WIFI);
    configTime(0, 0, "pool.ntp.org", "time.google.com");
    heartbeatClientBegin();
    responseActionClientBegin();
    xTaskCreatePinnedToCore(network, "Network", 8192, nullptr, 1, nullptr, 0);
}

void loop()
{
    bool b = digitalRead(BUTTON);
    if (lastButton && !b && millis() - lastPress >= 35)
    {
        lastPress = millis();
        setLed(!red);
        changed();
    }
    lastButton = b;
}
