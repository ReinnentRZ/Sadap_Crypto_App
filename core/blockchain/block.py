"""
AeroSat GroundStation - Blockchain Block Structure
Defines an immutable block containing digital asset records, SHA-256 chaining,
and Proof of Work (PoW) consensus logic.
"""
import hashlib
import json
import time


class Block:
    """Represents a single tamper-evident block in the blockchain ledger."""

    def __init__(
        self,
        index: int,
        timestamp: int,
        data: list[dict] | dict,
        previous_hash: str,
        nonce: int = 0,
        hash_val: str | None = None
    ):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = hash_val if hash_val else self.compute_hash()

    def compute_hash(self) -> str:
        """
        Compute SHA-256 cryptographic hash of block contents.
        Uses canonical JSON serialization (sorted keys) to guarantee deterministic hashing.
        """
        canonical_data = json.dumps(self.data, sort_keys=True, separators=(",", ":"))
        block_content = f"{self.index}{self.timestamp}{canonical_data}{self.previous_hash}{self.nonce}"
        return hashlib.sha256(block_content.encode("utf-8")).hexdigest()

    def mine_block(self, difficulty: int):
        """
        Proof of Work (PoW) consensus mining.
        Iterates nonce until block hash starts with `difficulty` number of leading zeroes.
        """
        target_prefix = "0" * difficulty
        while not self.hash.startswith(target_prefix):
            self.nonce += 1
            self.hash = self.compute_hash()

    def to_dict(self) -> dict:
        """Serialize block to dictionary format for JSON storage."""
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "hash": self.hash
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Block":
        """Deserialize block from dictionary."""
        return cls(
            index=d["index"],
            timestamp=d["timestamp"],
            data=d["data"],
            previous_hash=d["previous_hash"],
            nonce=d["nonce"],
            hash_val=d["hash"]
        )

    def __repr__(self) -> str:
        return f"<Block #{self.index} Hash:{self.hash[:10]}... Prev:{self.previous_hash[:10]}... Nonce:{self.nonce}>"
