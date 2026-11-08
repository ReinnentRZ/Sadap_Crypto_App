"""
AeroSat GroundStation - Blockchain Ledger & Consensus Engine
Manages the distributed ledger, Proof of Work mining, chain integrity verification,
and persistent storage.
"""
import json
import time
from pathlib import Path

from config.settings import (
    BLOCKCHAIN_DIFFICULTY,
    BLOCKCHAIN_GENESIS_PREV_HASH,
    BLOCKCHAIN_PATH,
)
from core.blockchain.block import Block
from core.utils.logger import get_logger

logger = get_logger("Blockchain")


class Blockchain:
    """Manages the chain of blocks, PoW consensus, and tamper verification."""

    def __init__(self, difficulty: int = BLOCKCHAIN_DIFFICULTY, ledger_path: Path | str = BLOCKCHAIN_PATH):
        self.difficulty = difficulty
        self.ledger_path = Path(ledger_path)
        self.chain: list[Block] = []
        self.pending_transactions: list[dict] = []

        # Load existing ledger from disk or initialize fresh chain with Genesis Block
        if self.ledger_path.exists():
            if not self.load_from_file():
                logger.warning("Could not load existing blockchain ledger. Initializing Genesis Block.")
                self._initialize_genesis_block()
        else:
            self._initialize_genesis_block()

    def _initialize_genesis_block(self):
        """Create and mine the first block (Genesis Block) in the network."""
        genesis_data = [{
            "event": "GENESIS_NETWORK_INIT",
            "protocol": "AEROSAT-ORBIT-LEDGER-v1",
            "message": "AeroSat GroundStation Immutable Asset Ledger Online.",
            "timestamp": int(time.time()),
            "genesis_operator": "AEROSAT-HEADQUARTERS"
        }]

        genesis_block = Block(
            index=0,
            timestamp=int(time.time()),
            data=genesis_data,
            previous_hash=BLOCKCHAIN_GENESIS_PREV_HASH,
            nonce=0
        )
        genesis_block.mine_block(self.difficulty)
        self.chain = [genesis_block]
        self.save_to_file()
        logger.info(f"Genesis Block mined: Hash={genesis_block.hash}")

    def get_latest_block(self) -> Block:
        """Return the most recently mined block in the chain."""
        return self.chain[-1]

    def add_transaction(self, transaction_data: dict) -> int:
        """
        Add a new digital asset event to the pending transaction pool.
        Returns the index of the block that will include this transaction.
        """
        transaction_data["queued_at"] = int(time.time())
        self.pending_transactions.append(transaction_data)
        return len(self.chain)

    def mine_pending_transactions(self, miner_callsign: str = "AEROSAT-GROUND-STATION") -> Block:
        """
        Package pending transactions into a new Block and perform Proof of Work mining.
        Appends the mined block to the chain and persists to disk.
        """
        if not self.pending_transactions:
            # Create a heartbeat audit transaction if pool is empty
            self.pending_transactions.append({
                "event": "LEDGER_HEARTBEAT_AUDIT",
                "auditor": miner_callsign,
                "timestamp": int(time.time())
            })

        latest_block = self.get_latest_block()
        new_block = Block(
            index=len(self.chain),
            timestamp=int(time.time()),
            data=self.pending_transactions.copy(),
            previous_hash=latest_block.hash,
            nonce=0
        )

        logger.info(f"Mining Block #{new_block.index} with {len(self.pending_transactions)} transactions (Difficulty: {self.difficulty})...")
        new_block.mine_block(self.difficulty)
        logger.info(f"Block #{new_block.index} successfully mined! Hash: {new_block.hash} (Nonce: {new_block.nonce})")

        self.chain.append(new_block)
        self.pending_transactions = []
        self.save_to_file()
        return new_block

    def is_chain_valid(self) -> tuple[bool, str]:
        """
        Verify complete integrity of the blockchain:
        1. Every block's stored hash equals its recomputed hash.
        2. Every block's previous_hash matches the actual hash of the prior block.
        3. Every block's hash satisfies the Proof of Work difficulty prefix.
        Returns: (is_valid, report_message)
        """
        target_prefix = "0" * self.difficulty

        for i in range(len(self.chain)):
            current = self.chain[i]

            # 1. Check current block internal hash integrity
            if current.hash != current.compute_hash():
                return False, f"Tampering detected at Block #{i}! Data has been modified. Stored hash does not match computed hash."

            # 2. Check Proof of Work difficulty compliance
            if not current.hash.startswith(target_prefix):
                return False, f"PoW violation at Block #{i}! Hash does not satisfy difficulty requirement ({target_prefix})."

            # 3. Check linkage with previous block (for index >= 1)
            if i > 0:
                previous = self.chain[i - 1]
                if current.previous_hash != previous.hash:
                    return False, f"Chain linkage broken at Block #{i}! Previous hash ({current.previous_hash[:16]}...) does not match Block #{i-1} hash ({previous.hash[:16]}...)."

        return True, f"Blockchain integrity verified. All {len(self.chain)} blocks are authentic and immutable."

    def save_to_file(self, target_path: Path | str | None = None) -> bool:
        """Serialize full chain to JSON disk file."""
        p = Path(target_path or self.ledger_path)
        try:
            p.parent.mkdir(parents=True, exist_ok=True)
            serialized = [b.to_dict() for b in self.chain]
            with open(p, "w", encoding="utf-8") as f:
                json.dump(serialized, f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to persist blockchain: {e}")
            return False

    def load_from_file(self, source_path: Path | str | None = None) -> bool:
        """Load and reconstruct blockchain from JSON disk file."""
        p = Path(source_path or self.ledger_path)
        if not p.exists():
            return False

        try:
            with open(p, "r", encoding="utf-8") as f:
                data_list = json.load(f)

            loaded_chain = [Block.from_dict(d) for d in data_list]
            if not loaded_chain:
                return False

            self.chain = loaded_chain

            # Verify integrity immediately upon loading
            is_valid, msg = self.is_chain_valid()
            if not is_valid:
                logger.error(f"Security Alert: Loaded ledger is invalid! {msg}")
                return False

            logger.info(f"Loaded {len(self.chain)} verified blocks from {p}")
            return True
        except Exception as e:
            logger.error(f"Error loading blockchain ledger: {e}")
            return False


# Global singleton instance
_blockchain_instance: Blockchain | None = None


def get_blockchain() -> Blockchain:
    """Return shared Blockchain singleton instance."""
    global _blockchain_instance
    if _blockchain_instance is None:
        _blockchain_instance = Blockchain()
    return _blockchain_instance
