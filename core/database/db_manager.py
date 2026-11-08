"""
AeroSat GroundStation - Encrypted Database Manager
Provides transparent field-level AES-256-GCM encryption for SQLite storage at rest.
"""
import contextlib
import sqlite3
import time
from pathlib import Path
from config.settings import DB_PATH
from core.crypto.file_aes import encrypt_bytes, decrypt_bytes
from core.utils.crypto_helpers import bytes_to_b64, b64_to_bytes
from core.database.models import (
    SQL_CREATE_MEMOS_TABLE,
    SQL_CREATE_FILES_TABLE,
    SQL_CREATE_STEGO_TABLE,
    SQL_CREATE_AUDIT_TABLE,
)
from core.utils.logger import get_logger

logger = get_logger("DBVault")


class VaultDatabaseManager:
    """Manages SQLite database with transparent AES-256 field-level encryption."""

    def __init__(self, db_path: Path | str = DB_PATH, vault_passphrase: str = "AeroSat-Master-Passphrase-2026"):
        self.db_path = Path(db_path)
        self.vault_passphrase = vault_passphrase
        self._init_database()

    @contextlib.contextmanager
    def _get_connection(self):
        """Create a managed SQLite connection that guarantees connection closure."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def _init_database(self):
        """Execute table creation DDL statements."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(SQL_CREATE_MEMOS_TABLE)
            cursor.execute(SQL_CREATE_FILES_TABLE)
            cursor.execute(SQL_CREATE_STEGO_TABLE)
            cursor.execute(SQL_CREATE_AUDIT_TABLE)
            conn.commit()
        logger.info(f"Database vault initialized at {self.db_path}")

    def _encrypt_field(self, plaintext: str) -> str:
        """Encrypt sensitive field using AES-256-GCM and encode as Base64."""
        if not plaintext:
            return ""
        enc_bytes = encrypt_bytes(plaintext.encode("utf-8"), self.vault_passphrase)
        return bytes_to_b64(enc_bytes)

    def _decrypt_field(self, b64_str: str) -> str:
        """Decrypt Base64 ciphertext back to plaintext using AES-256-GCM."""
        if not b64_str:
            return ""
        try:
            enc_bytes = b64_to_bytes(b64_str)
            dec_bytes = decrypt_bytes(enc_bytes, self.vault_passphrase)
            return dec_bytes.decode("utf-8")
        except Exception as e:
            logger.error(f"Failed to decrypt database field: {e}")
            return "[ENCRYPTED_DATA_LOCKED]"

    # ==========================
    # 1. SECRET MEMOS CRUD
    # ==========================
    def add_memo(self, title: str, content: str, author: str = "COMMANDER-01", vigenere_hint: str = "") -> int:
        """Store a new classified memo with content encrypted at rest."""
        enc_content = self._encrypt_field(content)
        enc_hint = self._encrypt_field(vigenere_hint) if vigenere_hint else ""
        timestamp = int(time.time())

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO secret_memos (title, encrypted_content, vigenere_hint, author, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (title, enc_content, enc_hint, author, timestamp)
            )
            conn.commit()
            return cursor.lastrowid

    def list_memos(self) -> list[dict]:
        """Retrieve and transparently decrypt all classified memos."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM secret_memos ORDER BY created_at DESC")
            rows = cursor.fetchall()

        results = []
        for r in rows:
            results.append({
                "id": r["id"],
                "title": r["title"],
                "content": self._decrypt_field(r["encrypted_content"]),
                "vigenere_hint": self._decrypt_field(r["vigenere_hint"]) if r["vigenere_hint"] else "",
                "author": r["author"],
                "created_at": r["created_at"]
            })
        return results

    def delete_memo(self, memo_id: int) -> bool:
        """Delete memo by ID."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM secret_memos WHERE id = ?", (memo_id,))
            conn.commit()
            return cursor.rowcount > 0

    # ==========================
    # 2. ENCRYPTED FILES METADATA
    # ==========================
    def add_file_record(self, original_filename: str, file_path: str, file_size: int, file_sha256: str) -> int:
        """Record an encrypted file metadata entry with encrypted original name."""
        enc_name = self._encrypt_field(original_filename)
        timestamp = int(time.time())

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO encrypted_files_meta
                (encrypted_original_filename, file_path, file_size, file_sha256, encrypted_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (enc_name, file_path, file_size, file_sha256, timestamp)
            )
            conn.commit()
            return cursor.lastrowid

    def list_file_records(self) -> list[dict]:
        """List encrypted file records with decrypted original filenames."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM encrypted_files_meta ORDER BY encrypted_at DESC")
            rows = cursor.fetchall()

        results = []
        for r in rows:
            results.append({
                "id": r["id"],
                "original_filename": self._decrypt_field(r["encrypted_original_filename"]),
                "file_path": r["file_path"],
                "file_size": r["file_size"],
                "file_sha256": r["file_sha256"],
                "encrypted_at": r["encrypted_at"]
            })
        return results

    # ==========================
    # 3. STEGANOGRAPHY RECORDS
    # ==========================
    def add_stego_record(self, image_path: str, secret_preview: str, payload_size: int, psnr_db: float) -> int:
        """Record a steganography injection event with encrypted secret preview."""
        enc_preview = self._encrypt_field(secret_preview)
        timestamp = int(time.time())

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO stego_records
                (image_path, encrypted_secret_preview, payload_size, psnr_db, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (image_path, enc_preview, payload_size, psnr_db, timestamp)
            )
            conn.commit()
            return cursor.lastrowid

    def list_stego_records(self) -> list[dict]:
        """List all stego injection history records."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM stego_records ORDER BY created_at DESC")
            rows = cursor.fetchall()

        results = []
        for r in rows:
            results.append({
                "id": r["id"],
                "image_path": r["image_path"],
                "secret_preview": self._decrypt_field(r["encrypted_secret_preview"]),
                "payload_size": r["payload_size"],
                "psnr_db": r["psnr_db"],
                "created_at": r["created_at"]
            })
        return results

    # ==========================
    # 4. AUDIT LOGS
    # ==========================
    def add_audit_log(
        self,
        event_type: str,
        details: str,
        operator: str = "AEROSAT-SYSTEM",
        device_info: str = "LOCAL-WORKSTATION"
    ) -> int:
        """Record a security audit log with encrypted event details."""
        enc_details = self._encrypt_field(details)
        timestamp = int(time.time())

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                """
                INSERT INTO audit_logs
                (event_type, encrypted_details, operator_callsign, device_info, timestamp)
                VALUES (?, ?, ?, ?, ?)
                """,
                (event_type, enc_details, operator, device_info, timestamp)
            )
            conn.commit()
            return cursor.lastrowid

    def list_audit_logs(self, limit: int = 50) -> list[dict]:
        """List security audit log entries with decrypted details."""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM audit_logs ORDER BY timestamp DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()

        results = []
        for r in rows:
            results.append({
                "id": r["id"],
                "event_type": r["event_type"],
                "details": self._decrypt_field(r["encrypted_details"]),
                "operator": r["operator_callsign"],
                "device": r["device_info"],
                "timestamp": r["timestamp"]
            })
        return results


# Global singleton database instance
_vault_db_instance: VaultDatabaseManager | None = None


def get_vault_db(passphrase: str = "AeroSat-Master-Passphrase-2026") -> VaultDatabaseManager:
    """Return shared VaultDatabaseManager instance."""
    global _vault_db_instance
    if _vault_db_instance is None or _vault_db_instance.vault_passphrase != passphrase:
        _vault_db_instance = VaultDatabaseManager(vault_passphrase=passphrase)
    return _vault_db_instance
