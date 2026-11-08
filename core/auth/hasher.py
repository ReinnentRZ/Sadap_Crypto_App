"""
AeroSat GroundStation - Cryptographic Password Hasher
Implements PBKDF2-HMAC-SHA256 with per-user salt and constant-time comparison.
"""
import hashlib
import hmac
import os
import secrets
import string
from config.settings import (
    PASSWORD_SALT_BYTES,
    PASSWORD_KDF_ITERATIONS,
)
from core.utils.crypto_helpers import constant_time_compare


def hash_password(
    password: str,
    salt: bytes | None = None,
    iterations: int = PASSWORD_KDF_ITERATIONS
) -> str:
    """
    Hash a plaintext password using PBKDF2-HMAC-SHA256.
    Returns formatted string: pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>
    """
    if not password:
        raise ValueError("Password cannot be empty.")

    if salt is None:
        salt = os.urandom(PASSWORD_SALT_BYTES)

    # Derive 32-byte (256-bit) key
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        iterations,
        dklen=32
    )

    salt_hex = salt.hex()
    hash_hex = dk.hex()
    return f"pbkdf2_sha256${iterations}${salt_hex}${hash_hex}"


def verify_password(password: str, stored_hash: str) -> bool:
    """
    Verify a plaintext password against a stored formatted hash string.
    Uses constant-time comparison to prevent timing side-channel attacks.
    """
    if not password or not stored_hash:
        return False

    try:
        parts = stored_hash.split("$")
        if len(parts) != 4 or parts[0] != "pbkdf2_sha256":
            return False

        iterations = int(parts[1])
        salt = bytes.fromhex(parts[2])
        expected_hash = bytes.fromhex(parts[3])

        # Compute hash with same parameters
        dk = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations,
            dklen=len(expected_hash)
        )

        return constant_time_compare(dk, expected_hash)
    except Exception:
        return False


def generate_secure_passcode(length: int = 16) -> str:
    """Generate a high-entropy random passphrase for access credentials."""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(alphabet) for _ in range(length))
