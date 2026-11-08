"""
AeroSat GroundStation - AES-256-GCM File Encryption Engine
Implements Authenticated Encryption with Associated Data (AEAD) with streaming
chunk support for large files, tamper detection, and original filename preservation.
"""
import io
import os
import struct
from pathlib import Path
from typing import Callable
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import InvalidTag

from config.settings import (
    AES_CHUNK_SIZE_BYTES,
    AES_KEY_SIZE_BYTES,
    AES_NONCE_SIZE_BYTES,
)
from core.utils.logger import get_logger

logger = get_logger("FileAES")

FILE_MAGIC = b"AERF"  # AeroSat Encrypted File
FILE_VERSION = 1
KDF_ITERATIONS = 100_000


def derive_aes_key(passphrase: str, salt: bytes) -> bytes:
    """Derive 256-bit symmetric key from passphrase and salt using PBKDF2-HMAC-SHA256."""
    if not passphrase:
        raise ValueError("Passphrase cannot be empty.")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=AES_KEY_SIZE_BYTES,
        salt=salt,
        iterations=KDF_ITERATIONS,
    )
    return kdf.derive(passphrase.encode("utf-8"))


def encrypt_file(
    input_path: str | Path,
    output_path: str | Path,
    passphrase: str,
    chunk_size: int = AES_CHUNK_SIZE_BYTES,
    progress_callback: Callable[[float], None] | None = None
) -> tuple[bool, str, dict]:
    """
    Encrypt a file using AES-256-GCM in streaming chunks.
    Header format: [MAGIC 4B] + [VERSION 1B] + [SALT 16B] + [NAME_LEN 2B] + [ORIGINAL_NAME]
    Chunk format: [CHUNK_INDEX 4B] + [IS_LAST 1B] + [NONCE 12B] + [DATA_LEN 4B] + [CIPHERTEXT + TAG]
    """
    in_file = Path(input_path)
    out_file = Path(output_path)

    if not in_file.exists():
        return False, f"Source file does not exist: {in_file}", {}

    try:
        total_size = in_file.stat().st_size
        salt = os.urandom(16)
        key = derive_aes_key(passphrase, salt)
        aesgcm = AESGCM(key)

        original_name_bytes = in_file.name.encode("utf-8")
        out_file.parent.mkdir(parents=True, exist_ok=True)

        processed_bytes = 0
        chunk_index = 0

        with open(in_file, "rb") as fin, open(out_file, "wb") as fout:
            # Write Header
            header = (
                FILE_MAGIC +
                struct.pack("!B", FILE_VERSION) +
                salt +
                struct.pack("!H", len(original_name_bytes)) +
                original_name_bytes
            )
            fout.write(header)

            # Handle empty file edge case
            if total_size == 0:
                nonce = os.urandom(AES_NONCE_SIZE_BYTES)
                aad = f"chunk_0_1".encode("utf-8")
                enc_chunk = aesgcm.encrypt(nonce, b"", aad)
                chunk_header = struct.pack("!IB12sI", 0, 1, nonce, len(enc_chunk))
                fout.write(chunk_header)
                fout.write(enc_chunk)
            else:
                while True:
                    chunk = fin.read(chunk_size)
                    if not chunk:
                        break

                    processed_bytes += len(chunk)
                    is_last = 1 if processed_bytes >= total_size else 0
                    nonce = os.urandom(AES_NONCE_SIZE_BYTES)
                    aad = f"chunk_{chunk_index}_{is_last}".encode("utf-8")

                    enc_chunk = aesgcm.encrypt(nonce, chunk, aad)

                    chunk_header = struct.pack("!IB12sI", chunk_index, is_last, nonce, len(enc_chunk))
                    fout.write(chunk_header)
                    fout.write(enc_chunk)

                    if progress_callback and total_size > 0:
                        progress_callback((processed_bytes / total_size) * 100.0)

                    chunk_index += 1
                    if is_last:
                        break

        metadata = {
            "original_filename": in_file.name,
            "original_size": total_size,
            "encrypted_size": out_file.stat().st_size,
            "chunks_count": chunk_index if total_size > 0 else 1,
            "algorithm": "AES-256-GCM",
        }
        return True, "File encrypted successfully.", metadata

    except Exception as e:
        if out_file.exists():
            out_file.unlink(missing_ok=True)
        return False, f"Encryption failed: {str(e)}", {}


def decrypt_file(
    input_path: str | Path,
    output_dir_or_file: str | Path,
    passphrase: str,
    progress_callback: Callable[[float], None] | None = None
) -> tuple[bool, str, Path | None]:
    """
    Decrypt an AES-256-GCM encrypted file, verifying tag integrity and reconstructing original data.
    """
    in_file = Path(input_path)
    if not in_file.exists():
        return False, f"Encrypted file does not exist: {in_file}", None

    out_target = Path(output_dir_or_file)
    actual_out_file: Path | None = None

    try:
        total_size = in_file.stat().st_size
        with open(in_file, "rb") as fin:
            # 1. Read & Validate Header
            magic = fin.read(4)
            if magic != FILE_MAGIC:
                return False, "Invalid file format: Not an AeroSat encrypted file.", None

            version_byte = fin.read(1)
            if not version_byte:
                return False, "File is truncated.", None
            version = struct.unpack("!B", version_byte)[0]
            if version != FILE_VERSION:
                return False, f"Unsupported file version ({version}).", None

            salt = fin.read(16)
            name_len_bytes = fin.read(2)
            name_len = struct.unpack("!H", name_len_bytes)[0]
            original_filename = fin.read(name_len).decode("utf-8")

            # Determine output filepath
            if out_target.is_dir() or (not out_target.suffix and not out_target.exists()):
                out_target.mkdir(parents=True, exist_ok=True)
                actual_out_file = out_target / original_filename
            else:
                actual_out_file = out_target
                actual_out_file.parent.mkdir(parents=True, exist_ok=True)

            key = derive_aes_key(passphrase, salt)
            aesgcm = AESGCM(key)

            header_size = 4 + 1 + 16 + 2 + name_len
            bytes_read = header_size

            # 2. Decrypt Chunks
            with open(actual_out_file, "wb") as fout:
                expected_chunk_index = 0
                while True:
                    chunk_header_bytes = fin.read(4 + 1 + 12 + 4)
                    if not chunk_header_bytes:
                        break

                    bytes_read += len(chunk_header_bytes)
                    chunk_index, is_last, nonce, enc_len = struct.unpack("!IB12sI", chunk_header_bytes)

                    # Validate chunk sequence to prevent chunk reordering
                    if chunk_index != expected_chunk_index:
                        raise ValueError(f"Chunk order anomaly detected! Expected {expected_chunk_index}, got {chunk_index}.")

                    enc_chunk = fin.read(enc_len)
                    bytes_read += len(enc_chunk)

                    aad = f"chunk_{chunk_index}_{is_last}".encode("utf-8")
                    try:
                        decrypted_chunk = aesgcm.decrypt(nonce, enc_chunk, aad)
                    except InvalidTag:
                        raise ValueError(
                            "Authentication tag mismatch! Incorrect passphrase or file has been tampered with."
                        )

                    fout.write(decrypted_chunk)

                    if progress_callback and total_size > 0:
                        progress_callback(min(100.0, (bytes_read / total_size) * 100.0))

                    expected_chunk_index += 1
                    if is_last:
                        break

        return True, "File decrypted and authenticated successfully.", actual_out_file

    except Exception as e:
        if actual_out_file and actual_out_file.exists():
            actual_out_file.unlink(missing_ok=True)
        return False, f"Decryption failed: {str(e)}", None


def encrypt_bytes(data: bytes, passphrase: str) -> bytes:
    """Convenience helper to encrypt in-memory raw bytes using AES-256-GCM."""
    salt = os.urandom(16)
    nonce = os.urandom(AES_NONCE_SIZE_BYTES)
    key = derive_aes_key(passphrase, salt)
    aesgcm = AESGCM(key)
    ciphertext_with_tag = aesgcm.encrypt(nonce, data, None)
    # [SALT 16B] + [NONCE 12B] + [CIPHERTEXT_WITH_TAG]
    return salt + nonce + ciphertext_with_tag


def decrypt_bytes(encrypted_data: bytes, passphrase: str) -> bytes:
    """Convenience helper to decrypt in-memory raw bytes using AES-256-GCM."""
    if len(encrypted_data) < 16 + AES_NONCE_SIZE_BYTES + 16:
        raise ValueError("Ciphertext data too short.")
    salt = encrypted_data[:16]
    nonce = encrypted_data[16: 16 + AES_NONCE_SIZE_BYTES]
    ciphertext_with_tag = encrypted_data[16 + AES_NONCE_SIZE_BYTES:]
    key = derive_aes_key(passphrase, salt)
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ciphertext_with_tag, None)
