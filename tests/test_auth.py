"""
Unit and Integration Tests for Phase 2: 3-Factor Authentication System
Tests Password Hasher, USB Dongle Verification, and Face Biometric Engine.
"""
import shutil
import tempfile
import unittest
from pathlib import Path
import numpy as np

from core.auth.hasher import hash_password, verify_password, generate_secure_passcode
from core.auth.usb_dongle import (
    create_dongle_token,
    verify_token_payload,
    get_volume_serial_number,
    find_and_verify_dongle,
    USB_TOKEN_FILENAME,
)
from core.auth.face_recog import get_face_engine


class TestPasswordHasher(unittest.TestCase):
    """Test cryptographic password hashing."""

    def test_correct_password_verification(self):
        password = "Classified-Sat-Uplink-9921!"
        hashed = hash_password(password)

        self.assertTrue(hashed.startswith("pbkdf2_sha256$"))
        self.assertTrue(verify_password(password, hashed))

    def test_wrong_password_rejected(self):
        password = "CorrectPasscode123"
        hashed = hash_password(password)

        self.assertFalse(verify_password("WrongPasscode123", hashed))
        self.assertFalse(verify_password("", hashed))

    def test_salt_uniqueness(self):
        password = "SamePasswordForBoth"
        hash1 = hash_password(password)
        hash2 = hash_password(password)

        # Due to random salt, the two hashes must be completely different
        self.assertNotEqual(hash1, hash2)
        self.assertTrue(verify_password(password, hash1))
        self.assertTrue(verify_password(password, hash2))

    def test_tampered_hash_fails_gracefully(self):
        password = "SecretPassword"
        hashed = hash_password(password)
        tampered = hashed[:-4] + "ffff"

        self.assertFalse(verify_password(password, tampered))
        self.assertFalse(verify_password(password, "invalid_format_string"))

    def test_generate_secure_passcode(self):
        code = generate_secure_passcode(24)
        self.assertEqual(len(code), 24)
        self.assertIsInstance(code, str)


class TestUSBDongle(unittest.TestCase):
    """Test USB Hardware Dongle generation, verification, and tamper detection."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="aerosat_usb_test_")

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_create_and_verify_dongle(self):
        serial = "TEST-USB-SERIAL-99"
        success, msg, payload = create_dongle_token(
            self.test_dir,
            operator_callsign="OPERATOR-TEST",
            custom_serial=serial
        )
        self.assertTrue(success)
        self.assertEqual(payload["device_serial"], serial)

        # Verify token payload
        is_valid, verify_msg = verify_token_payload(payload, current_serial=serial)
        self.assertTrue(is_valid)
        self.assertIn("verified", verify_msg.lower())

    def test_serial_mismatch_detected(self):
        """Simulate copying the token file to another USB drive with different serial number."""
        original_serial = "ORIGINAL-SERIAL-1111"
        different_serial = "CLONED-DRIVE-SERIAL-2222"

        _, _, payload = create_dongle_token(
            self.test_dir,
            operator_callsign="OPERATOR-TEST",
            custom_serial=original_serial
        )

        # Verifying on the fake drive must fail!
        is_valid, msg = verify_token_payload(payload, current_serial=different_serial)
        self.assertFalse(is_valid)
        self.assertIn("mismatch", msg.lower())

    def test_tampered_signature_detected(self):
        """Simulate malicious alteration of operator callsign or token content."""
        serial = "TEST-SERIAL"
        _, _, payload = create_dongle_token(
            self.test_dir,
            operator_callsign="OPERATOR-ORIGINAL",
            custom_serial=serial
        )

        # Alter payload
        payload["operator_callsign"] = "MALICIOUS-INTRUDER"

        is_valid, msg = verify_token_payload(payload, current_serial=serial)
        self.assertFalse(is_valid)
        self.assertIn("mismatch", msg.lower())


class TestFaceBiometricEngine(unittest.TestCase):
    """Test AI face recognition and feature matching."""

    def setUp(self):
        self.engine = get_face_engine()

    def test_engine_initialization(self):
        self.assertIsNotNone(self.engine._detector)
        self.assertIsNotNone(self.engine._recognizer)

    def test_embedding_matching_logic(self):
        # Create synthetic 128-D normalized embedding vectors
        v1 = np.random.randn(1, 128).astype(np.float32)
        v1 = v1 / np.linalg.norm(v1)

        # Identical vector should yield high similarity
        is_same, score = self.engine.is_match(v1, v1)
        self.assertTrue(is_same)
        self.assertAlmostEqual(score, 1.0, places=2)

        # Orthogonal/different vector should yield low similarity
        v2 = np.random.randn(1, 128).astype(np.float32)
        v2 = v2 / np.linalg.norm(v2)
        # Cosine distance between random 128-D vectors is near 0
        _, random_score = self.engine.is_match(v1, v2)
        self.assertLess(random_score, 0.4)

    def test_template_save_and_load(self):
        tmp_dir = tempfile.mkdtemp(prefix="aerosat_face_test_")
        template_file = Path(tmp_dir) / "test_template.npz"

        try:
            sample_feat = np.ones((1, 128), dtype=np.float32)
            saved = self.engine.save_template(sample_feat, "Major Tom", template_file)
            self.assertTrue(saved)

            loaded_feat, loaded_name = self.engine.load_template(template_file)
            self.assertIsNotNone(loaded_feat)
            self.assertEqual(loaded_name, "Major Tom")
            np.testing.assert_array_equal(sample_feat, loaded_feat)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
