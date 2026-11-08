"""
Unit and Integration Tests for Phase 4: AES-256-GCM File Encryption
"""
import os
import shutil
import tempfile
import unittest
from pathlib import Path

from core.crypto.file_aes import (
    encrypt_file,
    decrypt_file,
    encrypt_bytes,
    decrypt_bytes,
    FILE_MAGIC,
)


class TestFileAES(unittest.TestCase):
    """Test suite for AES-256-GCM file and byte encryption."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="aerosat_file_aes_test_")
        self.passphrase = "TopSecret-Orbital-Key-7788!"

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_in_memory_bytes_encryption(self):
        raw_data = b"Satellite Telemetry Vector: Alpha-9, Orbit Speed 7.8 km/s"
        encrypted = encrypt_bytes(raw_data, self.passphrase)
        self.assertNotEqual(raw_data, encrypted)

        decrypted = decrypt_bytes(encrypted, self.passphrase)
        self.assertEqual(raw_data, decrypted)

    def test_in_memory_wrong_passphrase_rejected(self):
        raw_data = b"Confidential Medical Scan or Satellite Coordinates"
        encrypted = encrypt_bytes(raw_data, self.passphrase)

        with self.assertRaises(Exception):
            decrypt_bytes(encrypted, "WrongPassword-1234")

    def test_in_memory_tampered_byte_rejected(self):
        raw_data = b"Important Asset Hash: 8f2383e4dd3cfbb4553ea8718107fc0423210dc"
        encrypted = bytearray(encrypt_bytes(raw_data, self.passphrase))

        # Flip one bit in ciphertext
        encrypted[-1] ^= 0x01

        with self.assertRaises(Exception):
            decrypt_bytes(bytes(encrypted), self.passphrase)

    def test_file_encryption_text_file(self):
        src_path = Path(self.test_dir) / "intel_report.txt"
        enc_path = Path(self.test_dir) / "intel_report.txt.enc"
        out_dir = Path(self.test_dir) / "decrypted_output"

        content = "DIRECTIVE 001: Orbit pass completed over Sector 7.\nWeather: Clear."
        src_path.write_text(content, encoding="utf-8")

        # Encrypt
        success, msg, meta = encrypt_file(src_path, enc_path, self.passphrase)
        self.assertTrue(success)
        self.assertTrue(enc_path.exists())
        self.assertEqual(meta["original_filename"], "intel_report.txt")

        # Decrypt
        dec_success, dec_msg, recovered_path = decrypt_file(enc_path, out_dir, self.passphrase)
        self.assertTrue(dec_success)
        self.assertIsNotNone(recovered_path)
        self.assertTrue(recovered_path.exists())
        self.assertEqual(recovered_path.name, "intel_report.txt")
        self.assertEqual(recovered_path.read_text(encoding="utf-8"), content)

    def test_multi_chunk_binary_file(self):
        """Test file larger than 64 KB chunk size (e.g. 200 KB) to verify chunk streaming."""
        src_path = Path(self.test_dir) / "sat_radar_raw.bin"
        enc_path = Path(self.test_dir) / "sat_radar_raw.bin.enc"
        out_dir = Path(self.test_dir) / "decrypted_binary"

        # Generate 200 KB of pseudo-random bytes
        data = os.urandom(200 * 1024)
        src_path.write_bytes(data)

        progress_calls = []

        def track_progress(pct):
            progress_calls.append(pct)

        # Encrypt with chunk size 64 KB
        success, msg, meta = encrypt_file(
            src_path, enc_path, self.passphrase, chunk_size=64 * 1024, progress_callback=track_progress
        )
        self.assertTrue(success)
        self.assertEqual(meta["chunks_count"], 4)  # 200 KB / 64 KB = 3.125 -> 4 chunks
        self.assertGreater(len(progress_calls), 0)

        # Decrypt
        dec_success, dec_msg, recovered_path = decrypt_file(enc_path, out_dir, self.passphrase)
        self.assertTrue(dec_success)
        self.assertEqual(recovered_path.read_bytes(), data)

    def test_empty_file_encryption(self):
        src_path = Path(self.test_dir) / "empty_log.txt"
        enc_path = Path(self.test_dir) / "empty_log.txt.enc"
        out_dir = Path(self.test_dir) / "decrypted_empty"

        src_path.write_bytes(b"")

        success, msg, meta = encrypt_file(src_path, enc_path, self.passphrase)
        self.assertTrue(success)

        dec_success, dec_msg, recovered_path = decrypt_file(enc_path, out_dir, self.passphrase)
        self.assertTrue(dec_success)
        self.assertEqual(recovered_path.read_bytes(), b"")

    def test_wrong_passphrase_on_file(self):
        src_path = Path(self.test_dir) / "confidential.pdf"
        enc_path = Path(self.test_dir) / "confidential.pdf.enc"
        out_dir = Path(self.test_dir) / "decrypted_pdf"

        src_path.write_bytes(b"%PDF-1.4 Fake PDF raw header and stream data")
        encrypt_file(src_path, enc_path, self.passphrase)

        dec_success, dec_msg, recovered_path = decrypt_file(enc_path, out_dir, "WrongPassword!")
        self.assertFalse(dec_success)
        self.assertIn("failed", dec_msg.lower())
        self.assertIsNone(recovered_path)

    def test_tampered_encrypted_file_detected(self):
        src_path = Path(self.test_dir) / "sat_image.png"
        enc_path = Path(self.test_dir) / "sat_image.png.enc"
        out_dir = Path(self.test_dir) / "decrypted_png"

        src_path.write_bytes(b"\x89PNG\r\n\x1a\nFake PNG byte payload")
        encrypt_file(src_path, enc_path, self.passphrase)

        # Corrupt one byte near the end
        enc_bytes = bytearray(enc_path.read_bytes())
        enc_bytes[-5] ^= 0xFF
        enc_path.write_bytes(bytes(enc_bytes))

        dec_success, dec_msg, recovered_path = decrypt_file(enc_path, out_dir, self.passphrase)
        self.assertFalse(dec_success)
        self.assertIn("mismatch", dec_msg.lower())


if __name__ == "__main__":
    unittest.main()
