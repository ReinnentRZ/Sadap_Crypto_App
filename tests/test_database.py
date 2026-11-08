"""
Unit and Integration Tests for Phase 6: Encrypted SQLite Database Vault
"""
import shutil
import sqlite3
import tempfile
import unittest
from pathlib import Path

from core.database.db_manager import VaultDatabaseManager


class TestDatabaseVault(unittest.TestCase):
    """Test suite for transparent field-level encrypted database."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="aerosat_db_test_")
        self.db_path = Path(self.test_dir) / "vault_test.db"
        self.passphrase = "MasterKey-Passphrase-9921"
        self.db = VaultDatabaseManager(db_path=self.db_path, vault_passphrase=self.passphrase)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_database_initialization(self):
        self.assertTrue(self.db_path.exists())

        # Verify tables exist via raw sqlite query
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        conn.close()

        self.assertIn("secret_memos", tables)
        self.assertIn("encrypted_files_meta", tables)
        self.assertIn("stego_records", tables)
        self.assertIn("audit_logs", tables)

    def test_memo_field_level_encryption_at_rest(self):
        title = "Operasi Orbit Alpha"
        secret_content = "Koordinat target: -07.1234, 110.5678. Status: Terpantau radar."
        author = "AEROSAT-COMMANDER"

        memo_id = self.db.add_memo(title, secret_content, author, vigenere_hint="Key-99")
        self.assertGreater(memo_id, 0)

        # 1. Inspect RAW SQLite storage to verify encryption at rest
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT encrypted_content FROM secret_memos WHERE id = ?", (memo_id,))
        raw_row = cursor.fetchone()
        conn.close()

        raw_stored_content = raw_row[0]
        # Must NOT leak plaintext!
        self.assertNotIn("Koordinat target", raw_stored_content)
        self.assertNotIn("Terpantau radar", raw_stored_content)

        # 2. Verify transparent decryption via db manager
        memos = self.db.list_memos()
        self.assertEqual(len(memos), 1)
        self.assertEqual(memos[0]["title"], title)
        self.assertEqual(memos[0]["content"], secret_content)
        self.assertEqual(memos[0]["vigenere_hint"], "Key-99")
        self.assertEqual(memos[0]["author"], author)

    def test_memo_deletion(self):
        memo_id = self.db.add_memo("Temporary Memo", "Will be deleted immediately", "TEST")
        self.assertEqual(len(self.db.list_memos()), 1)

        deleted = self.db.delete_memo(memo_id)
        self.assertTrue(deleted)
        self.assertEqual(len(self.db.list_memos()), 0)

    def test_file_metadata_encryption(self):
        original_name = "satellite_classified_scan.pdf"
        file_path = "/var/vault/file_01.enc"
        file_size = 2048500
        file_sha256 = "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"

        rec_id = self.db.add_file_record(original_name, file_path, file_size, file_sha256)
        self.assertGreater(rec_id, 0)

        # Check raw disk
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT encrypted_original_filename FROM encrypted_files_meta WHERE id = ?", (rec_id,))
        raw_name = cursor.fetchone()[0]
        conn.close()

        self.assertNotIn("satellite_classified_scan.pdf", raw_name)

        # Decrypted retrieval
        records = self.db.list_file_records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["original_filename"], original_name)
        self.assertEqual(records[0]["file_sha256"], file_sha256)

    def test_stego_records_storage(self):
        img_path = "/assets/stego_01.png"
        preview = "Secret directive for Sector 4"
        payload_size = 1024
        psnr = 62.45

        self.db.add_stego_record(img_path, preview, payload_size, psnr)
        records = self.db.list_stego_records()
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["secret_preview"], preview)
        self.assertAlmostEqual(records[0]["psnr_db"], psnr, places=2)

    def test_audit_logs_storage(self):
        event = "AUTH_BIOMETRIC_SUCCESS"
        details = "Face biometric verified with cosine similarity 0.892"

        self.db.add_audit_log(event, details, operator="COMMANDER-ALPHA")
        logs = self.db.list_audit_logs()
        self.assertEqual(len(logs), 1)
        self.assertEqual(logs[0]["event_type"], event)
        self.assertEqual(logs[0]["details"], details)

    def test_wrong_passphrase_locks_data(self):
        """Opening the database with a wrong passphrase must return [ENCRYPTED_DATA_LOCKED]."""
        self.db.add_memo("Top Secret", "Unreadable by intruders", "ALPHA")

        # Create unauthorized DB manager pointing to same SQLite file
        intruder_db = VaultDatabaseManager(db_path=self.db_path, vault_passphrase="WrongHackerPassphrase!")
        memos = intruder_db.list_memos()

        self.assertEqual(len(memos), 1)
        # Content must be locked!
        self.assertEqual(memos[0]["content"], "[ENCRYPTED_DATA_LOCKED]")


if __name__ == "__main__":
    unittest.main()
