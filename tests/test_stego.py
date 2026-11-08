"""
Unit and Integration Tests for Phase 5: LSB Image Steganography
"""
import shutil
import tempfile
import unittest
from pathlib import Path
import numpy as np
from PIL import Image

from core.stego.lsb_engine import (
    calculate_image_capacity,
    calculate_psnr,
    embed_payload_into_image,
    extract_payload_from_image,
)


class TestStegoEngine(unittest.TestCase):
    """Test suite for LSB image steganography."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="aerosat_stego_test_")
        self.cover_path = Path(self.test_dir) / "cover_sat.png"
        self.stego_path = Path(self.test_dir) / "stego_output.png"

        # Create a 200x200 test RGB image
        img_arr = np.random.randint(50, 200, size=(200, 200, 3), dtype=np.uint8)
        img = Image.fromarray(img_arr, mode="RGB")
        img.save(self.cover_path, format="PNG")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_capacity_calculation(self):
        # 200 * 200 * 3 = 120,000 channel bytes -> 15,000 bytes - 9 header bytes = 14,991 bytes
        capacity = calculate_image_capacity(200, 200)
        self.assertEqual(capacity, 14991)

    def test_psnr_calculation(self):
        arr1 = np.ones((50, 50, 3), dtype=np.uint8) * 100
        # Exactly identical arrays should yield 100 dB
        self.assertEqual(calculate_psnr(arr1, arr1), 100.0)

        # Altering just 1 bit in 1 pixel
        arr2 = arr1.copy()
        arr2[0, 0, 0] = 101
        psnr = calculate_psnr(arr1, arr2)
        self.assertGreater(psnr, 60.0)

    def test_plain_text_steganography(self):
        secret_message = (
            "KOORDINAT SATELIT RAHASIA:\n"
            "Lintang: -06.21462°\n"
            "Bujur: 106.84513°\n"
            "Elevasi: 420.5 km | Sudut Azimuth: 142.8°"
        )

        # 1. Embed
        ok, msg, meta = embed_payload_into_image(
            self.cover_path,
            self.stego_path,
            secret_message
        )
        self.assertTrue(ok)
        self.assertTrue(self.stego_path.exists())
        self.assertGreater(meta["psnr_db"], 50.0)

        # 2. Extract
        ext_ok, ext_msg, extracted_data, ext_meta = extract_payload_from_image(self.stego_path)
        self.assertTrue(ext_ok)
        self.assertEqual(extracted_data, secret_message)
        self.assertFalse(ext_meta["is_encrypted"])

    def test_pre_encrypted_steganography(self):
        secret_text = "Classified Space Defense Protocol Alpha-Zero"
        passphrase = "StegoPassword-9921"

        # 1. Embed with AES-256 pre-encryption
        ok, msg, meta = embed_payload_into_image(
            self.cover_path,
            self.stego_path,
            secret_text,
            passphrase=passphrase
        )
        self.assertTrue(ok)
        self.assertTrue(meta["is_encrypted"])

        # 2. Extract without passphrase -> Must notify that payload is encrypted
        ext_ok, ext_msg, data, ext_meta = extract_payload_from_image(self.stego_path, passphrase=None)
        self.assertFalse(ext_ok)
        self.assertIn("passphrase required", ext_msg.lower())
        self.assertIsNone(data)

        # 3. Extract with wrong passphrase -> Must fail cleanly
        ext_ok, ext_msg, data, _ = extract_payload_from_image(self.stego_path, passphrase="WrongPassword!")
        self.assertFalse(ext_ok)
        self.assertIn("failed", ext_msg.lower())

        # 4. Extract with correct passphrase -> Must recover exact plaintext
        ext_ok, ext_msg, data, _ = extract_payload_from_image(self.stego_path, passphrase=passphrase)
        self.assertTrue(ext_ok)
        self.assertEqual(data, secret_text)

    def test_raw_binary_payload(self):
        raw_bytes = bytes([0xDE, 0xAD, 0xBE, 0xEF, 0x00, 0xFF, 0x42, 0x99] * 30)

        ok, msg, meta = embed_payload_into_image(
            self.cover_path,
            self.stego_path,
            raw_bytes
        )
        self.assertTrue(ok)

        ext_ok, ext_msg, extracted_bytes, _ = extract_payload_from_image(self.stego_path)
        self.assertTrue(ext_ok)
        self.assertEqual(extracted_bytes, raw_bytes)

    def test_oversized_payload_rejected(self):
        # Image capacity is ~14.9 KB, payload is 30 KB
        huge_payload = b"X" * 30000

        ok, msg, meta = embed_payload_into_image(
            self.cover_path,
            self.stego_path,
            huge_payload
        )
        self.assertFalse(ok)
        self.assertIn("exceeds", msg.lower())

    def test_non_stego_image_fails_gracefully(self):
        # Extract from normal cover image with no payload
        ext_ok, ext_msg, data, _ = extract_payload_from_image(self.cover_path)
        self.assertFalse(ext_ok)
        self.assertIn("no aerosat stego", ext_msg.lower())
        self.assertIsNone(data)


if __name__ == "__main__":
    unittest.main()
