import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken, MultiFernet
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


class LogDecryptionError(ValueError):
    """Raised when an encrypted log cannot be decrypted with configured keys."""


def _build_fernet() -> MultiFernet:
    raw_keys = os.getenv("FERNET_KEYS")
    if not raw_keys:
        raise RuntimeError("Required environment variable is missing: FERNET_KEYS")

    keys = [key.strip() for key in raw_keys.split(",") if key.strip()]
    if not keys:
        raise RuntimeError("FERNET_KEYS must contain at least one Fernet key")

    try:
        fernets = [Fernet(key.encode("ascii")) for key in keys]
    except (ValueError, UnicodeEncodeError) as exc:
        raise RuntimeError("FERNET_KEYS contains an invalid Fernet key") from exc

    return MultiFernet(fernets)


_fernet = _build_fernet()


def encrypt_text(value: str | None) -> str | None:
    if value is None:
        return None
    return _fernet.encrypt(value.encode("utf-8")).decode("ascii")


def decrypt_text(token: str | None) -> str | None:
    if token is None:
        return None
    try:
        return _fernet.decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeDecodeError, UnicodeEncodeError) as exc:
        raise LogDecryptionError("Encrypted log could not be decrypted") from exc
