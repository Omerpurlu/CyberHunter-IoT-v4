from fastapi import FastAPI, HTTPException, Depends, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import hmac
import hashlib
import time
import logging

# --- LOGLAMA SİSTEMİ (Emir'in Teşhis Aracı) ---
logger = logging.getLogger("uvicorn.error")

# --- SQLALCHEMY VERİTABANI KÜTÜPHANELERİ ---
from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker, Session

SQLALCHEMY_DATABASE_URL = "sqlite:///CyberHunter.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class LedLog(Base):
    __tablename__ = "LedLoglari"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, index=True)
    led = Column(String)
    sequence = Column(Integer)
    device_timestamp = Column(Integer)
    nonce = Column(String)
    server_received_at = Column(Integer)

class DeviceCommand(Base):
    __tablename__ = "CihazEmirleri"
    id = Column(Integer, primary_key=True, index=True)
    device_id = Column(String, index=True)
    komut = Column(String) # Örn: "KIRMIZI_YAK", "MAVI_YAK"
    durum = Column(String, default="bekliyor") # bekliyor, tamamlandi
    olusturulma_zamani = Column(Integer)

# TABLO TANIMLAMALARI BİTTİKTEN SONRA, EN SOLA DAYALI ŞEKİLDE:
Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# --- WEBSOCKET YAYIN İSTASYONU ---
class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                pass # Hatalı/Kopan istemciyi yoksay

manager = ConnectionManager()
app = FastAPI(title="CyberHunter IoT Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DEVICE_SECRET = "CyberHunter_2026_SecretKey!"
last_sequence = 0
used_nonces = set()

class CommandRequest(BaseModel):
    device_id: str
    komut: str

class IoTRequest(BaseModel):
    deviceId: str
    led: str
    sequence: int
    timestamp: int
    nonce: str
    signature: str

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@app.get("/api/logs")
async def get_past_logs(limit: int = 50, db: Session = Depends(get_db)):
    gecmis_loglar = db.query(LedLog).order_by(LedLog.id.desc()).limit(limit).all()
    return gecmis_loglar

@app.get("/api/iot/devices/{device_id}/state")
async def get_device_state(device_id: str, db: Session = Depends(get_db)):
    last_log = db.query(LedLog).filter(LedLog.device_id == device_id).order_by(LedLog.id.desc()).first()
    su_an_ms = int(time.time() * 1000)
    
    if not last_log:
        return {
            "deviceId": device_id,
            "led": "off",
            "online": False,
            "sequence": 0,
            "deviceTimestamp": None,
            "serverReceivedAt": None
        }
    
    is_online = (su_an_ms - last_log.server_received_at) < 30000

    return {
        "deviceId": last_log.device_id,
        "led": last_log.led,
        "online": is_online,
        "sequence": last_log.sequence,
        "deviceTimestamp": last_log.device_timestamp,
        "serverReceivedAt": last_log.server_received_at
    }

# --- HTTP API KAPISI (GÜÇLENDİRİLMİŞ HATA YAKALAMA İLE) ---
@app.post("/api/iot/led-state")
async def receive_led_state(req: IoTRequest, db: Session = Depends(get_db)):
    global last_sequence
    
    try:
        logger.info(
            "LED istegi alindi | device=%s led=%s sequence=%s",
            req.deviceId,
            req.led,
            req.sequence
        )

        logger.info("Asama 1: device ve led kontrolu")
        if req.deviceId != "esp32-led-01":
            raise HTTPException(status_code=400, detail="Geçersiz Cihaz Kimliği")
        if req.led not in ["blue", "red", "off"]:
            raise HTTPException(status_code=400, detail="Geçersiz LED Durumu")

        logger.info("Asama 2 ve 5: HMAC, timestamp ve nonce kontrolu")
        imzalanacak_metin = f"{req.deviceId}|{req.led}|{req.sequence}|{req.timestamp}|{req.nonce}"
        hesaplanan_imza = hmac.new(
            DEVICE_SECRET.encode('utf-8'),
            imzalanacak_metin.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        if not hmac.compare_digest(hesaplanan_imza, req.signature):
            raise HTTPException(status_code=401, detail="Geçersiz İmza!")

        su_an_ms = int(time.time() * 1000)
        if (su_an_ms - req.timestamp) > 300000:
            raise HTTPException(status_code=400, detail="Zaman aşımı (Replay Attack)")
            
        if req.nonce in used_nonces:
            raise HTTPException(status_code=400, detail="Nonce daha önce kullanılmış")

        # --- EMIR ICIN SEQUENCE DEBUG LOGLARI ---
        logger.info("=== SEQUENCE DEBUG KONTROLU ===")
        logger.info(f"Cihaz ID: {req.deviceId}")
        logger.info(f"Gelen Sequence: {req.sequence}")
        logger.info(f"Backend last_sequence: {last_sequence}")
        logger.info(f"Gelen > Last Sonucu: {req.sequence > last_sequence}")
        logger.info("===============================")
        # ----------------------------------------

        # SADECE BİR KERE KONTROL EDİYORUZ
        if req.sequence <= last_sequence:
            raise HTTPException(status_code=400, detail="Geçersiz sıra numarası")

        # BÜTÜN GÜVENLİK TESTLERİNİ GEÇTİYSE YENİ DEĞERLERİ KAYDEDİYORUZ
        last_sequence = req.sequence
        used_nonces.add(req.nonce)

        logger.info("Asama 6: veritabani kaydi")
        try:
            yeni_log = LedLog(
                device_id=req.deviceId,
                led=req.led,
                sequence=req.sequence,
                device_timestamp=req.timestamp,
                nonce=req.nonce,
                server_received_at=su_an_ms
            )
            db.add(yeni_log)
            db.commit()
            db.refresh(yeni_log)
        except Exception:
            db.rollback()
            logger.exception("LED veritabani kaydi basarisiz")
            raise

        logger.info("Asama 7: websocket yayini")
        try:
            canli_veri = {
                "type": "device-state",
                "deviceId": req.deviceId,
                "led": req.led,
                "online": True,
                "sequence": req.sequence,
                "deviceTimestamp": req.timestamp,
                "serverReceivedAt": su_an_ms
            }
            await manager.broadcast(canli_veri)
        except Exception:
            logger.exception("WebSocket yayini basarisiz")

        return {
            "ok": True,
            "deviceId": req.deviceId,
            "led": req.led,
            "serverReceivedAt": su_an_ms
        }

    except Exception:
        logger.exception(
            "LED endpoint'inde beklenmeyen hata | device=%s led=%s sequence=%s",
            getattr(req, "deviceId", None),
            getattr(req, "led", None),
            getattr(req, "sequence", None)
        )
        raise
    # --- 1. WEB SİTESİNDEN CİHAZA EMİR GÖNDERME KAPISI ---
@app.post("/api/iot/commands")
async def create_command(req: CommandRequest, db: Session = Depends(get_db)):
    yeni_emir = DeviceCommand(
        device_id=req.device_id,
        komut=req.komut,
        durum="bekliyor",
        olusturulma_zamani=int(time.time() * 1000)
    )
    db.add(yeni_emir)
    db.commit()
    return {"mesaj": "Siber emir basariyla siraya alindi", "komut": req.komut}

# --- 2. ESP32'NİN "BANA EMİR VAR MI?" DİYE SORDUĞU KAPI ---
@app.get("/api/iot/commands/pending/{device_id}")
async def get_pending_commands(device_id: str, db: Session = Depends(get_db)):
    bekleyen_emir = db.query(DeviceCommand).filter(
        DeviceCommand.device_id == device_id,
        DeviceCommand.durum == "bekliyor"
    ).first()

    if bekleyen_emir:
        return {"id": bekleyen_emir.id, "komut": bekleyen_emir.komut}
    return {"id": None, "komut": "YOK"}

# --- 3. ESP32'NİN "EMRİ YERİNE GETİRDİM" DEDİĞİ KAPI ---
@app.post("/api/iot/commands/complete/{command_id}")
async def complete_command(command_id: int, db: Session = Depends(get_db)):
    emir = db.query(DeviceCommand).filter(DeviceCommand.id == command_id).first()
    if emir:
        emir.durum = "tamamlandi"
        db.commit()
        return {"mesaj": "Emir tamamlandi olarak isaretlendi"}
    raise HTTPException(status_code=404, detail="Emir bulunamadi")