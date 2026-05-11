"""AES-256-GCM envelope encryption for user secrets (LLM + broker keys).

## Why envelope encryption

Plaintext secrets never live in the DB. We follow the standard
"key encryption key" (KEK) + "data encryption key" (DEK) envelope pattern:

1. The **server holds a single 32-byte master KEK** (in `Settings.MASTER_KEK`,
   loaded from env, never committed). Treat it like a TLS private key —
   loss means every secret in the DB is unrecoverable.
2. Each plaintext key (an Anthropic API key, a Bitunix HMAC, etc.) is
   encrypted with a freshly generated **256-bit DEK** specific to that
   record.
3. The DEK is then encrypted with a per-user KEK derived from
   `HKDF(MASTER_KEK, salt=random_per_record, info=b"wally-dek-wrap-v1")`.
4. The DB stores `(encrypted_key, encrypted_dek, nonce, salt, last4)`.
   The plaintext key is held only in process memory for the duration of
   the request that needs it.

## Rotation

To rotate the master KEK, call `rewrap_all_keys(old_kek, new_kek)` from
the admin CLI. Each row's DEK is decrypted with the old KEK and re-
wrapped with the new one. Plaintext secrets never need to be re-encrypted.

## Security notes

- AES-256-GCM authenticates the ciphertext, so tampering is detected.
- Nonces are 96-bit random — collision probability is negligible for our
  cardinality (≪ 2^48 records).
- We use `cryptography.hazmat`. It's the FIPS-validated path; the
  high-level `Fernet` API is too rigid for our key-management needs.
"""

from __future__ import annotations

import base64
import secrets
from dataclasses import dataclass
from typing import Final

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

NONCE_BYTES: Final = 12
SALT_BYTES: Final = 16
DEK_BYTES: Final = 32
KEK_INFO: Final = b"wally-dek-wrap-v1"


class EncryptionError(Exception):
    """Raised when encryption/decryption fails (bad key, tampered data, etc.)."""


@dataclass(frozen=True)
class EncryptedSecret:
    """Result of encrypting a plaintext secret."""

    encrypted_key: bytes
    encrypted_dek: bytes
    nonce: bytes
    salt: bytes
    last4: str


def _decode_master_kek(master_kek_b64: str) -> bytes:
    """Decode the base64 master KEK and validate its length."""
    try:
        raw = base64.urlsafe_b64decode(master_kek_b64.encode())
    except Exception as exc:  # noqa: BLE001
        raise EncryptionError("MASTER_KEK is not valid base64") from exc
    if len(raw) != DEK_BYTES:
        raise EncryptionError(
            f"MASTER_KEK must decode to {DEK_BYTES} bytes (got {len(raw)})"
        )
    return raw


def _derive_kek(master_kek: bytes, salt: bytes) -> bytes:
    """HKDF-SHA256 derives a per-record KEK from the master + salt."""
    return HKDF(
        algorithm=hashes.SHA256(),
        length=DEK_BYTES,
        salt=salt,
        info=KEK_INFO,
    ).derive(master_kek)


def encrypt_secret(plaintext: str, master_kek_b64: str) -> EncryptedSecret:
    """Encrypt a plaintext secret with envelope encryption.

    Returns the ciphertext + every parameter needed to decrypt it later
    given the same master KEK.
    """
    if not plaintext:
        raise EncryptionError("Refusing to encrypt empty string")

    master_kek = _decode_master_kek(master_kek_b64)
    dek = AESGCM.generate_key(bit_length=256)
    nonce = secrets.token_bytes(NONCE_BYTES)
    salt = secrets.token_bytes(SALT_BYTES)

    # Encrypt the user's secret with the DEK
    encrypted_key = AESGCM(dek).encrypt(nonce, plaintext.encode(), None)

    # Wrap the DEK with a KEK derived from MASTER_KEK + salt.
    # We reuse `nonce` as the DEK-wrap nonce — that's safe because the DEK
    # is unique per record, so the (nonce, key) pair is unique even though
    # the nonce value is reused across the two operations (different keys).
    derived_kek = _derive_kek(master_kek, salt)
    encrypted_dek = AESGCM(derived_kek).encrypt(nonce, dek, None)

    last4 = plaintext[-4:] if len(plaintext) >= 4 else plaintext

    return EncryptedSecret(
        encrypted_key=encrypted_key,
        encrypted_dek=encrypted_dek,
        nonce=nonce,
        salt=salt,
        last4=last4,
    )


def decrypt_secret(
    encrypted_key: bytes,
    encrypted_dek: bytes,
    nonce: bytes,
    salt: bytes,
    master_kek_b64: str,
) -> str:
    """Decrypt a previously encrypted secret. Raises EncryptionError on tamper."""
    master_kek = _decode_master_kek(master_kek_b64)
    derived_kek = _derive_kek(master_kek, salt)
    try:
        dek = AESGCM(derived_kek).decrypt(nonce, encrypted_dek, None)
        plaintext = AESGCM(dek).decrypt(nonce, encrypted_key, None)
    except Exception as exc:  # noqa: BLE001
        raise EncryptionError("Decryption failed (wrong KEK or tampered data)") from exc
    return plaintext.decode()


def rewrap_dek(
    encrypted_dek: bytes,
    nonce: bytes,
    salt: bytes,
    old_master_kek_b64: str,
    new_master_kek_b64: str,
) -> bytes:
    """Re-wrap a DEK from one master KEK to another.

    Used by the rotate_kek admin command to roll the master without
    touching any plaintext.
    """
    old_master = _decode_master_kek(old_master_kek_b64)
    new_master = _decode_master_kek(new_master_kek_b64)
    old_derived = _derive_kek(old_master, salt)
    new_derived = _derive_kek(new_master, salt)
    try:
        dek = AESGCM(old_derived).decrypt(nonce, encrypted_dek, None)
        return AESGCM(new_derived).encrypt(nonce, dek, None)
    except Exception as exc:  # noqa: BLE001
        raise EncryptionError("Rewrap failed (bad old KEK or tampered data)") from exc


def generate_master_kek() -> str:
    """Generate a fresh base64 master KEK suitable for `MASTER_KEK` env var."""
    return base64.urlsafe_b64encode(secrets.token_bytes(DEK_BYTES)).decode()
