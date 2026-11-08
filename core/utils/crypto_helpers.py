"""
Cryptographic and Byte Utility Functions
"""
import base64
import os
import hmac
import hashlib


def generate_salt(length: int = 16) -> bytes:
    """Generate cryptographically secure random bytes."""
    return os.urandom(length)


def bytes_to_b64(data: bytes) -> str:
    """Encode bytes into URL-safe or standard Base64 string."""
    return base64.b64encode(data).decode("utf-8")


def b64_to_bytes(b64_str: str) -> bytes:
    """Decode standard or URL-safe Base64 string into bytes."""
    return base64.b64decode(b64_str.encode("utf-8"))


def sha256_hash(data: bytes) -> str:
    """Compute SHA-256 hexadecimal hash string for binary data."""
    return hashlib.sha256(data).hexdigest()


def sha256_hash_file(file_path: str) -> str:
    """Compute SHA-256 hash for a disk file using chunks."""
    h = hashlib.sha256()
    with open(file_path, "rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest()


def constant_time_compare(val1: bytes, val2: bytes) -> bool:
    """Perform constant-time comparison to prevent timing attacks."""
    return hmac.compare_digest(val1, val2)
