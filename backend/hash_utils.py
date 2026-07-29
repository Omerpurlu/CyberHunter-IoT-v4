"""Eğitimsel, güvenlik dışı kayıt parmak izleri için MD5 yardımcıları.

Bu modüldeki MD5 değerleri parola saklama, kimlik doğrulama, imza doğrulama
veya herhangi bir güvenlik kararı için kullanılmamalıdır. Payload fonksiyonları
yalnızca açıkça listelenen, gizli olmayan kayıt alanlarını içerir.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from typing import TypeAlias

JsonScalar: TypeAlias = str | int | float | bool | None
FingerprintPayload: TypeAlias = dict[str, JsonScalar]


def canonical_json(payload: Mapping[str, JsonScalar]) -> str:
    """Payload'u kararlı, boşluksuz bir JSON metnine dönüştürür."""
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def md5_checksum(payload: Mapping[str, JsonScalar]) -> str:
    """Güvenlik amacı taşımayan 32 karakterlik kayıt parmak izi üretir."""
    canonical_value = canonical_json(payload)
    return hashlib.md5(
        canonical_value.encode("utf-8"),
        usedforsecurity=False,
    ).hexdigest()


def led_log_payload(
    *,
    device_id: str,
    led: str,
    sequence: int,
    device_timestamp: int,
    nonce: str,
    server_received_at: int,
) -> FingerprintPayload:
    """Bir LED kaydının gizli olmayan, değişmez alanlarını hazırlar."""
    return {
        "record_type": "led_log",
        "device_id": device_id,
        "led": led,
        "sequence": int(sequence),
        "device_timestamp": int(device_timestamp),
        "nonce": nonce,
        "server_received_at": int(server_received_at),
    }


def device_command_payload(
    *,
    device_id: str,
    komut: str,
    olusturulma_zamani: int,
) -> FingerprintPayload:
    """Bir komut kaydının durum ve gizli veri içermeyen alanlarını hazırlar."""
    return {
        "record_type": "device_command",
        "device_id": device_id,
        "komut": komut,
        "olusturulma_zamani": int(olusturulma_zamani),
    }
