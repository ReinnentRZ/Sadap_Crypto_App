"""
Unit and Integration Tests for Phase 7: Simple Blockchain Ledger & Asset Notary
"""
import shutil
import tempfile
import unittest
from pathlib import Path

from core.blockchain.block import Block
from core.blockchain.chain import Blockchain
from core.blockchain.asset_tracker import AssetTracker


class TestBlockchain(unittest.TestCase):
    """Test suite for simple blockchain, PoW consensus, and digital asset notarization."""

    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="aerosat_chain_test_")
        self.ledger_file = Path(self.test_dir) / "test_ledger.json"
        # Use low difficulty (2) for super-fast unit testing
        self.blockchain = Blockchain(difficulty=2, ledger_path=self.ledger_file)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_genesis_block_creation(self):
        self.assertEqual(len(self.blockchain.chain), 1)
        genesis = self.blockchain.get_latest_block()

        self.assertEqual(genesis.index, 0)
        self.assertTrue(genesis.hash.startswith("00"))
        self.assertEqual(genesis.previous_hash, "0" * 64)

        # Integrity check
        valid, msg = self.blockchain.is_chain_valid()
        self.assertTrue(valid)

    def test_mine_block_and_chaining(self):
        # Add pending transactions
        tx1 = {"action": "ASSET_REGISTRATION", "item": "Satellite Directive #1"}
        tx2 = {"action": "ASSET_REGISTRATION", "item": "Orbit Radar Map"}

        self.blockchain.add_transaction(tx1)
        self.blockchain.add_transaction(tx2)

        mined_block = self.blockchain.mine_pending_transactions(miner_callsign="STATION-TEST")

        self.assertEqual(len(self.blockchain.chain), 2)
        self.assertEqual(mined_block.index, 1)
        self.assertTrue(mined_block.hash.startswith("00"))
        self.assertEqual(mined_block.previous_hash, self.blockchain.chain[0].hash)

        # Whole chain must be valid
        valid, msg = self.blockchain.is_chain_valid()
        self.assertTrue(valid)
        self.assertIn("verified", msg.lower())

    def test_tamper_detection_data_modification(self):
        """Simulate malicious alteration of transaction data in a past block."""
        self.blockchain.add_transaction({"asset": "Secret Satellite Blueprint", "owner": "COMMANDER"})
        self.blockchain.mine_pending_transactions()

        self.assertEqual(len(self.blockchain.chain), 2)

        # Attacker modifies data in Block #1
        self.blockchain.chain[1].data[0]["owner"] = "MALICIOUS-INTRUDER"

        # Verification must catch this tampering!
        valid, msg = self.blockchain.is_chain_valid()
        self.assertFalse(valid)
        self.assertIn("tampering detected", msg.lower())

    def test_tamper_detection_broken_chain_link(self):
        """Simulate recomputing one block's hash without fixing the next block's previous_hash."""
        # Add block 1
        self.blockchain.add_transaction({"asset": "Asset A"})
        self.blockchain.mine_pending_transactions()

        # Add block 2
        self.blockchain.add_transaction({"asset": "Asset B"})
        self.blockchain.mine_pending_transactions()

        self.assertEqual(len(self.blockchain.chain), 3)

        # Attacker modifies Block #1 and updates Block #1 hash to match
        self.blockchain.chain[1].data[0]["asset"] = "Hacked Asset"
        self.blockchain.chain[1].hash = self.blockchain.chain[1].compute_hash()

        # Chain link between Block 1 and Block 2 is now broken!
        valid, msg = self.blockchain.is_chain_valid()
        self.assertFalse(valid)
        self.assertTrue("linkage broken" in msg.lower() or "pow violation" in msg.lower())

    def test_blockchain_persistence(self):
        self.blockchain.add_transaction({"memo": "Persistent Blockchain Entry"})
        self.blockchain.mine_pending_transactions()

        self.assertTrue(self.ledger_file.exists())

        # Load into brand new blockchain instance from same JSON file
        new_chain = Blockchain(difficulty=2, ledger_path=self.ledger_file)
        self.assertEqual(len(new_chain.chain), 2)
        valid, _ = new_chain.is_chain_valid()
        self.assertTrue(valid)
        self.assertEqual(new_chain.chain[1].hash, self.blockchain.chain[1].hash)

    def test_asset_tracker_registration_and_verification(self):
        tracker = AssetTracker(self.blockchain)

        # Create dummy file to notarize
        dummy_file = Path(self.test_dir) / "classified_telemetry.dat"
        dummy_file.write_bytes(b"TELEMETRY-VECTOR: LAT 10.5, LON 120.4, ALT 550KM")

        # 1. Register asset
        reg_ok, reg_msg, asset_meta = tracker.register_file_asset(
            dummy_file,
            asset_name="Classified Telemetry Data",
            owner_callsign="COMMANDER-01"
        )
        self.assertTrue(reg_ok)
        self.assertEqual(asset_meta["owner"], "COMMANDER-01")

        # 2. Verify unmodified file
        ver_ok, ver_msg, ver_info = tracker.verify_file_asset(dummy_file)
        self.assertTrue(ver_ok)
        self.assertIsNotNone(ver_info)
        self.assertEqual(ver_info["asset_name"], "Classified Telemetry Data")

        # 3. Modify 1 byte of the file (tamper simulation)
        dummy_file.write_bytes(b"TELEMETRY-VECTOR: LAT 99.9, LON 999.9, ALT 000KM")

        # Verification must now FAIL!
        tamper_ok, tamper_msg, _ = tracker.verify_file_asset(dummy_file)
        self.assertFalse(tamper_ok)
        self.assertIn("tampered", tamper_msg.lower())


if __name__ == "__main__":
    unittest.main()
