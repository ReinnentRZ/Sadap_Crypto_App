"""
AeroSat GroundStation - Digital Asset Tracker & Notary
Connects physical and digital intelligence files to the immutable blockchain ledger
for proof-of-existence, copyright provenance, and tamper detection.
"""
import uuid
import time
from pathlib import Path

from core.blockchain.chain import Blockchain, get_blockchain
from core.utils.crypto_helpers import sha256_hash_file
from core.utils.logger import get_logger

logger = get_logger("AssetTracker")


class AssetTracker:
    """Provides high-level digital asset registration and notarization on the blockchain."""

    def __init__(self, blockchain: Blockchain | None = None):
        self.blockchain = blockchain or get_blockchain()

    def register_file_asset(
        self,
        file_path: str | Path,
        asset_name: str,
        owner_callsign: str = "COMMANDER-ALPHA-01",
        metadata: dict | None = None
    ) -> tuple[bool, str, dict]:
        """
        Hash a file and record its ownership and fingerprint on the blockchain.
        Mines a new block immediately to anchor the asset immutably.
        """
        p = Path(file_path)
        if not p.exists():
            return False, f"Target file does not exist: {p}", {}

        try:
            file_hash = sha256_hash_file(str(p))
            file_size = p.stat().st_size
            asset_id = f"ASSET-{uuid.uuid4().hex[:12].upper()}"

            transaction = {
                "action": "REGISTER_DIGITAL_ASSET",
                "asset_id": asset_id,
                "asset_name": asset_name,
                "file_sha256": file_hash,
                "file_size_bytes": file_size,
                "owner_callsign": owner_callsign,
                "registered_at": int(time.time()),
                "metadata": metadata or {}
            }

            self.blockchain.add_transaction(transaction)
            mined_block = self.blockchain.mine_pending_transactions(miner_callsign=owner_callsign)

            result_info = {
                "asset_id": asset_id,
                "asset_name": asset_name,
                "file_sha256": file_hash,
                "block_index": mined_block.index,
                "block_hash": mined_block.hash,
                "owner": owner_callsign,
            }

            logger.info(f"Asset '{asset_name}' ({asset_id}) registered in Block #{mined_block.index}")
            return True, f"Asset successfully registered in Block #{mined_block.index}", result_info

        except Exception as e:
            return False, f"Asset registration failed: {str(e)}", {}

    def verify_file_asset(self, file_path: str | Path) -> tuple[bool, str, dict | None]:
        """
        Calculate current SHA-256 hash of a file on disk and search the blockchain.
        Verifies both file authenticity and chain integrity.
        """
        p = Path(file_path)
        if not p.exists():
            return False, f"File not found: {p}", None

        # 1. Verify chain validity first
        chain_ok, chain_msg = self.blockchain.is_chain_valid()
        if not chain_ok:
            return False, f"Security Warning: Blockchain is corrupted! {chain_msg}", None

        # 2. Compute current file hash
        current_hash = sha256_hash_file(str(p))

        # 3. Search chain blocks for matching asset
        for block in reversed(self.blockchain.chain):
            transactions = block.data if isinstance(block.data, list) else [block.data]
            for tx in transactions:
                if isinstance(tx, dict) and tx.get("file_sha256") == current_hash:
                    info = {
                        "asset_id": tx.get("asset_id"),
                        "asset_name": tx.get("asset_name"),
                        "owner": tx.get("owner_callsign"),
                        "file_sha256": current_hash,
                        "block_index": block.index,
                        "block_hash": block.hash,
                        "block_timestamp": block.timestamp,
                    }
                    return True, f"Asset verified! Authentic record found in Block #{block.index}.", info

        return False, f"Unregistered or tampered file! SHA-256 ({current_hash[:16]}...) does not match any blockchain block.", None

    def list_all_assets(self) -> list[dict]:
        """Scan all blocks and return unique list of registered assets."""
        assets = []
        seen_ids = set()

        for block in self.blockchain.chain:
            transactions = block.data if isinstance(block.data, list) else [block.data]
            for tx in transactions:
                if isinstance(tx, dict) and tx.get("action") == "REGISTER_DIGITAL_ASSET":
                    aid = tx.get("asset_id")
                    if aid and aid not in seen_ids:
                        seen_ids.add(aid)
                        assets.append({
                            "asset_id": aid,
                            "asset_name": tx.get("asset_name"),
                            "owner": tx.get("owner_callsign"),
                            "file_sha256": tx.get("file_sha256"),
                            "file_size": tx.get("file_size_bytes"),
                            "block_index": block.index,
                            "timestamp": tx.get("registered_at"),
                        })
        return assets
