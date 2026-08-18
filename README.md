# CyberHunter-IoT

CyberHunter-IoT, IoT cihazlarından gelen güvenlik olaylarını toplayan, değerlendiren, veritabanında saklayan ve web tabanlı bir kontrol panelinde görüntüleyen bir siber güvenlik projesidir.

Projenin temel amacı; ESP32 ve Raspberry Pi gibi cihazlardan gelen verileri merkezi bir backend servisine aktarmak, güvenlik olaylarını analiz etmek, sistem bileşenlerinin durumunu takip etmek ve kullanıcıya anlaşılır bir yönetim paneli sunmaktır.

---

## İçindekiler

- [Proje Hakkında](#proje-hakkında)
- [Projenin Amaçları](#projenin-amaçları)
- [Sistem Mimarisi](#sistem-mimarisi)
- [Veri Akışı](#veri-akışı)
- [Kullanılan Teknolojiler](#kullanılan-teknolojiler)
- [Proje Klasör Yapısı](#proje-klasör-yapısı)
- [Temel Özellikler](#temel-özellikler)
- [Kurulum](#kurulum)
- [Backend Kurulumu](#backend-kurulumu)
- [Frontend Kurulumu](#frontend-kurulumu)
- [ESP32 Firmware Kurulumu](#esp32-firmware-kurulumu)
- [Veritabanı Kurulumu](#veritabanı-kurulumu)
- [Projeyi Çalıştırma](#projeyi-çalıştırma)
- [API ve Swagger](#api-ve-swagger)
- [Testler](#testler)
- [Güvenlik Yapısı](#güvenlik-yapısı)
- [Sistem Durumu ve Heartbeat](#sistem-durumu-ve-heartbeat)
- [Mevcut Proje Durumu](#mevcut-proje-durumu)
- [Geliştirme Planı](#geliştirme-planı)
- [Önemli Güvenlik Uyarıları](#önemli-güvenlik-uyarıları)

---

## Proje Hakkında

CyberHunter-IoT, IoT tabanlı sistemlerde oluşabilecek güvenlik olaylarının izlenmesi için geliştirilmiştir.

Sistem içerisinde ESP32 cihazı, Raspberry Pi, FastAPI backend servisi, PostgreSQL veritabanı ve React tabanlı bir web arayüzü birlikte çalışmaktadır.

Cihazlardan gelen güvenlik verileri backend tarafından doğrulanır, işlenir ve PostgreSQL veritabanına kaydedilir. Kaydedilen veriler daha sonra API üzerinden frontend uygulamasına aktarılır ve kullanıcıya kontrol paneli üzerinden gösterilir.

Proje; IoT güvenliği, veri bütünlüğü, cihaz doğrulama, sistem sağlığı takibi, olay kaydı ve merkezi izleme gibi konuları bir araya getirmektedir.

---

## Projenin Amaçları

CyberHunter-IoT projesinin temel amaçları şunlardır:

- IoT cihazlarından gelen güvenlik olaylarını merkezi olarak toplamak
- Güvenlik olaylarını PostgreSQL veritabanında saklamak
- ESP32 tarafından yapılan risk değerlendirmelerini kaydetmek
- Aynı olayın birden fazla kez kaydedilmesini engellemek
- Sistem bileşenlerinin çevrimiçi veya çevrimdışı durumunu takip etmek
- Cihazlardan düzenli heartbeat verisi almak
- Güvenlik olaylarını web panelinde görüntülemek
- Verilerin bütünlüğünü kontrol etmek
- API üzerinden frontend, backend ve cihaz iletişimini sağlamak
- Sistemin ileride farklı IoT cihazlarıyla genişletilebilmesini sağlamak

---

## Sistem Mimarisi

CyberHunter-IoT genel olarak aşağıdaki bileşenlerden oluşur:

```text
IoT / Güvenlik Verisi
        |
        v
   Raspberry Pi
        |
        v
      ESP32
        |
        v
 FastAPI Backend
        |
        v
   PostgreSQL
        |
        v
  React Dashboard
```

Sistemdeki ana bileşenler:

### ESP32

ESP32, cihaz tarafındaki temel IoT bileşenidir.

Görevleri:

- Wi-Fi ağına bağlanmak
- Backend servisine bağlanmak
- Cihaz kimliğini göndermek
- Heartbeat verisi göndermek
- Firmware sürümünü bildirmek
- Güvenlik değerlendirmelerini sisteme aktarmak
- Gerektiğinde komut almak veya durum bilgisi göndermek

### Raspberry Pi

Raspberry Pi, güvenlik verilerinin oluşturulduğu veya cihazlar arasında aktarıldığı ara katman olarak kullanılabilir.

Görevleri:

- Güvenlik olaylarını almak
- Verileri uygun formata dönüştürmek
- ESP32 ile iletişim kurmak
- Test veya saldırı verilerinin sisteme aktarılmasını sağlamak

### FastAPI Backend

Backend, sistemin merkezi kontrol ve veri işleme katmanıdır.

Görevleri:

- API endpointlerini sağlamak
- Gelen verileri doğrulamak
- Veritabanı işlemlerini gerçekleştirmek
- Hataları yönetmek
- Tekrarlanan olayları kontrol etmek
- Sistem durumunu hesaplamak
- Frontend ile cihazlar arasında bağlantı kurmak

### PostgreSQL

PostgreSQL, sistemdeki kalıcı verilerin saklandığı ilişkisel veritabanıdır.

Başlıca saklanan veriler:

- Güvenlik olayları
- ESP32 risk değerlendirmeleri
- Sistem bileşenlerinin durumları
- Cihaz bilgileri
- Olay zamanları
- IP ve port bilgileri
- Hash değerleri
- Firmware sürümleri
- Heartbeat kayıtları

### React Dashboard

React tabanlı frontend, verilerin kullanıcıya gösterildiği yönetim panelidir.

Görevleri:

- Güvenlik olaylarını listelemek
- Sistem durumunu göstermek
- ESP32 değerlendirmelerini göstermek
- Sistem loglarını görüntülemek
- Backend API ile düzenli olarak haberleşmek
- Hata, yüklenme ve boş veri durumlarını yönetmek

---

## Veri Akışı

Sistemde güvenlik olaylarının genel veri akışı aşağıdaki gibidir:

1. Bir test saldırısı veya güvenlik olayı oluşturulur.
2. Veri Raspberry Pi tarafından alınır.
3. Veri ESP32 tarafına aktarılır.
4. ESP32 olay üzerinde bir risk değerlendirmesi gerçekleştirir.
5. Olay ve değerlendirme sonucu backend servisine gönderilir.
6. FastAPI gelen veriyi doğrular.
7. Veritabanı işlemi tek bir transaction içerisinde gerçekleştirilir.
8. Güvenlik olayı PostgreSQL veritabanına kaydedilir.
9. ESP32 değerlendirmesi ilgili güvenlik olayıyla ilişkilendirilir.
10. Frontend, API üzerinden kayıtları alır.
11. Kullanıcı güvenlik olaylarını dashboard üzerinden görüntüler.

---

## Kullanılan Teknolojiler

### Backend

- Python
- FastAPI
- Uvicorn
- SQLAlchemy
- Alembic
- Pydantic
- Psycopg
- PostgreSQL
- Pytest

### Frontend

- React
- Vite
- JavaScript
- JSX
- CSS
- Fetch API

### IoT ve Firmware

- ESP32
- C++
- PlatformIO
- Wi-Fi
- HTTP / HTTPS
- Heartbeat mekanizması

### Veritabanı

- PostgreSQL
- pgAdmin
- SQLAlchemy ORM
- Alembic migration sistemi

### Geliştirme Araçları

- Git
- GitHub
- Visual Studio Code
- Swagger UI
- Windows PowerShell
- Komut İstemi

---

## Proje Klasör Yapısı

Projenin genel klasör yapısı aşağıdaki gibidir:

```text
CyberHunter-IoT/
│
├── backend/
│   ├── main.py
│   ├── models.py
│   ├── schemas.py
│   ├── dependencies.py
│   ├── routers/
│   ├── services/
│   ├── repositories/
│   ├── tests/
│   └── README.md
│
├── frontend/
│   ├── src/
│   ├── public/
│   ├── package.json
│   ├── vite.config.js
│   └── README.md
│
├── esp32-firmware/
│   ├── include/
│   ├── src/
│   ├── platformio.ini
│   └── README.md
│
├── alembic/
│   ├── versions/
│   └── env.py
│
├── docs/
│   ├── database.md
│   ├── api.md
│   └── system-architecture.md
│
├── .env.example
├── .gitignore
├── alembic.ini
└── README.md
```

Klasör yapısı geliştirme sürecinde değişebilir. En güncel yapı doğrudan proje dizini üzerinden kontrol edilmelidir.

---

## Temel Özellikler

### Güvenlik olaylarının kaydedilmesi

Sistem, cihazlardan gelen güvenlik olaylarını backend üzerinden PostgreSQL veritabanına kaydeder.

Bir güvenlik olayı şu tür bilgileri içerebilir:

- Olay kimliği
- Cihaz kimliği
- Kaynak IP adresi
- Kaynak port
- Hedef port
- Protokol
- Olay türü
- Olay mesajı
- Komut bilgisi
- Olay zamanı
- Risk puanı
- Hash değeri

### ESP32 değerlendirmesi

ESP32 tarafından yapılan değerlendirme, güvenlik olayıyla ilişkilendirilir.

Değerlendirme içerisinde aşağıdaki bilgiler bulunabilir:

- Risk puanı
- Risk seviyesi
- Değerlendirme sonucu
- Cihaz kimliği
- Değerlendirme zamanı
- Ek açıklamalar

### Tekrarlanan kayıt kontrolü

Aynı olayın tekrar gönderilmesi durumunda sistem yeni bir kayıt oluşturmak yerine mevcut kaydı algılayabilir.

Bu yapı sayesinde:

- Aynı olayın gereksiz yere tekrar kaydedilmesi önlenir.
- Veritabanında yinelenen kayıt miktarı azaltılır.
- Cihazın ağ sorunları nedeniyle aynı veriyi tekrar göndermesi daha güvenli şekilde yönetilir.

### Transaction yönetimi

Bir güvenlik olayı ve ona bağlı ESP32 değerlendirmesi tek bir veritabanı işlemi içerisinde kaydedilir.

İşlemlerden biri başarısız olursa transaction geri alınır. Böylece veritabanında eksik veya yarım kayıt oluşması engellenir.

### Sistem durumunun izlenmesi

Backend, sistem bileşenlerinin son bağlantı zamanlarını kontrol ederek çevrimiçi veya çevrimdışı durumlarını belirleyebilir.

Takip edilebilecek bileşenler:

- Backend
- PostgreSQL
- ESP32
- Raspberry Pi
- Frontend

---

## Kurulum

Projeyi çalıştırmak için aşağıdaki yazılımların sistemde kurulu olması gerekir:

- Git
- Python 3.12 veya uyumlu bir Python sürümü
- Node.js
- npm
- PostgreSQL
- pgAdmin
- PlatformIO
- Visual Studio Code

Projeyi bilgisayara indirmek için:

```bash
git clone <CyberHunter-IoT-v4>
cd CyberHunter-IoT
```

Repository adresi özel ise GitHub hesabının projeye erişim yetkisi bulunmalıdır.

---

## Backend Kurulumu

Backend klasörüne geçin:

```bash
cd backend
```

Sanal ortam oluşturun:

```bash
python -m venv .venv
```

Windows PowerShell üzerinde sanal ortamı etkinleştirin:

```powershell
.\.venv\Scripts\Activate.ps1
```

Komut İstemi üzerinde:

```cmd
.venv\Scripts\activate
```

Gerekli paketleri yükleyin:

```bash
pip install -r requirements.txt
```

Backend ortam değişkenlerini ayarlayın.

Örnek:

```env
DATABASE_URL=postgresql+psycopg://postgres:parola@localhost:5432/cyberhunter
SECRET_KEY=guvenli-bir-deger
```

Gerçek veritabanı parolaları ve gizli anahtarlar GitHub repository içerisine eklenmemelidir.

Backend hakkında daha ayrıntılı bilgi için:

```text
backend/README.md
```

---

## Frontend Kurulumu

Frontend klasörüne geçin:

```bash
cd frontend
```

Paketleri yükleyin:

```bash
npm install
```

Frontend ortam değişkeni dosyasını oluşturun:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Development sunucusunu başlatın:

```bash
npm run dev
```

Production build oluşturmak için:

```bash
npm run build
```

Frontend hakkında daha ayrıntılı bilgi için:

```text
frontend/README.md
```

---

## ESP32 Firmware Kurulumu

ESP32 firmware kodları aşağıdaki klasörde bulunur:

```text
esp32-firmware/
```

Firmware içerisinde gizli bilgiler doğrudan kaynak koduna yazılmamalıdır.

Örnek yapılandırma dosyası:

```text
esp32-firmware/include/secrets.example.h
```

Bu dosya kopyalanarak gerçek bir `secrets.h` dosyası oluşturulabilir.

Örnek değişkenler:

```cpp
#define WIFI_SSID "YYU-Muhendislik-Wifi"
#define WIFI_PASSWORD ""
#define DEVICE_ID "esp32-01"
#define API_BASE_URL "http://192.168.1.100:8000"
#define FIRMWARE_VERSION "1.0.0"
#define DEVICE_SECRET "cihaz-gizli-anahtari"
```

Kullanılabilecek diğer ayarlar:

```cpp
#define TLS_ROOT_CA "sertifika-bilgisi"
#define ALLOW_INSECURE_TLS false
```

Firmware yüklemek için PlatformIO kullanılabilir:

```bash
pio run
```

ESP32’ye yüklemek için:

```bash
pio run --target upload
```

Seri port ekranını açmak için:

```bash
pio device monitor
```

ESP32 fiziksel olarak bağlı değilse frontend ve backend çalıştırılabilir. Ancak gerçek heartbeat ve cihaz durumu verisi alınamaz.

Firmware hakkında daha ayrıntılı bilgi için:

```text
esp32-firmware/README.md
```

---

## Veritabanı Kurulumu

CyberHunter-IoT projesinin ana veritabanı PostgreSQL’dir.

Örnek veritabanı oluşturma komutu:

```sql
CREATE DATABASE cyberhunter;
```

Backend bağlantı adresi `.env` dosyasında tanımlanır:

```env
DATABASE_URL=postgresql+psycopg://postgres:parola@localhost:5432/cyberhunter
```

Migration işlemlerini uygulamak için:

```bash
alembic upgrade head
```

Mevcut migration durumunu kontrol etmek için:

```bash
alembic current
```

Migration geçmişini görüntülemek için:

```bash
alembic history
```

Yeni bir migration oluşturmak için:

```bash
alembic revision --autogenerate -m "migration_aciklamasi"
```

Migration oluşturulduktan sonra dosya içeriği kontrol edilmeden doğrudan canlı veritabanına uygulanmamalıdır.

Veritabanı yedeği almak için örnek komut:

```bash
pg_dump -U postgres -d cyberhunter -F c -f cyberhunter_backup.dump
```

Yedeği geri yüklemek için:

```bash
pg_restore -U postgres -d cyberhunter cyberhunter_backup.dump
```

Veritabanı yapısı hakkında daha ayrıntılı bilgi için:

```text
docs/database.md
```

---

## Projeyi Çalıştırma

Projenin tam olarak çalıştırılması için backend ve frontend ayrı terminallerde başlatılmalıdır.

### Backend terminali

```bash
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```

Backend adresi:

```text
http://127.0.0.1:8000
```

### Frontend terminali

```bash
cd frontend
npm run dev
```

Vite tarafından verilen frontend adresi tarayıcıdan açılmalıdır.

Genellikle:

```text
http://localhost:5173
```

Port başka bir uygulama tarafından kullanılıyorsa Vite farklı bir port seçebilir.

### ESP32

ESP32 firmware’i cihaza yüklendikten sonra cihazın backend ile aynı ağa erişebilmesi gerekir.

ESP32 içerisindeki `API_BASE_URL` değeri, backend’in ağ üzerinden erişilebilen IP adresini göstermelidir.

ESP32 üzerinden `127.0.0.1` kullanılamaz. Çünkü ESP32 açısından `127.0.0.1`, ESP32’nin kendisini ifade eder.

Örnek:

```cpp
#define API_BASE_URL "http://192.168.1.50:8000"
```

---

## API ve Swagger

FastAPI, API dokümantasyonunu otomatik olarak oluşturur.

Backend çalışırken Swagger arayüzüne şu adresten erişilebilir:

```text
http://127.0.0.1:8000/docs
```

Alternatif ReDoc arayüzü:

```text
http://127.0.0.1:8000/redoc
```

OpenAPI JSON çıktısı:

```text
http://127.0.0.1:8000/openapi.json
```

Projede bulunabilecek temel endpoint örnekleri:

| Method | Endpoint               | Açıklama                                 |
| ------ | ---------------------- | ---------------------------------------- |
| POST   | `/api/security-events` | Yeni güvenlik olayını kaydeder           |
| GET    | `/api/security-events` | Güvenlik olaylarını listeler             |
| GET    | `/api/system/status`   | Sistem bileşenlerinin durumunu döndürür  |
| POST   | `/api/iot/heartbeat`   | ESP32 heartbeat bilgisini alır           |
| GET    | `/api/health`          | Backend sağlık kontrolünü gerçekleştirir |

Endpoint listesi geliştirme sürecinde değişebilir. En güncel endpointler Swagger üzerinden kontrol edilmelidir.

### AI - Bridge - backend güvenlik olayı sözleşmesi

AI tarafından üretilen ham JSON doğrudan `POST /api/security-events`
endpointine gönderilmez. Ham çıktıyı backend sözleşmesine dönüştürme,
ESP32'nin gerçek değerlendirmesiyle birleştirme ve birleşik isteği gönderme
sorumluluğu Raspberry Pi Bridge katmanına aittir.

AI ham JSON örneği:

```json
{
  "event_id": "evt-20260803T190152Z-k4m8x2",
  "timestamp": "2026-08-03T19:01:52Z",
  "source_ip": "192.168.137.1",
  "destination_port": 22,
  "protocol": "SSH",
  "event_type": "Credential_Attack",
  "command": "whoami; uname -a; pwd; ls; exit",
  "tactic": "Credential Access",
  "risk_score": 55
}
```

Bridge tarafından backend'e gönderilecek birleşik JSON örneği:

```json
{
  "event_id": "evt-20260803T190152Z-k4m8x2",
  "timestamp": "2026-08-03T19:01:52Z",
  "source_ip": "192.168.137.1",
  "destination_port": 22,
  "protocol": "ssh",
  "event_type": "credential_attack",
  "command": "whoami; uname -a; pwd; ls; exit",
  "tactic": "credential_access",
  "input_risk_score": 55,
  "esp32_risk_score": 55,
  "esp32_decision": "warning",
  "esp32_processed": true,
  "device_id": "esp32-cyberhunter-01"
}
```

Bu örnekteki `esp32_risk_score`, `esp32_decision`, `esp32_processed` ve
`device_id` değerleri yalnızca JSON sözleşmesini göstermek içindir. Gerçek
değerler ESP32'den gelmelidir; Bridge bu değerleri tahmin etmemeli veya AI risk
skorundan üretmemelidir. AI `risk_score` değeri yalnızca backend'in kanonik
`input_risk_score` alanına eşlenmelidir.

Backend, desteklenen `protocol`, `event_type` ve `tactic` yazımlarını payload
hash'i hesaplanmadan önce kanonik hale getirir. Tanınmayan değerlerde geriye
uyumluluk korunur: protocol mevcut trim/küçük harf davranışını, event type trim
davranışını, tactic ise gönderildiği değeri korur.

`destination_port`, saldırganın dışarıdan hedeflediği porttur. TCP/22 trafiği
Cowrie'nin TCP/2222 portuna yönlendirilse bile veritabanında dış hedef port `22`
saklanmalıdır; `2222` yalnızca altyapının iç port ayrıntısıdır.

### ESP32 çift yönlü round-trip prototipi

Yazılımsal kabul döngüsü şu akışı kullanır:

```text
ESP32/Bridge -> POST /api/security-events -> PostgreSQL
RiskPolicyEvaluator -> response_actions
ESP32 -> GET /api/iot/commands/next?device_id=...
ESP32 -> POST /api/iot/commands/{command_id}/ack
GET /api/response-actions -> gelecekte dashboard
```

PostgreSQL ESP32'ye doğrudan bağlantı kurmaz ve ESP32 veritabanı bağlantı
bilgilerini bilmez. Bütün haberleşme FastAPI HTTP API üzerinden yapılır.

Varsayılan prototip policy güvenlidir: otomatik shutdown kapalı ve manuel onay
zorunludur. Bu nedenle varsayılan ayarlarla fiziksel izolasyon komutu oluşmaz.
`isolate_device` round-trip testi için ayrı test ortamında aşağıdaki ayarlar
kullanılabilir:

```env
POLICY_AUTOMATIC_SHUTDOWN_ALLOWED=true
POLICY_MANUAL_APPROVAL_REQUIRED=false
```

Backend çalışırken HTTP simülatörü şu şekilde başlatılır:

```bash
cd backend
python tools/esp32_roundtrip_simulator.py --base-url http://127.0.0.1:8000
```

Simülatördeki ESP32 assessment alanları yalnız test amaçlı sözleşme
değerleridir. Gerçek röle kullanılmaz; `simulated_isolated` yalnız yazılımsal
kabul sonucudur. ESP32 kendi yönetim bağlantısını kesmemelidir; ilerideki
fiziksel röle korunan cihazın bağlantısını kesmelidir.

Polling ve ACK endpointlerinde cihaz kimlik doğrulaması henüz uygulanmamıştır.
Üretime açılmadan önce HMAC, timestamp, nonce, sequence ve kalıcı replay
koruması eklenmelidir. Organization ve çoklu policy tabloları sonraki aşamadır.

ESP32 firmware'deki response-action istemcisi şimdilik yalnız
`isolate_device` eylemini dry-run olarak işler. Komut seri monitörde gösterilir,
hiçbir GPIO değiştirilmez ve gerçek röle çalıştırılmaz. Başarılı dry-run ACK'i
`relay_state="simulated_isolated"` değerini taşır. Son işlenen command ID ve ACK
gövdesi `response` Preferences namespace'inde saklanır; böylece yeniden
başlatma veya ACK retry sırasında aynı komut tekrar uygulanmaz.

Firmware hiçbir zaman PostgreSQL'e doğrudan bağlanmaz. Gerçek röle desteği
eklenmeden önce polling ve ACK istekleri için cihaz HMAC'i, güvenilir timestamp,
kalıcı sequence ve nonce tabanlı replay koruması zorunlu hale getirilmelidir.

### Temel HTTP yanıt kodları

| Kod                         | Açıklama                                            |
| --------------------------- | --------------------------------------------------- |
| `200 OK`                    | İşlem başarıyla tamamlandı                          |
| `201 Created`               | Yeni kayıt oluşturuldu                              |
| `409 Conflict`              | Aynı kimliğe sahip çakışan kayıt bulundu            |
| `422 Unprocessable Entity`  | Gönderilen veri doğrulama kurallarına uymadı        |
| `500 Internal Server Error` | Backend tarafında beklenmeyen hata oluştu           |
| `503 Service Unavailable`   | Veritabanı veya servis geçici olarak kullanılamıyor |

---

## Testler

Backend testlerini çalıştırmak için:

```bash
cd backend
pytest
```

Daha ayrıntılı test çıktısı için:

```bash
pytest -v
```

Belirli bir test dosyasını çalıştırmak için:

```bash
pytest tests/test_security_events.py -v
```

Frontend build kontrolü için:

```bash
cd frontend
npm run build
```

Firmware derleme kontrolü için:

```bash
cd esp32-firmware
pio run
```

Değişiklikler GitHub’a gönderilmeden önce en azından aşağıdaki kontrollerin yapılması önerilir:

- Backend testlerinin başarılı olması
- Frontend build işleminin tamamlanması
- Alembic migration durumunun kontrol edilmesi
- Swagger endpointlerinin test edilmesi
- Veritabanı kayıtlarının doğrulanması
- Gizli dosyaların Git’e eklenmediğinin kontrol edilmesi

---

## Güvenlik Yapısı

CyberHunter-IoT projesinde güvenlik amacıyla farklı yöntemler kullanılabilir.

### Veri doğrulama

Backend’e gelen veriler Pydantic şemalarıyla doğrulanır.

Kontrol edilebilecek alanlar:

- IP adresi biçimi
- Port aralığı
- Risk puanı
- Zaman bilgisi
- Zorunlu alanlar
- Metin uzunlukları
- Cihaz kimliği

### Hash kullanımı

Hash değerleri, bir verinin özetini oluşturmak ve kayıt değişikliklerini tespit etmeye yardımcı olmak için kullanılabilir.

Projede MD5 alanları bulunabilir. Ancak MD5 modern kriptografik güvenlik için yeterli değildir.

MD5:

- Eğitim ve basit bütünlük kontrolü için kullanılabilir.
- Parola saklamak için kullanılmamalıdır.
- Dijital imza yerine kullanılmamalıdır.
- Güvenlik açısından kritik doğrulamalarda tercih edilmemelidir.

Daha güçlü bütünlük kontrolleri için SHA-256 veya HMAC-SHA256 tercih edilmelidir.

### Cihaz gizli anahtarı

Her cihaz için bir `DEVICE_SECRET` değeri kullanılabilir.

Bu değer:

- Cihazın kimliğini doğrulamak
- İstek imzası oluşturmak
- Sahte cihaz isteklerini azaltmak
- HMAC tabanlı doğrulama yapmak

amacıyla kullanılabilir.

Gizli anahtar hiçbir zaman frontend koduna veya GitHub repository içerisine yazılmamalıdır.

### HTTPS ve TLS

Gerçek ağ veya internet ortamında HTTP yerine HTTPS kullanılması önerilir.

HTTP verileri şifrelemeden aktarır.

HTTPS ise TLS kullanarak:

- İstemci ve sunucu arasındaki trafiği şifreler.
- Verinin değiştirilmesini zorlaştırır.
- Sunucu kimliğinin doğrulanmasına yardımcı olur.

Geliştirme ortamında HTTP kullanılabilir. Üretim ortamında HTTPS tercih edilmelidir.

---

## Sistem Durumu ve Heartbeat

Heartbeat, bir cihazın belirli aralıklarla backend’e “çalışıyorum” mesajı göndermesidir.

ESP32 heartbeat mesajı içerisinde şu bilgiler bulunabilir:

- Cihaz kimliği
- Firmware sürümü
- Çalışma süresi
- Yerel IP adresi
- Sinyal gücü
- Gönderim zamanı
- Sistem durumu

Backend, son heartbeat zamanını kontrol ederek cihazın durumunu belirler.

Örnek:

- Son heartbeat yakın zamanda geldiyse cihaz çevrimiçi kabul edilir.
- Belirlenen süre boyunca heartbeat alınmadıysa cihaz çevrimdışı kabul edilir.
- Veriler eksik veya geçersizse cihaz durumu bilinmiyor olarak gösterilebilir.

Heartbeat sistemi, cihazın fiziksel olarak çalışıp çalışmadığını anlamaya yardımcı olur. Ancak tek başına cihazın tüm işlevlerinin doğru çalıştığını kesin olarak kanıtlamaz.

---

## Mevcut Proje Durumu

Projenin mevcut geliştirme aşamasında tamamlanan veya üzerinde çalışılan başlıca özellikler:

- FastAPI backend yapısı oluşturuldu.
- React ve Vite tabanlı frontend geliştirildi.
- SQLite veritabanından PostgreSQL’e geçiş gerçekleştirildi.
- SQLAlchemy modelleri PostgreSQL ile uyumlu hâle getirildi.
- Alembic migration sistemi eklendi.
- Güvenlik olayları için POST endpointi geliştirildi.
- Güvenlik olayları için GET endpointi geliştirildi.
- ESP32 değerlendirmeleri güvenlik olaylarıyla ilişkilendirildi.
- Tekrarlanan olaylar için idempotency kontrolü eklendi.
- Veritabanı transaction yönetimi oluşturuldu.
- Güvenlik olayları frontend üzerinde görüntülenmeye başlandı.
- Sistem logları ve güvenlik olayları ayrı bölümlerde gösterildi.
- Heartbeat firmware yapısı geliştirildi.
- Sistem bileşenlerinin durumunu takip eden yapı üzerinde çalışıldı.
- Backend testleri oluşturuldu.
- Swagger dokümantasyonu kullanılabilir hâle getirildi.
- PostgreSQL yedekleme ve doğrulama işlemleri gerçekleştirildi.

Bu bölüm her önemli geliştirme sonrasında güncellenmelidir.

---

## Geliştirme Planı

Projenin sonraki aşamalarında aşağıdaki çalışmalar gerçekleştirilebilir:

- Gerçek ESP32 cihazıyla heartbeat testlerinin tamamlanması
- Raspberry Pi ve ESP32 arasındaki veri akışının doğrulanması
- HTTPS ve TLS yapılandırmasının tamamlanması
- HMAC-SHA256 cihaz doğrulamasının geliştirilmesi
- Eski LED ve cihaz emri yapılarının kaldırılması
- Kullanılmayan veritabanı tablolarının migration ile silinmesi
- Sistem sağlık ekranının genişletilmesi
- Kullanıcı giriş ve yetkilendirme sisteminin eklenmesi
- Güvenlik olayları için filtreleme ve arama eklenmesi
- Risk seviyesine göre bildirim sistemi oluşturulması
- Merkezi loglama mekanizmasının geliştirilmesi
- Docker desteğinin eklenmesi
- CI/CD test sürecinin oluşturulması
- Production ortamı için güvenli deployment yapılması

---

## Önemli Güvenlik Uyarıları

Aşağıdaki bilgiler repository içerisine eklenmemelidir:

- Wi-Fi parolası
- PostgreSQL parolası
- Gerçek cihaz gizli anahtarı
- API anahtarları
- TLS özel anahtarları
- Sertifika özel bilgileri
- Kullanıcı parolaları
- Production ortam değişkenleri

Gizli bilgiler aşağıdaki dosyalarda tutulabilir:

```text
.env
secrets.h
```

Bu dosyalar `.gitignore` içerisinde bulunmalıdır.

Örnek dosyalar paylaşılabilir:

```text
.env.example
secrets.example.h
```

Örnek dosyalarda gerçek parola veya anahtar bulunmamalıdır.

---

## Git Çalışma Düzeni

Yeni özellikler ayrı branch üzerinde geliştirilmelidir.

Örnek:

```bash
git checkout -b feature/yeni-ozellik
```

Değişiklikleri kontrol etmek için:

```bash
git status
```

Dosyaları hazırlamak için:

```bash
git add .
```

Commit oluşturmak için:

```bash
git commit -m "Yeni özellik açıklaması"
```

Branch’i GitHub’a göndermek için:

```bash
git push -u origin feature/yeni-ozellik
```

Doğrudan ana branch üzerinde büyük değişiklik yapılması önerilmez.

---

## Dokümantasyon

Daha ayrıntılı açıklamalar için aşağıdaki dosyalar kullanılabilir:

| Dosya                         | İçerik                                    |
| ----------------------------- | ----------------------------------------- |
| `backend/README.md`           | Backend kurulumu ve API yapısı            |
| `frontend/README.md`          | Frontend kurulumu ve ekran yapısı         |
| `esp32-firmware/README.md`    | ESP32 firmware kurulumu                   |
| `docs/database.md`            | PostgreSQL tabloları ve veritabanı yapısı |
| `docs/api.md`                 | Endpoint ve yanıt açıklamaları            |
| `docs/system-architecture.md` | Sistem mimarisi ve veri akışı             |

---

## Katkıda Bulunma

Projede değişiklik yapmadan önce:

1. Güncel branch’i çekin.
2. Yeni bir feature branch oluşturun.
3. Yalnızca kendi görevinizle ilgili dosyalarda değişiklik yapın.
4. Testleri çalıştırın.
5. Gizli bilgilerin commit içerisine girmediğini kontrol edin.
6. Açıklayıcı bir commit mesajı oluşturun.
7. Değişiklikleri ilgili branch’e gönderin.
8. Gerekirse pull request oluşturun.

---

## Lisans

Bu proje eğitim ve geliştirme amacıyla hazırlanmıştır.

Lisans bilgisi daha sonra proje gereksinimlerine göre eklenecektir.

---

## Proje Ekibi

CyberHunter-IoT, ekip çalışmasıyla geliştirilen bir IoT ve siber güvenlik projesidir.

Projedeki temel çalışma alanları:

- IoT cihaz geliştirme
- ESP32 firmware
- Raspberry Pi entegrasyonu
- Backend geliştirme
- PostgreSQL veritabanı yönetimi
- Frontend geliştirme
- Güvenlik testi ve saldırı verisi üretimi
- Sistem mimarisi
- Dokümantasyon ve test

---

## Sonuç

CyberHunter-IoT; IoT cihazlarından gelen güvenlik olaylarını merkezi bir sistemde toplamak, değerlendirmek, saklamak ve kullanıcıya görsel olarak sunmak amacıyla geliştirilmiştir.

Proje içerisinde cihaz iletişimi, REST API, PostgreSQL, veri doğrulama, transaction yönetimi, sistem sağlık takibi, heartbeat, frontend geliştirme ve güvenlik kontrolleri birlikte kullanılmaktadır.

Projenin modüler yapısı sayesinde ileride yeni cihazlar, yeni güvenlik analizleri, farklı veritabanı tabloları ve gelişmiş izleme özellikleri sisteme eklenebilir.
