"""
Encrypted SQLAlchemy types for secrets stored in the database.
"""

import base64
import hashlib
import json
import os
from functools import lru_cache
from typing import Any

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import JSON, Text, text
from sqlalchemy.engine import Connection
from sqlalchemy.types import TypeDecorator

ENCRYPTED_PREFIX = "enc::"
SENSITIVE_COLUMNS = {
    "price_alerts": ("slack_webhook_url", "discord_webhook_url"),
    "store_connections": ("api_key", "api_secret"),
    "users": ("notification_prefs",),
}


def _get_encryption_secret() -> str:
    secret = (os.getenv("FIELD_ENCRYPTION_KEY") or os.getenv("SECRET_KEY") or "").strip()
    if not secret:
        raise RuntimeError("FIELD_ENCRYPTION_KEY or SECRET_KEY must be set to encrypt sensitive fields")
    return secret


@lru_cache(maxsize=1)
def _get_cipher() -> Fernet:
    digest = hashlib.sha256(_get_encryption_secret().encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt_secret(value: str | None) -> str | None:
    if value is None:
        return None
    if value == "" or value.startswith(ENCRYPTED_PREFIX):
        return value

    token = _get_cipher().encrypt(value.encode("utf-8")).decode("utf-8")
    return f"{ENCRYPTED_PREFIX}{token}"


def decrypt_secret(value: Any) -> Any:
    if value is None or value == "":
        return value
    if not isinstance(value, str) or not value.startswith(ENCRYPTED_PREFIX):
        return value

    token = value[len(ENCRYPTED_PREFIX):]
    try:
        return _get_cipher().decrypt(token.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise RuntimeError(
            "Failed to decrypt stored sensitive field. Check FIELD_ENCRYPTION_KEY or SECRET_KEY."
        ) from exc


class EncryptedString(TypeDecorator):
    """Store strings encrypted at rest with plaintext fallback for legacy rows."""

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect) -> str | None:
        return encrypt_secret(value)

    def process_result_value(self, value: Any, dialect) -> Any:
        return decrypt_secret(value)


class EncryptedJSON(TypeDecorator):
    """Store JSON as an encrypted string while still reading legacy JSON objects."""

    impl = JSON
    cache_ok = True

    def process_bind_param(self, value: Any, dialect) -> str | None:
        if value is None:
            return None
        return encrypt_secret(json.dumps(value))

    def process_result_value(self, value: Any, dialect) -> Any:
        if value is None:
            return None
        if isinstance(value, (dict, list)):
            return value

        decrypted = decrypt_secret(value)
        if decrypted in (None, ""):
            return None

        return json.loads(decrypted)


def encrypt_existing_sensitive_values(connection: Connection) -> int:
    """
    Rewrite legacy plaintext secrets in place without changing the schema.
    Returns the number of rows updated.
    """
    updated_rows = 0

    for table_name, columns in SENSITIVE_COLUMNS.items():
        selected_columns = ", ".join(columns)
        rows = connection.execute(
            text(f"SELECT id, {selected_columns} FROM {table_name}")
        ).mappings()

        for row in rows:
            params = {"id": row["id"]}
            assignments = []

            for column_name in columns:
                value = row[column_name]
                if value in (None, ""):
                    continue

                if table_name == "users" and column_name == "notification_prefs":
                    if isinstance(value, (dict, list)):
                        raw_value = json.dumps(value)
                    else:
                        raw_value = str(value)
                        try:
                            decoded_value = json.loads(raw_value)
                        except json.JSONDecodeError:
                            decoded_value = raw_value

                        if isinstance(decoded_value, str):
                            raw_value = decoded_value
                        elif isinstance(decoded_value, (dict, list)):
                            raw_value = json.dumps(decoded_value)
                        else:
                            raw_value = str(decoded_value)
                elif isinstance(value, (dict, list)):
                    raw_value = json.dumps(value)
                else:
                    raw_value = str(value)

                if raw_value.startswith(ENCRYPTED_PREFIX):
                    continue

                encrypted_value = encrypt_secret(raw_value)
                if table_name == "users" and column_name == "notification_prefs":
                    params[column_name] = json.dumps(encrypted_value)
                else:
                    params[column_name] = encrypted_value

                assignments.append(f"{column_name} = :{column_name}")

            if not assignments:
                continue

            connection.execute(
                text(
                    f"UPDATE {table_name} "
                    f"SET {', '.join(assignments)} "
                    f"WHERE id = :id"
                ),
                params,
            )
            updated_rows += 1

    return updated_rows
