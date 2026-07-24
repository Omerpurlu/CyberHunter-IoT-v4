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

# --- BAÄLANTI BÄ°LGÄ°LERÄ° ---
API_BASE = os.getenv("CYBERHUNTER_API_URL", "http://10.104.1.89:8000")
URL = f"{API_BASE}/api/iot/led-state"
SECRET = os.getenv("DEVICE_SECRET")
if not SECRET:
    raise RuntimeError("Required environment variable is missing: DEVICE_SECRET")

# --- SAHTE ESP32 VERÄ°LERÄ° ---
device_id = "esp32-led-01"
led = "red"        # Test etmek istediÄŸin LED rengi: "blue", "red", "off"
sequence = 1       # NOT: Her yeni testte bu sayÄ±yÄ± artÄ±rmalÄ±sÄ±n! (Ã–rn: 2, 3, 4...)
timestamp = int(time.time() * 1000)  # Milisaniye cinsinden zaman damgasÄ±
nonce = uuid.uuid4().hex[:8]        # Tek kullanÄ±mlÄ±k 8 haneli rastgele kod

# 1. SÃ¶zleÅŸmeye Uygun Ä°mza Metnini OluÅŸtur (deviceId|led|sequence|timestamp|nonce)
imzalanacak_metin = f"{device_id}|{led}|{sequence}|{timestamp}|{nonce}"

# 2. HMAC-SHA256 Ä°mzasÄ±nÄ± Hesapla
signature = hmac.new(
    SECRET.encode('utf-8'),
    imzalanacak_metin.encode('utf-8'),
    hashlib.sha256
).hexdigest()

# 3. GÃ¶nderilecek JSON Paketini HazÄ±rla
payload = {
    "deviceId": device_id,
    "led": led,
    "sequence": sequence,
    "timestamp": timestamp,
    "nonce": nonce,
    "signature": signature
}

print("ğŸ“¡ Sahte ESP32 verisi API kapÄ±sÄ±na fÄ±rlatÄ±lÄ±yor...")
try:
    response = requests.post(URL, json=payload)
    print(f"Status Code: {response.status_code}")
    print("Server Response:", response.json())
except Exception as e:
    print(f"âŒ BaÄŸlantÄ± hatasÄ±: {e}")

