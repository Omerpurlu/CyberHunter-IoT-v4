import requests
import hmac
import hashlib
import time
import uuid
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

# --- BAĞLANTI BİLGİLERİ ---
API_BASE = os.getenv("CYBERHUNTER_API_URL", "http://10.104.1.89:8000")
URL = f"{API_BASE}/api/iot/led-state"
SECRET = os.getenv("DEVICE_SECRET")
if not SECRET:
    raise RuntimeError("Required environment variable is missing: DEVICE_SECRET")

# --- SAHTE ESP32 VERİLERİ ---
device_id = "esp32-led-01"
led = "red"        # Test etmek istediğin LED rengi: "blue", "red", "off"
sequence = 1       # NOT: Her yeni testte bu sayıyı artırmalısın! (Örn: 2, 3, 4...)
timestamp = int(time.time() * 1000)  # Milisaniye cinsinden zaman damgası
nonce = uuid.uuid4().hex[:8]        # Tek kullanımlık 8 haneli rastgele kod

# 1. Sözleşmeye uygun imza metnini oluştur (deviceId|led|sequence|timestamp|nonce)
imzalanacak_metin = f"{device_id}|{led}|{sequence}|{timestamp}|{nonce}"

# 2. HMAC-SHA256 imzasını hesapla
signature = hmac.new(
    SECRET.encode('utf-8'),
    imzalanacak_metin.encode('utf-8'),
    hashlib.sha256
).hexdigest()

# 3. Gönderilecek JSON paketini hazırla
payload = {
    "deviceId": device_id,
    "led": led,
    "sequence": sequence,
    "timestamp": timestamp,
    "nonce": nonce,
    "signature": signature
}

print("📡 Sahte ESP32 verisi API'ye gönderiliyor...")
try:
    response = requests.post(URL, json=payload)
    print(f"Status Code: {response.status_code}")
    print("Server Response:", response.json())
except Exception as e:
    print(f"❌ Bağlantı hatası: {e}")

