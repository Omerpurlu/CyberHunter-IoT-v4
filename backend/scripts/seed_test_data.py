"""PostgreSQL'e CyberHunter sanal test verileri ekler.

Bu script yalnızca ``esp32-test-01`` cihaz kimliğini kullanır. Mevcut test
kayıtlarını hiçbir zaman silmez; kayıt varsa devam etmek için açıkça
``--append`` verilmesini ister.
"""

from __future__ import annotations

import argparse
import random
import sys
import time
import uuid
from pathlib import Path

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

BACKEND_DIR = Path(__file__).resolve().parents[1]
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from crypto_utils import encrypt_text  # noqa: E402
from database import SessionLocal  # noqa: E402
from hash_utils import device_command_payload, led_log_payload, md5_checksum  # noqa: E402
from models import DeviceCommand, LedLog  # noqa: E402

TEST_DEVICE_ID = "esp32-test-01"
DEFAULT_LOG_COUNT = 50
DEFAULT_COMMAND_COUNT = 20
MAX_LOG_COUNT = 50
MAX_COMMAND_COUNT = 20
ENCRYPTION_VERSION = 1
DAY_MS = 24 * 60 * 60 * 1000

LED_STATES = ("red", "blue", "off")
COMMANDS = ("MAVI_YAK", "KIRMIZI_YAK")
COMMAND_STATUSES = ("bekliyor", "tamamlandi")


def bounded_count(value: str, maximum: int) -> int:
    try:
        count = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("tam sayı olmalıdır") from exc
    if not 0 <= count <= maximum:
        raise argparse.ArgumentTypeError(f"0 ile {maximum} arasında olmalıdır")
    return count


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="CyberHunter PostgreSQL veritabanına güvenli sanal test verisi ekler."
    )
    parser.add_argument(
        "--logs",
        type=lambda value: bounded_count(value, MAX_LOG_COUNT),
        default=DEFAULT_LOG_COUNT,
        help=f"eklenecek LED logu sayısı (varsayılan: {DEFAULT_LOG_COUNT}, en fazla: {MAX_LOG_COUNT})",
    )
    parser.add_argument(
        "--commands",
        type=lambda value: bounded_count(value, MAX_COMMAND_COUNT),
        default=DEFAULT_COMMAND_COUNT,
        help=(
            "eklenecek cihaz komutu sayısı "
            f"(varsayılan: {DEFAULT_COMMAND_COUNT}, en fazla: {MAX_COMMAND_COUNT})"
        ),
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="esp32-test-01 kayıtları zaten varsa silmeden yeni kayıtlar ekle",
    )
    parser.add_argument(
        "--live",
        action="store_true",
        help="kayıt zamanlarını son 24 saate dağıtmak yerine güncel sistem zamanını kullan",
    )
    return parser.parse_args()


def distributed_timestamps(count: int, now_ms: int, rng: random.Random) -> list[int]:
    """Son 24 saate yayılmış, artan ve benzersiz milisaniye değerleri üretir."""
    if count == 0:
        return []
    bucket_ms = DAY_MS // count
    start_ms = now_ms - DAY_MS
    values = [
        start_ms + index * bucket_ms + rng.randrange(bucket_ms)
        for index in range(count)
    ]
    return sorted(values)


def varied_values(
    choices: tuple[str, ...], count: int, rng: random.Random
) -> list[str]:
    """Mümkün olduğunda her seçeneği içeren, karıştırılmış değerler üretir."""
    values = [choices[index % len(choices)] for index in range(count)]
    rng.shuffle(values)
    return values


def led_message(log: LedLog) -> str:
    return (
        f"{log.device_id} cihazından {log.led} LED durumu alındı "
        f"(paket #{log.sequence})."
    )


def command_message(command: DeviceCommand) -> str:
    return (
        f"{command.device_id} cihazına {command.komut} komutu gönderildi "
        f"({command.durum})."
    )


def seed_data(args: argparse.Namespace) -> tuple[int, int]:
    rng = random.SystemRandom()
    now_ms = int(time.time() * 1000)
    session = SessionLocal()

    try:
        existing_logs = (
            session.query(LedLog)
            .filter(LedLog.device_id == TEST_DEVICE_ID)
            .count()
        )
        existing_commands = (
            session.query(DeviceCommand)
            .filter(DeviceCommand.device_id == TEST_DEVICE_ID)
            .count()
        )
        if (existing_logs or existing_commands) and not args.append:
            raise RuntimeError(
                f"{TEST_DEVICE_ID} için {existing_logs} log ve "
                f"{existing_commands} komut zaten var. Hiçbir kayıt silinmedi. "
                "Silmeden yeni veri eklemek için --append kullanın."
            )

        latest_sequence = session.query(func.max(LedLog.sequence)).scalar() or 0
        log_timestamps = (
            [now_ms] * args.logs
            if args.live
            else distributed_timestamps(args.logs, now_ms, rng)
        )
        command_timestamps = (
            [now_ms] * args.commands
            if args.live
            else distributed_timestamps(args.commands, now_ms, rng)
        )
        led_states = varied_values(LED_STATES, args.logs, rng)
        command_names = varied_values(COMMANDS, args.commands, rng)
        command_statuses = varied_values(COMMAND_STATUSES, args.commands, rng)
        generated_nonces: set[str] = set()

        for offset, (timestamp_ms, led_state) in enumerate(
            zip(log_timestamps, led_states), start=1
        ):
            nonce = uuid.uuid4().hex
            while nonce in generated_nonces:
                nonce = uuid.uuid4().hex
            generated_nonces.add(nonce)
            sequence = latest_sequence + offset
            server_received_at = min(
                timestamp_ms + rng.randrange(25, 1_501), now_ms
            )
            checksum = md5_checksum(
                led_log_payload(
                    device_id=TEST_DEVICE_ID,
                    led=led_state,
                    sequence=sequence,
                    device_timestamp=timestamp_ms,
                    nonce=nonce,
                    server_received_at=server_received_at,
                )
            )

            log = LedLog(
                device_id=TEST_DEVICE_ID,
                led=led_state,
                sequence=sequence,
                device_timestamp=timestamp_ms,
                nonce=nonce,
                server_received_at=server_received_at,
                encryption_version=ENCRYPTION_VERSION,
                md5_checksum=checksum,
            )
            log.message = encrypt_text(led_message(log))
            session.add(log)

        for timestamp_ms, command_name, command_status in zip(
            command_timestamps, command_names, command_statuses
        ):
            checksum = md5_checksum(
                device_command_payload(
                    device_id=TEST_DEVICE_ID,
                    komut=command_name,
                    olusturulma_zamani=timestamp_ms,
                )
            )
            command = DeviceCommand(
                device_id=TEST_DEVICE_ID,
                komut=command_name,
                durum=command_status,
                olusturulma_zamani=timestamp_ms,
                encryption_version=ENCRYPTION_VERSION,
                md5_checksum=checksum,
            )
            command.message = encrypt_text(command_message(command))
            session.add(command)

        session.commit()
        return args.logs, args.commands
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def main() -> int:
    args = parse_args()
    try:
        log_count, command_count = seed_data(args)
    except (RuntimeError, SQLAlchemyError) as exc:
        print(f"HATA: {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"HATA: {type(exc).__name__}; transaction geri alındı.", file=sys.stderr)
        return 1

    print(
        f"Tamamlandı: {TEST_DEVICE_ID} için {log_count} LED logu ve "
        f"{command_count} cihaz komutu eklendi."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
