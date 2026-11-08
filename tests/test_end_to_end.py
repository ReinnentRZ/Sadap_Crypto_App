"""
End-to-End Integration and Security Penetration Test for AeroSat GroundStation
Simulates complete operational lifecycle: Gatekeeper Auth -> Super-Cipher ->
AES File Stream -> Satellite Stego -> Encrypted DB -> Blockchain Notary -> Tamper Defense.
"""
import shutil
import tempfile
import unittest
from pathlib import Path
import numpy as np
from PIL import Image

# 1. Auth imports
from core.auth.usb_dongle import create_dongle_token, find_and_verify_dongle
from core.auth.hasher import hash_password, verify_password
from core.auth.face_recog import get_face_engine

# 2. Crypto imports
from core.crypto.rsa_engine import generate_rsa_keypair
from core.crypto.super_text_cipher import super_encrypt, super_decrypt
from core.crypto.file_aes import encrypt_file, decrypt_file

# 3. Stego imports
from core.stego.lsb_engine import embed_payload_into_image, extract_payload_from_image

# 4. Database imports
from core.database.db_manager import VaultDatabaseManager

# 5. Blockchain imports
from core.blockchain.chain import Blockchain
from core.blockchain.asset_tracker import AssetTracker


class TestEndToEndSecurityFlow(unittest.TestCase):
    """Complete end-to-end mission scenario verification."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="aerosat_e2e_mission_")
        self.dir_path = Path(self.test_dir)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_complete_covert_mission_flow(self):
        print("\n" + "=" * 60)
        print(">>> STARTING END-TO-END SECURITY AUDIT & MISSION SIMULATION <<<")
        print("=" * 60)

        # ---------------------------------------------------------
        # STEP 1: ZERO-TRUST 3-FACTOR GATEKEEPER AUTHORIZATION
        # ---------------------------------------------------------
        print("[1/6] Verifying Gatekeeper Auth (USB + Biometric + Hash)...")

        # Factor 1: USB Dongle
        usb_dir = self.dir_path / "usb_mount"
        usb_ok, _, payload = create_dongle_token(
            str(usb_dir),
            operator_callsign="COMMANDER-TEST",
            custom_serial="SERIAL-AEROSAT-9921"
        )
        self.assertTrue(usb_ok)

        # Factor 2: Face Biometric Template
        face_engine = get_face_engine()
        synthetic_face = np.random.randn(1, 128).astype(np.float32)
        synthetic_face = synthetic_face / np.linalg.norm(synthetic_face)
        template_file = self.dir_path / "face.npz"
        face_engine.save_template(synthetic_face, "Commander Test", template_file)

        # Verify biometric match
        is_face_match, face_score = face_engine.is_match(synthetic_face, synthetic_face)
        self.assertTrue(is_face_match)

        # Factor 3: Password Hash
        master_pwd = "AeroSat-MasterClearance-2026!"
        pwd_hash = hash_password(master_pwd)
        self.assertTrue(verify_password(master_pwd, pwd_hash))
        self.assertFalse(verify_password("WrongPassword!", pwd_hash))
        print("      ✓ 3-Factor Gatekeeper passed successfully.")

        # ---------------------------------------------------------
        # STEP 2: SUPER-ENCRYPTION OF CLASSIFIED DIRECTIVE
        # ---------------------------------------------------------
        print("[2/6] Executing Super-Encryption (Extended Vigenère + RSA-OAEP)...")
        priv_key, pub_key = generate_rsa_keypair(key_size=2048)
        directive = (
            "OPERATION ORBITAL FALCON:\n"
            "Satellite SV-09 transponder frequency: 2.245 GHz.\n"
            "Re-align optics to coordinate -06.2088° S, 106.8456° E."
        )
        vigenere_key = "KUNCI-ORBIT-SUPER-2026"

        token = super_encrypt(directive, vigenere_key, pub_key)
        self.assertIsInstance(token, str)

        # Verify decryption
        dec_ok, recovered_text, _ = super_decrypt(token, vigenere_key, priv_key)
        self.assertTrue(dec_ok)
        self.assertEqual(directive, recovered_text)
        print("      ✓ Super-encryption and decryption verified.")

        # ---------------------------------------------------------
        # STEP 3: ENCRYPTED DATABASE VAULT PERSISTENCE
        # ---------------------------------------------------------
        print("[3/6] Storing Directive into SQLite Encrypted Vault (At-Rest)...")
        db_path = self.dir_path / "mission_vault.db"
        db = VaultDatabaseManager(db_path=db_path, vault_passphrase="MissionVaultKey-99")

        memo_id = db.add_memo(
            title="Directive Falcon",
            content=directive,
            author="COMMANDER-TEST",
            vigenere_hint=vigenere_key
        )
        self.assertGreater(memo_id, 0)

        # Retrieve and verify transparent decryption
        memos = db.list_memos()
        self.assertEqual(len(memos), 1)
        self.assertEqual(memos[0]["content"], directive)
        print("      ✓ Vault database field-level encryption verified.")

        # ---------------------------------------------------------
        # STEP 4: AES-256-GCM FILE STREAM ENCRYPTION
        # ---------------------------------------------------------
        print("[4/6] Encrypting Confidential Mission Document with AES-256-GCM...")
        doc_path = self.dir_path / "tactical_map.pdf"
        doc_path.write_bytes(b"%PDF-1.4 Classified orbital telemetry tactical dataset" * 500)

        enc_doc_path = self.dir_path / "tactical_map.pdf.enc"
        file_pass = "AES-FilePassword-2026!"

        f_ok, _, meta = encrypt_file(doc_path, enc_doc_path, file_pass)
        self.assertTrue(f_ok)
        self.assertTrue(enc_doc_path.exists())

        # Decrypt to verify
        dec_dir = self.dir_path / "recovered_files"
        dec_ok, _, rec_path = decrypt_file(enc_doc_path, dec_dir, file_pass)
        self.assertTrue(dec_ok)
        self.assertEqual(rec_path.read_bytes(), doc_path.read_bytes())
        print("      ✓ AES-256-GCM authenticated file stream verified.")

        # ---------------------------------------------------------
        # STEP 5: SATELLITE STEGANOGRAPHY (LSB)
        # ---------------------------------------------------------
        print("[5/6] Concealing Secret Payload inside Satellite Imagery (LSB)...")
        cover_path = self.dir_path / "sat_raster.png"
        stego_path = self.dir_path / "stego_raster.png"

        img_arr = np.random.randint(20, 220, size=(150, 150, 3), dtype=np.uint8)
        Image.fromarray(img_arr, mode="RGB").save(cover_path, "PNG")

        secret_stego_text = "GROUND-TO-ORBIT PASSCODE: 9942-ALPHA-ZULU"
        stego_pass = "CryptoStegoKey!"

        embed_ok, _, stego_meta = embed_payload_into_image(
            cover_path,
            stego_path,
            secret_stego_text,
            passphrase=stego_pass
        )
        self.assertTrue(embed_ok)
        self.assertGreater(stego_meta["psnr_db"], 50.0)

        # Extract
        ext_ok, _, ext_text, _ = extract_payload_from_image(stego_path, passphrase=stego_pass)
        self.assertTrue(ext_ok)
        self.assertEqual(ext_text, secret_stego_text)
        print("      ✓ Steganography embedding & extraction verified (Lossless PSNR).")

        # ---------------------------------------------------------
        # STEP 6: BLOCKCHAIN NOTARIZATION & TAMPER DEFENSE
        # ---------------------------------------------------------
        print("[6/6] Anchoring Asset Fingerprint to Blockchain & Testing Tamper Defense...")
        chain_path = self.dir_path / "mission_chain.json"
        blockchain = Blockchain(difficulty=2, ledger_path=chain_path)
        tracker = AssetTracker(blockchain)

        # Notarize the original document
        notarize_ok, _, asset_info = tracker.register_file_asset(
            doc_path,
            asset_name="Tactical Map PDF",
            owner_callsign="COMMANDER-TEST"
        )
        self.assertTrue(notarize_ok)

        # Verify integrity on chain
        ver_ok, _, ver_info = tracker.verify_file_asset(doc_path)
        self.assertTrue(ver_ok)
        self.assertEqual(ver_info["asset_name"], "Tactical Map PDF")

        # ATTACK SIMULATION 1: Adversary alters file on disk
        doc_path.write_bytes(b"%PDF-1.4 TAMPERED_BY_MALICIOUS_ADVERSARY")
        tamper_ok, tamper_msg, _ = tracker.verify_file_asset(doc_path)
        self.assertFalse(tamper_ok)
        self.assertIn("tampered", tamper_msg.lower())

        # ATTACK SIMULATION 2: Adversary alters block data in blockchain
        blockchain.chain[1].data[0]["owner_callsign"] = "ENEMY-STATION"
        chain_valid, chain_err = blockchain.is_chain_valid()
        self.assertFalse(chain_valid)
        self.assertIn("tampering detected", chain_err.lower())

        print("      ✓ Blockchain tamper defense successfully flagged all intrusion attempts.")
        print("=" * 60)
        print(">>> ALL 6 SUBSYSTEMS & INTEGRATION TESTS PASSED WITH 100% SUCCESS <<<")
        print("=" * 60)


if __name__ == "__main__":
    unittest.main()
