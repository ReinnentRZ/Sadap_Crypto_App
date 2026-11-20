"""
Unit and Integration Tests for Phase 2: 3-Factor Authentication System
Tests Password Hasher, USB Dongle Verification, and Face Biometric Engine.
"""
import shutil
import tempfile
import unittest
from pathlib import Path
import cv2
import numpy as np

from core.auth.hasher import hash_password, verify_password, generate_secure_passcode
from core.auth.usb_dongle import (
    create_dongle_token,
    verify_token_payload,
    get_volume_serial_number,
    find_and_verify_dongle,
    dongle_identity_matches,
    USB_TOKEN_FILENAME,
)
from core.auth.face_recog import get_face_engine
from core.crypto.file_aes import encrypt_file, decrypt_file


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


class TestMultiFaceTemplates(unittest.TestCase):
    """Multi-operator biometric registry, migration, and best-of-N matching."""

    def setUp(self):
        self.engine = get_face_engine()
        self.tmp_dir = tempfile.mkdtemp(prefix="sadap_multiface_test_")
        self.path = Path(self.tmp_dir) / "operators.npz"

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    @staticmethod
    def _vector(seed: int) -> np.ndarray:
        vector = np.random.default_rng(seed).normal(size=(1, 128)).astype(np.float32)
        return vector / np.linalg.norm(vector)

    def test_save_multiple_and_match_best_operator(self):
        alpha = self._vector(1)
        beta = self._vector(2)
        self.assertTrue(self.engine.save_template(alpha, "ALPHA", self.path))
        self.assertTrue(self.engine.save_template(beta, "BETA", self.path))

        self.assertEqual(self.engine.list_template_names(self.path), ["ALPHA", "BETA"])
        matched, score, name = self.engine.match_embedding(beta, self.engine.load_templates(self.path))
        self.assertTrue(matched)
        self.assertAlmostEqual(score, 1.0, places=2)
        self.assertEqual(name, "BETA")

    def test_upsert_and_delete_keep_other_operators(self):
        alpha = self._vector(3)
        beta = self._vector(4)
        replacement = self._vector(5)
        self.engine.save_template(alpha, "ALPHA", self.path)
        self.engine.save_template(beta, "BETA", self.path)

        self.assertTrue(self.engine.save_template(replacement, "ALPHA", self.path))
        self.assertEqual(self.engine.list_template_names(self.path), ["ALPHA", "BETA"])
        _, _, name = self.engine.match_embedding(replacement, self.engine.load_templates(self.path))
        self.assertEqual(name, "ALPHA")

        self.assertTrue(self.engine.delete_template("ALPHA", self.path))
        self.assertEqual(self.engine.list_template_names(self.path), ["BETA"])
        self.assertFalse(self.engine.delete_template("ALPHA", self.path))

    def test_legacy_single_face_is_migrated(self):
        legacy = self._vector(6)
        np.savez_compressed(self.path, embedding=legacy, operator_name="rei")

        loaded = self.engine.load_templates(self.path)
        self.assertEqual([t.name for t in loaded], ["rei"])

        self.engine.save_template(self._vector(7), "SADAP-ALPHA", self.path)
        data = np.load(self.path, allow_pickle=True)
        self.assertIn("embeddings", data)
        self.assertEqual(len(data["embeddings"]), 2)
        self.assertEqual(self.engine.list_template_names(self.path), ["rei", "SADAP-ALPHA"])


class TestEncryptedFaceSnapshot(unittest.TestCase):
    """Snapshot bytes are AES-256-GCM encrypted and recoverable with the passphrase."""

    def test_encrypt_and_decrypt_snapshot(self):
        with tempfile.TemporaryDirectory(prefix="sadap_snapshot_test_") as tmp:
            root = Path(tmp)
            plain = root / "face.png"
            cv2.imwrite(str(plain), np.zeros((112, 112, 3), dtype=np.uint8))

            encrypted = root / "face.png.enc"
            ok, msg, _ = encrypt_file(plain, encrypted, "snapshot-passphrase")
            self.assertTrue(ok, msg)
            self.assertTrue(encrypted.exists())
            self.assertFalse(encrypted.read_bytes().startswith(b"\x89PNG"))

            out_dir = root / "decrypted"
            ok, msg, decrypted = decrypt_file(encrypted, out_dir, "snapshot-passphrase")
            self.assertTrue(ok, msg)
            self.assertIsNotNone(decrypted)
            self.assertEqual(cv2.imread(str(decrypted)).shape, (112, 112, 3))

            ok, msg, _ = decrypt_file(encrypted, root / "wrong", "wrong-passphrase")
            self.assertFalse(ok)


class TestDongleIdentityPinning(unittest.TestCase):
    """Swapping to a different authorized dongle must be treated as removal."""

    def test_only_original_token_is_accepted(self):
        expected = {"token_id": "token-1", "device_serial": "SERIAL-1"}
        self.assertTrue(dongle_identity_matches(dict(expected), expected))
        self.assertFalse(
            dongle_identity_matches({"token_id": "token-2", "device_serial": "SERIAL-1"}, expected)
        )
        self.assertFalse(
            dongle_identity_matches({"token_id": "token-1", "device_serial": "SERIAL-2"}, expected)
        )
        self.assertTrue(dongle_identity_matches({}, {}))


if __name__ == "__main__":
    unittest.main()
