import paho.mqtt.client as mqtt
import ssl
import json
import time

# MQTT Broker Configuration
MQTT_BROKER = "10.104.1.89"
MQTT_PORT = 1883
#MQTT_USERNAME = "CyberHunter"
#MQTT_PASSWORD = "Kullanici01"

# Emir'in dinleyeceği komut kanalı (Topic)
MQTT_TOPIC_COMMAND = "devices/esp32-led-01/command"

print("🚀 Tetikleyici başlatılıyor...")

# İstemciyi (Client) oluştur ve güvenlik ayarlarını yap
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2, "CyberHunter_Tetikleyici")
client.tls_set(tls_version=ssl.PROTOCOL_TLS_CLIENT)
#client.username_pw_set(MQTT_USERNAME, MQTT_PASSWORD)

# Sunucuya bağlan
print("⏳ HiveMQ postanemize bağlanılıyor...")
client.connect(MQTT_BROKER, MQTT_PORT, 60)

# Arka planda haberleşme motorunu başlat
client.loop_start()

# Bağlantının tam oturması için 2 saniye bekle
time.sleep(2)

# --- GÖNDERİLECEK EMİR (JSON FORMATINDA) ---
komut_paketi = {
    "aksiyon": "fiziksel_mudahale",
    "led": "red",
    "durum": "acik",
    "sistem_mesaji": "Kritik Tehdit Algılandı! Sistemi Kilitle."
}

# Sinyali Fırlat!
print(f"📡 '{MQTT_TOPIC_COMMAND}' kanalına emir fırlatılıyor...")
client.publish(MQTT_TOPIC_COMMAND, json.dumps(komut_paketi))
print("✅ Sinyal başarıyla gönderildi! (Emir'in kodları doğruysa kırmızı LED şu an yandı)")

# İşlem bitti, motoru durdur ve postanedeki bağlantıyı kes
time.sleep(1)
client.loop_stop()
client.disconnect()
print("🔌 Görev tamamlandı, bağlantı kapatıldı.")