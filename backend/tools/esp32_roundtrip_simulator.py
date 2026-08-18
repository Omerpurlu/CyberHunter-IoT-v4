"""HTTP-only ESP32 round-trip simulator; never connects to PostgreSQL."""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from uuid import uuid4


def request_json(method, url, payload=None, expected=(200,)):
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = Request(
        url,
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(request, timeout=10) as response:
            if response.status not in expected:
                raise RuntimeError(f"Beklenmeyen HTTP durumu: {response.status}")
            content = response.read()
            return response.status, json.loads(content) if content else None
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code}: {detail}") from exc
    except URLError as exc:
        raise RuntimeError(f"Backend bağlantısı kurulamadı: {exc.reason}") from exc


def run(base_url, device_id, poll_seconds):
    event_id = f"evt-roundtrip-{uuid4().hex}"
    payload = {
        "event_id": event_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "source_ip": "192.0.2.10",
        "destination_port": 22,
        "protocol": "ssh",
        "event_type": "malware_botnet",
        "command": "simulated round-trip",
        "tactic": "command_and_control",
        "input_risk_score": 90,
        "esp32_risk_score": 90,
        "esp32_decision": "warning",
        "esp32_processed": True,
        "device_id": device_id,
    }
    print("Test amaçlı ESP32 alanları içeren birleşik olay gönderiliyor...")
    request_json("POST", f"{base_url}/api/security-events", payload, (201,))

    _, events = request_json("GET", f"{base_url}/api/security-events?limit=200")
    if not any(item["event_id"] == event_id for item in events["items"]):
        raise RuntimeError("Olay GET /api/security-events içinde bulunamadı")
    print(f"Olay PostgreSQL/API döngüsünde doğrulandı: {event_id}")

    deadline = time.monotonic() + poll_seconds
    command = None
    while time.monotonic() < deadline:
        query = urlencode({"device_id": device_id})
        status_code, command = request_json(
            "GET",
            f"{base_url}/api/iot/commands/next?{query}",
            expected=(200, 204),
        )
        if status_code == 200:
            break
        time.sleep(0.5)
    if command is None:
        raise RuntimeError(
            "Pending komut bulunamadı; simulator için isolate_device üreten "
            "test policy yapılandırmasını etkinleştirin"
        )
    print(f"Komut alındı: {command['command_id']} / {command['action']}")

    relay_state = (
        "simulated_isolated"
        if command["action"] == "isolate_device"
        else "simulated_no_physical_action"
    )
    ack = {
        "device_id": device_id,
        "result": "executed",
        "executed_at": datetime.now(timezone.utc).isoformat(),
        "relay_state": relay_state,
        "ack_message": "Simulation completed successfully",
    }
    request_json(
        "POST",
        f"{base_url}/api/iot/commands/{command['command_id']}/ack",
        ack,
        (200,),
    )
    query = urlencode({"event_id": event_id})
    _, actions = request_json("GET", f"{base_url}/api/response-actions?{query}")
    if not any(item["status"] == "executed" for item in actions["items"]):
        raise RuntimeError("Response action executed durumuna geçmedi")
    print("ACK kaydedildi; response action executed olarak doğrulandı.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--device-id", default="esp32-cyberhunter-01")
    parser.add_argument("--poll-seconds", type=int, default=10)
    args = parser.parse_args()
    try:
        run(args.base_url.rstrip("/"), args.device_id, args.poll_seconds)
    except RuntimeError as exc:
        print(f"Round-trip başarısız: {exc}", file=sys.stderr)
        return 1
    print("ESP32 HTTP round-trip simülasyonu başarıyla tamamlandı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
