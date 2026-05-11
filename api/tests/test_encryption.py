"""Tests for app.security.encryption.

Run with: `uv run pytest tests/test_encryption.py -v`
"""

from __future__ import annotations

import base64
import secrets

import pytest

from app.security.encryption import (
    EncryptionError,
    decrypt_secret,
    encrypt_secret,
    generate_master_kek,
    rewrap_dek,
)


@pytest.fixture
def master_kek() -> str:
    return generate_master_kek()


def test_roundtrip(master_kek: str) -> None:
    plaintext = "sk-ant-api03-test-12345-ABCDEFG"
    enc = encrypt_secret(plaintext, master_kek)

    # last4 is exposed for UI; the rest must be opaque bytes
    assert enc.last4 == "EFG"[-3:] or enc.last4 == plaintext[-4:]
    assert enc.last4 == plaintext[-4:]

    decrypted = decrypt_secret(
        enc.encrypted_key, enc.encrypted_dek, enc.nonce, enc.salt, master_kek
    )
    assert decrypted == plaintext


def test_different_nonces_each_call(master_kek: str) -> None:
    a = encrypt_secret("hello", master_kek)
    b = encrypt_secret("hello", master_kek)
    assert a.nonce != b.nonce
    assert a.salt != b.salt
    assert a.encrypted_key != b.encrypted_key


def test_wrong_master_kek_fails(master_kek: str) -> None:
    enc = encrypt_secret("secret", master_kek)
    other_kek = generate_master_kek()
    with pytest.raises(EncryptionError):
        decrypt_secret(
            enc.encrypted_key, enc.encrypted_dek, enc.nonce, enc.salt, other_kek
        )


def test_tampered_ciphertext_fails(master_kek: str) -> None:
    enc = encrypt_secret("secret", master_kek)
    bad_ct = bytearray(enc.encrypted_key)
    bad_ct[0] ^= 0xFF
    with pytest.raises(EncryptionError):
        decrypt_secret(bytes(bad_ct), enc.encrypted_dek, enc.nonce, enc.salt, master_kek)


def test_empty_plaintext_rejected(master_kek: str) -> None:
    with pytest.raises(EncryptionError):
        encrypt_secret("", master_kek)


def test_invalid_master_kek_length() -> None:
    bad = base64.urlsafe_b64encode(b"short").decode()
    with pytest.raises(EncryptionError):
        encrypt_secret("secret", bad)


def test_kek_rotation_preserves_plaintext(master_kek: str) -> None:
    plaintext = "sk-ant-api03-rotation-test"
    enc = encrypt_secret(plaintext, master_kek)

    new_kek = generate_master_kek()
    new_encrypted_dek = rewrap_dek(
        enc.encrypted_dek, enc.nonce, enc.salt, master_kek, new_kek
    )

    decrypted = decrypt_secret(
        enc.encrypted_key, new_encrypted_dek, enc.nonce, enc.salt, new_kek
    )
    assert decrypted == plaintext


def test_unicode_plaintext(master_kek: str) -> None:
    plaintext = "señalita-españa-🚀"
    enc = encrypt_secret(plaintext, master_kek)
    decrypted = decrypt_secret(
        enc.encrypted_key, enc.encrypted_dek, enc.nonce, enc.salt, master_kek
    )
    assert decrypted == plaintext


def test_generate_master_kek_is_decodable() -> None:
    kek = generate_master_kek()
    raw = base64.urlsafe_b64decode(kek.encode())
    assert len(raw) == 32


def test_large_secret(master_kek: str) -> None:
    plaintext = secrets.token_urlsafe(2048)
    enc = encrypt_secret(plaintext, master_kek)
    decrypted = decrypt_secret(
        enc.encrypted_key, enc.encrypted_dek, enc.nonce, enc.salt, master_kek
    )
    assert decrypted == plaintext
