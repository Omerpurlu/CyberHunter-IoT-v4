import hashlib
import hmac
import logging
import os
import time
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from crypto_utils import LogDecryptionError, decrypt_text, encrypt_text
from database import engine
from dependencies import get_db
from hash_utils import device_command_payload, led_log_payload, md5_checksum
from models import DeviceCommand, LedLog
from routers.security_events import router as security_events_router

logger = logging.getLogger("uvicorn.error")

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(f"Required environment variable is missing: {name}")
    return value


DEVICE_SECRET = require_env("DEVICE_SECRET")

app = FastAPI(title="CyberHunter IoT Backend")
app.include_router(security_events_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv("CORS_ORIGINS", "*").split(","),
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def verify_postgresql_connection() -> None:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1")).scalar_one()
    except SQLAlchemyError:
        raise RuntimeError(
            "PostgreSQL baglantisi dogrulanamadi; uygulama baslatilamadi."
        ) from None


DEVICE_ID = "esp32-led-01"
last_sequence = 0
used_nonces: dict[str, int] = {}
NONCE_TTL_MS = 300000
UNREADABLE_ENCRYPTED_LOG = "[Şifreli log çözülemedi]"


def device_log_message(log: LedLog) -> str:
    return (
        f"{log.device_id} cihazından {log.led} LED durumu alındı "
        f"(paket #{log.sequence})."
    )


def command_log_message(command: DeviceCommand) -> str:
    return (
        f"{command.device_id} cihazına {command.komut} komutu gönderildi "
        f"({command.durum})."
    )


def readable_log_message(record, legacy_message) -> str:
    if record.encryption_version == 1:
        try:
            return decrypt_text(record.message) or ""
        except LogDecryptionError:
            logger.warning(
                "Encrypted log could not be decrypted (table=%s, id=%s)",
                record.__tablename__,
                record.id,
            )
            return UNREADABLE_ENCRYPTED_LOG
    return record.message if record.message is not None else legacy_message(record)


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
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                disconnected.append(connection)
        for connection in disconnected:
            self.disconnect(connection)


manager = ConnectionManager()


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


@app.get("/api/db-logs")
async def get_past_logs(limit: int = 50, db: Session = Depends(get_db)):
    logs = db.query(LedLog).order_by(LedLog.id.desc()).limit(limit).all()
    return [
        {
            "id": log.id,
            "device_id": log.device_id,
            "led": log.led,
            "sequence": log.sequence,
            "device_timestamp": log.device_timestamp,
            "nonce": log.nonce,
            "server_received_at": log.server_received_at,
        }
        for log in logs
    ]


@app.get("/api/iot/devices/{device_id}/state")
async def get_device_state(device_id: str, db: Session = Depends(get_db)):
    last_log = (
        db.query(LedLog)
        .filter(LedLog.device_id == device_id)
        .order_by(LedLog.id.desc())
        .first()
    )
    now_ms = int(time.time() * 1000)
    if not last_log:
        return {
            "deviceId": device_id,
            "led": "off",
            "online": False,
            "sequence": 0,
            "deviceTimestamp": None,
            "serverReceivedAt": None,
        }
    return {
        "deviceId": last_log.device_id,
        "led": last_log.led,
        "online": now_ms - last_log.server_received_at < 30000,
        "sequence": last_log.sequence,
        "deviceTimestamp": last_log.device_timestamp,
        "serverReceivedAt": last_log.server_received_at,
    }


@app.post("/api/iot/led-state")
async def receive_led_state(req: IoTRequest, db: Session = Depends(get_db)):
    global last_sequence
    if req.deviceId != DEVICE_ID:
        raise HTTPException(status_code=400, detail="Geçersiz cihaz kimliği")
    if req.led not in {"blue", "red", "off"}:
        raise HTTPException(status_code=400, detail="Geçersiz LED durumu")

    signed_value = f"{req.deviceId}|{req.led}|{req.sequence}|{req.timestamp}|{req.nonce}"
    expected_signature = hmac.new(
        DEVICE_SECRET.encode("utf-8"), signed_value.encode("utf-8"), hashlib.sha256
    ).hexdigest()
    if not hmac.compare_digest(expected_signature, req.signature):
        raise HTTPException(status_code=401, detail="Geçersiz imza")

    now_ms = int(time.time() * 1000)
    if abs(now_ms - req.timestamp) > NONCE_TTL_MS:
        raise HTTPException(status_code=400, detail="Zaman aşımı")
    expired_nonces = [nonce for nonce, created_at in used_nonces.items() if now_ms - created_at > NONCE_TTL_MS]
    for nonce in expired_nonces:
        del used_nonces[nonce]
    if req.nonce in used_nonces:
        raise HTTPException(status_code=400, detail="Nonce daha önce kullanılmış")
    latest_log = db.query(LedLog.sequence).order_by(LedLog.sequence.desc()).first()
    latest_persisted_sequence = latest_log[0] if latest_log else 0
    if req.sequence <= max(last_sequence, latest_persisted_sequence):
        raise HTTPException(status_code=400, detail="Geçersiz sıra numarası")

    last_sequence = req.sequence
    used_nonces[req.nonce] = now_ms
    server_received_at = now_ms
    checksum = md5_checksum(
        led_log_payload(
            device_id=req.deviceId,
            led=req.led,
            sequence=req.sequence,
            device_timestamp=req.timestamp,
            nonce=req.nonce,
            server_received_at=server_received_at,
        )
    )
    log = LedLog(
        device_id=req.deviceId,
        led=req.led,
        sequence=req.sequence,
        device_timestamp=req.timestamp,
        nonce=req.nonce,
        server_received_at=server_received_at,
        encryption_version=1,
        md5_checksum=checksum,
    )
    log.message = encrypt_text(device_log_message(log))
    db.add(log)
    db.commit()

    event = {
        "type": "device-state",
        "deviceId": req.deviceId,
        "led": req.led,
        "online": True,
        "sequence": req.sequence,
        "deviceTimestamp": req.timestamp,
        "serverReceivedAt": server_received_at,
    }
    await manager.broadcast(event)
    return {"ok": True, **event}


@app.post("/api/iot/commands")
async def create_command(req: CommandRequest, db: Session = Depends(get_db)):
    if req.device_id != DEVICE_ID:
        raise HTTPException(status_code=400, detail="Geçersiz cihaz kimliği")
    if req.komut not in {"MAVI_YAK", "KIRMIZI_YAK"}:
        raise HTTPException(status_code=400, detail="Geçersiz komut")
    olusturulma_zamani = int(time.time() * 1000)
    checksum = md5_checksum(
        device_command_payload(
            device_id=req.device_id,
            komut=req.komut,
            olusturulma_zamani=olusturulma_zamani,
        )
    )
    command = DeviceCommand(
        device_id=req.device_id,
        komut=req.komut,
        durum="bekliyor",
        olusturulma_zamani=olusturulma_zamani,
        encryption_version=1,
        md5_checksum=checksum,
    )
    command.message = encrypt_text(command_log_message(command))
    db.add(command)
    db.commit()
    return {"mesaj": "Komut sıraya alındı", "komut": req.komut}


@app.get("/api/iot/commands/pending/{device_id}")
async def get_pending_commands(device_id: str, db: Session = Depends(get_db)):
    command = (
        db.query(DeviceCommand)
        .filter(DeviceCommand.device_id == device_id, DeviceCommand.durum == "bekliyor")
        .first()
    )
    return {"id": command.id, "komut": command.komut} if command else {"id": None, "komut": "YOK"}


@app.post("/api/iot/commands/complete/{command_id}")
async def complete_command(command_id: int, db: Session = Depends(get_db)):
    command = db.query(DeviceCommand).filter(DeviceCommand.id == command_id).first()
    if not command:
        raise HTTPException(status_code=404, detail="Komut bulunamadı")
    command.durum = "tamamlandi"
    db.commit()
    return {"mesaj": "Komut tamamlandı olarak işaretlendi"}


@app.get("/api/stats")
async def get_stats(db: Session = Depends(get_db)):
    now = datetime.now()
    data = []
    for i in range(5, -1, -1):
        time_point = now - timedelta(seconds=i * 3)
        start_ms = int((time_point - timedelta(seconds=3)).timestamp() * 1000)
        end_ms = int(time_point.timestamp() * 1000)
        state = (
            db.query(LedLog)
            .filter(LedLog.server_received_at > start_ms, LedLog.server_received_at <= end_ms)
            .order_by(LedLog.id.desc())
            .first()
        )
        command_count = db.query(DeviceCommand).filter(
            DeviceCommand.olusturulma_zamani > start_ms,
            DeviceCommand.olusturulma_zamani <= end_ms,
        ).count()
        data.append({
            "time": time_point.strftime("%H:%M:%S"),
            "gelenSinyal": {"red": 95, "blue": 65, "off": 20}.get(state.led, 0) if state else 0,
            "gidenKomut": 80 if command_count else 0,
        })
    return data


@app.get("/api/logs")
async def get_logs(limit: int = 50, db: Session = Depends(get_db)):
    device_logs = db.query(LedLog).order_by(LedLog.server_received_at.desc()).limit(limit).all()
    command_logs = db.query(DeviceCommand).order_by(DeviceCommand.olusturulma_zamani.desc()).limit(limit).all()
    events = [
        {
            "timestamp": log.server_received_at,
            "time": datetime.fromtimestamp(log.server_received_at / 1000).strftime("%H:%M:%S"),
            "type": "ESP32 -> DASHBOARD",
            "message": readable_log_message(log, device_log_message),
            "md5_checksum": getattr(log, "md5_checksum", None),
        }
        for log in device_logs
    ] + [
        {
            "timestamp": command.olusturulma_zamani,
            "time": datetime.fromtimestamp(command.olusturulma_zamani / 1000).strftime("%H:%M:%S"),
            "type": "DASHBOARD -> ESP32",
            "message": readable_log_message(command, command_log_message),
            "md5_checksum": getattr(command, "md5_checksum", None),
        }
        for command in command_logs
    ]
    return sorted(events, key=lambda event: event["timestamp"], reverse=True)[:limit]
