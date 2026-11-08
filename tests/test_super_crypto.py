"""
Unit and Integration Tests for Phase 3: Super-Encryption (Vigenère + RSA)
"""
import unittest
from core.crypto.vigenere import (
    vigenere_encrypt_text,
    vigenere_decrypt_text,
    vigenere_encrypt_bytes,
    vigenere_decrypt_bytes,
)
from core.crypto.rsa_engine import (
    generate_rsa_keypair,
    export_private_key_pem,
    export_public_key_pem,
    load_private_key_pem,
    load_public_key_pem,
    rsa_encrypt_bytes,
    rsa_decrypt_bytes,
)
from core.crypto.super_text_cipher import super_encrypt, super_decrypt


class TestVigenereCipher(unittest.TestCase):
    """Test Extended Vigenère Cipher (mod 256)."""

    def test_basic_encryption_decryption(self):
        text = "Laporan Operasi Satelit Orbit Alpha: Koordinat -6.2088, 106.8456!"
        key = "SECRET-VIGENERE-KEY-2026"

        encrypted_b64 = vigenere_encrypt_text(text, key)
        self.assertNotEqual(text, encrypted_b64)

        decrypted = vigenere_decrypt_text(encrypted_b64, key)
        self.assertEqual(text, decrypted)

    def test_unicode_and_symbols(self):
        complex_text = "Pesan Intelijen 🛰️ — Status: Siaga 1 \nBaris 2: #1234567890\t[CONFIDENTIAL]"
        key = "KunciRahasia!@#"

        encrypted_b64 = vigenere_encrypt_text(complex_text, key)
        decrypted = vigenere_decrypt_text(encrypted_b64, key)
        self.assertEqual(complex_text, decrypted)

    def test_wrong_key_fails_reconstruction(self):
        text = "Top Secret Flight Telemetry Directive"
        key_correct = "KeyAlpha"
        key_wrong = "KeyBravo"

        encrypted_b64 = vigenere_encrypt_text(text, key_correct)
        decrypted_wrong = vigenere_decrypt_text(encrypted_b64, key_wrong)
        self.assertNotEqual(text, decrypted_wrong)

    def test_empty_key_raises_error(self):
        with self.assertRaises(ValueError):
            vigenere_encrypt_bytes(b"data", "")


class TestRSAEngine(unittest.TestCase):
    """Test RSA keygen, PEM serialization, and chunked RSA-OAEP."""

    @classmethod
    def setUpClass(cls):
        cls.priv_key, cls.pub_key = generate_rsa_keypair(key_size=2048)

    def test_key_serialization_roundtrip(self):
        priv_pem = export_private_key_pem(self.priv_key, password="pass")
        pub_pem = export_public_key_pem(self.pub_key)

        loaded_priv = load_private_key_pem(priv_pem, password="pass")
        loaded_pub = load_public_key_pem(pub_pem)

        self.assertEqual(loaded_priv.key_size, 2048)
        self.assertEqual(loaded_pub.key_size, 2048)

    def test_short_payload_encryption(self):
        message = b"Short ground station signal."
        ciphertext = rsa_encrypt_bytes(message, self.pub_key)
        self.assertNotEqual(message, ciphertext)

        recovered = rsa_decrypt_bytes(ciphertext, self.priv_key)
        self.assertEqual(message, recovered)

    def test_long_payload_chunking(self):
        """Test payload greater than 190 bytes (requiring multi-chunk RSA-OAEP)."""
        long_message = (
            b"AeroSat Orbit Observation Report: Detailed telemetry analysis confirms that "
            b"Orbital Satellite SV-09 has completed its 4,500th revolution. Thermal sensors "
            b"indicate nominal parameters at 18.4 degrees Celsius. Transponder frequencies "
            b"are aligned with ground station receptors across Sector 4-B. Classified logs "
            b"and raw radar scans have been successfully transmitted to the local vault."
        )
        self.assertGreater(len(long_message), 300)

        ciphertext = rsa_encrypt_bytes(long_message, self.pub_key)
        # Because it is chunked, length will be multiple of 256
        self.assertEqual(len(ciphertext) % 256, 0)

        recovered = rsa_decrypt_bytes(ciphertext, self.priv_key)
        self.assertEqual(long_message, recovered)

    def test_wrong_private_key_fails(self):
        other_priv, _ = generate_rsa_keypair(key_size=2048)
        message = b"Confidential directive"
        ciphertext = rsa_encrypt_bytes(message, self.pub_key)

        with self.assertRaises(Exception):
            rsa_decrypt_bytes(ciphertext, other_priv)


class TestSuperEncryptionPipeline(unittest.TestCase):
    """Test integrated 2-layer Super-Encryption (Vigenère + RSA)."""

    @classmethod
    def setUpClass(cls):
        cls.priv_key, cls.pub_key = generate_rsa_keypair(key_size=2048)

    def test_full_pipeline_success(self):
        secret_memo = (
            "DIREKTIF INTELIJEN AEROSAT #9921:\n"
            "Target berada pada koordinat 07 14' 32\" S, 110 24' 15\" E.\n"
            "Seluruh transmisi file telah dialihkan ke mode AES-256.\n"
            "Kunci uplink orbit telah diperbarui secara kriptografis."
        )
        vigenere_key = "ORBIT-CIPHER-KUNCI-99"

        # Super Encrypt
        token = super_encrypt(secret_memo, vigenere_key, self.pub_key)
        self.assertIsInstance(token, str)

        # Super Decrypt
        success, recovered_text, msg = super_decrypt(token, vigenere_key, self.priv_key)
        self.assertTrue(success)
        self.assertEqual(secret_memo, recovered_text)
        self.assertIn("successful", msg.lower())

    def test_wrong_vigenere_key_detected(self):
        text = "Classified Message For Commander Eyes Only"
        v_key = "CorrectVigenereKey"
        wrong_v_key = "WrongKey123"

        token = super_encrypt(text, v_key, self.pub_key)
        success, recovered_text, msg = super_decrypt(token, wrong_v_key, self.priv_key)

        # Either decode error or mismatch
        self.assertNotEqual(text, recovered_text)

    def test_wrong_rsa_key_fails(self):
        text = "Classified Message"
        v_key = "ValidKey"
        other_priv, _ = generate_rsa_keypair(key_size=2048)

        token = super_encrypt(text, v_key, self.pub_key)
        success, recovered_text, msg = super_decrypt(token, v_key, other_priv)
        self.assertFalse(success)
        self.assertIn("failed", msg.lower())

    def test_tampered_token_detected(self):
        text = "Message to be tampered"
        v_key = "TestKey"
        token = super_encrypt(text, v_key, self.pub_key)

        # Tamper with the token string
        tampered_token = token[:-10] + "AAAAAAAAAA"
        success, _, msg = super_decrypt(tampered_token, v_key, self.priv_key)
        self.assertFalse(success)


if __name__ == "__main__":
    unittest.main()
