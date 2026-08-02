#pragma once

#define WIFI_SSID "YOUR_WIFI_SSID"
#define DEVICE_ID "esp32-cyberhunter-01"
#define DEVICE_SECRET "CHANGE_ME"
#define API_BASE_URL "https://example.ngrok-free.app"
#define FIRMWARE_VERSION "1.0.0"

// Keep false outside explicitly controlled development environments.
#define ALLOW_INSECURE_TLS false

// Configure a trusted PEM root CA when insecure development mode is disabled.
#define TLS_ROOT_CA ""
