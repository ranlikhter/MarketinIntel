"""
Encryption Service — symmetric AES-128 via Fernet (cryptography library)

Used to encrypt sensitive credentials stored in the database:
  - StoreConnection.api_key  (Shopify access_token / WC consumer_key)
  - StoreConnection.api_secret (WC consumer_secret)

Key management:
  - Set ENCRYPTION_KEY in the environment (base64-urlsafe 32-byte key).
  - Generate one with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
  - In development, a deterministic fallback is used and a warning is emitted.

Usage (in SQLAlchemy model or service):
    from services.encryption_service import encryption

    ciphertext = encryption.encrypt("my-secret")   # → str
    plaintext  = encryption.decrypt(ciphertext)    # → str
"""

import base64
import logging
import os

log = logging.getLogger(__name__)

_ENV_KEY = "ENCRYPTION_KEY"
_DEV_FALLBACK = b"ZmFsbGJhY2stZGV2LW9ubHkta2V5LTMyYnl0ZXMA"  # NOT safe for production


def _load_fernet():
    try:
        from cryptography.fernet import Fernet, InvalidToken  # noqa: F401
    except ImportError:
        log.warning(
            "cryptography package not installed — encryption disabled. "
            "Run: pip install cryptography"
        )
        return None, None

    raw = os.getenv(_ENV_KEY)
    if raw:
        key = raw.encode() if isinstance(raw, str) else raw
    else:
        log.warning(
            "ENCRYPTION_KEY not set — using insecure development fallback. "
            "Set ENCRYPTION_KEY in production!"
        )
        # Pad/truncate to valid Fernet key length (32 bytes → 44 base64 chars)
        key = base64.urlsafe_b64encode(_DEV_FALLBACK[:32])

    try:
        f = Fernet(key)
        return f, InvalidToken
    except Exception as exc:
        log.error("Failed to initialise Fernet with ENCRYPTION_KEY: %s", exc)
        return None, None


class EncryptionService:
    def __init__(self):
        self._fernet, self._InvalidToken = _load_fernet()

    @property
    def available(self) -> bool:
        return self._fernet is not None

    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string.

        Returns the ciphertext as a UTF-8 string (Fernet token).
        Returns the original plaintext unchanged if the cryptography package
        is not available (logged as a warning).
        """
        if not self._fernet:
            log.warning("Encryption unavailable — storing value in plaintext")
            return plaintext
        return self._fernet.encrypt(plaintext.encode()).decode()

    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt a Fernet-encrypted string.

        Returns the original plaintext.
        Returns the ciphertext unchanged if encryption is unavailable
        (handles legacy rows that were stored before encryption was enabled).
        """
        if not self._fernet:
            return ciphertext
        try:
            return self._fernet.decrypt(ciphertext.encode()).decode()
        except Exception:
            # Legacy plaintext value or wrong key — return as-is so the
            # application can still function during a key rotation window.
            log.warning("decrypt: could not decrypt value — returning raw (possible legacy row)")
            return ciphertext


# Module-level singleton
encryption = EncryptionService()
