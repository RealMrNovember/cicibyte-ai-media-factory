"""Symmetric encryption for secrets stored in the database (API keys, OAuth tokens)."""

import base64
from functools import lru_cache

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF


class SecretDecryptError(Exception):
    """Raised when a stored secret cannot be decrypted (wrong MF_SECRET_KEY or corrupt data)."""


@lru_cache(maxsize=8)
def _fernet(key: str) -> Fernet:
    derived = HKDF(algorithm=hashes.SHA256(), length=32, salt=None, info=b"mediafactory-secrets").derive(
        key.encode("utf-8")
    )
    return Fernet(base64.urlsafe_b64encode(derived))


def _default_key() -> str:
    from mediafactory.core.config import get_settings

    return get_settings().secret_key.get_secret_value()


def encrypt(plaintext: str, *, key: str | None = None) -> str:
    return _fernet(key or _default_key()).encrypt(plaintext.encode("utf-8")).decode("ascii")


def decrypt(token: str, *, key: str | None = None) -> str:
    try:
        return _fernet(key or _default_key()).decrypt(token.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError, UnicodeError) as exc:
        raise SecretDecryptError("stored secret cannot be decrypted; was MF_SECRET_KEY changed?") from exc
