"""
Unit Tests — EncryptionService

Tests encrypt/decrypt round-trips, edge cases, and graceful
degradation when the cryptography package is unavailable.
"""

import os
import pytest
from services.encryption_service import EncryptionService, encryption


class TestEncryptionRoundTrip:

    def test_encrypt_decrypt_roundtrip(self):
        """Encrypted value decrypts back to the original."""
        svc = EncryptionService()
        original = "my-super-secret-token"
        ciphertext = svc.encrypt(original)
        assert svc.decrypt(ciphertext) == original

    def test_ciphertext_is_different_from_plaintext(self):
        """Encrypted value must not equal the original."""
        svc = EncryptionService()
        original = "plaintext-value"
        ciphertext = svc.encrypt(original)
        if svc.available:
            assert ciphertext != original
        else:
            # If cryptography not installed, value is unchanged (logged as warning)
            assert ciphertext == original

    def test_encrypt_empty_string(self):
        """Encrypting an empty string should not raise."""
        svc = EncryptionService()
        ciphertext = svc.encrypt("")
        result = svc.decrypt(ciphertext)
        assert result == ""

    def test_encrypt_long_string(self):
        """Long tokens (like Shopify access tokens) round-trip correctly."""
        svc = EncryptionService()
        long_token = "shpat_" + "x" * 40
        assert svc.decrypt(svc.encrypt(long_token)) == long_token

    def test_encrypt_unicode_value(self):
        """Unicode strings round-trip correctly."""
        svc = EncryptionService()
        value = "שלום עולם"
        assert svc.decrypt(svc.encrypt(value)) == value

    def test_two_encryptions_differ(self):
        """Fernet uses nonce — same plaintext produces different ciphertext each time."""
        svc = EncryptionService()
        if not svc.available:
            pytest.skip("cryptography not available")
        value = "same-value"
        c1 = svc.encrypt(value)
        c2 = svc.encrypt(value)
        assert c1 != c2  # Different nonce each time
        assert svc.decrypt(c1) == svc.decrypt(c2) == value

    def test_decrypt_invalid_token_returns_input(self):
        """Decrypting garbage returns the original (legacy plaintext handling)."""
        svc = EncryptionService()
        if not svc.available:
            pytest.skip("cryptography not available")
        result = svc.decrypt("not-a-valid-fernet-token")
        assert result == "not-a-valid-fernet-token"

    def test_decrypt_plaintext_legacy_row(self):
        """Plain-text rows (before encryption was added) return unchanged."""
        svc = EncryptionService()
        result = svc.decrypt("plain-api-key-123")
        assert result == "plain-api-key-123"

    def test_module_singleton_available(self):
        """Module-level singleton is initialised correctly."""
        assert encryption is not None
        assert hasattr(encryption, "encrypt")
        assert hasattr(encryption, "decrypt")

    def test_multiple_different_values(self):
        """Different secrets round-trip independently."""
        svc = EncryptionService()
        pairs = [
            ("shopify-token-abc", "shopify-token-abc"),
            ("woo-key-xyz", "woo-key-xyz"),
            ("another-secret", "another-secret"),
        ]
        for plaintext, expected in pairs:
            assert svc.decrypt(svc.encrypt(plaintext)) == expected

    def test_available_property_is_bool(self):
        svc = EncryptionService()
        assert isinstance(svc.available, bool)

    def test_custom_key_from_env(self, monkeypatch):
        """Service reads ENCRYPTION_KEY from environment."""
        from cryptography.fernet import Fernet
        key = Fernet.generate_key().decode()
        monkeypatch.setenv("ENCRYPTION_KEY", key)
        svc = EncryptionService()
        assert svc.available
        value = "test-with-custom-key"
        assert svc.decrypt(svc.encrypt(value)) == value
