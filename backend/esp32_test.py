import requests
import hmac
import hashlib
import time
import uuid

# --- BAĞLANTI BİLGİLERİ ---
URL = "http://192.168.137.248:8000/api/iot/led-state"
SECRET = "CyberHunter_2026_SecretKey!"

# --- SAHTE ESP32 VERİLERİ ---
device_id = "esp32-led-01"
led = "red"        # Test etmek istediğin LED rengi: "blue", "red", "off"
sequence = 1       # NOT: Her yeni testte bu sayıyı artırmalısın! (Örn: 2, 3, 4...)
timestamp = int(time.time() * 1000)  # Milisaniye cinsinden zaman damgası
nonce = uuid.uuid4().hex[:8]        # Tek kullanımlık 8 haneli rastgele kod

# 1. Sözleşmeye Uygun İmza Metnini Oluştur (deviceId|led|sequence|timestamp|nonce)
imzalanacak_metin = f"{device_id}|{led}|{sequence}|{timestamp}|{nonce}"

# 2. HMAC-SHA256 İmzasını Hesapla
signature = hmac.new(
    SECRET.encode('utf-8'),
    imzalanacak_metin.encode('utf-8'),
    hashlib.sha256
).hexdigest()

# 3. Gönderilecek JSON Paketini Hazırla
payload = {
    "deviceId": device_id,
    "led": led,
    "sequence": sequence,
    "timestamp": timestamp,
    "nonce": nonce,
    "signature": signature
}

print("📡 Sahte ESP32 verisi API kapısına fırlatılıyor...")
try:
    response = requests.post(URL, json=payload)
    print(f"Status Code: {response.status_code}")
    print("Server Response:", response.json())
except Exception as e:
    print(f"❌ Bağlantı hatası: {e}")
    