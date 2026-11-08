"""
AeroSat GroundStation - RSA Engine (Modern Asymmetric Cryptography)
Implements RSA-2048/4096 keypair generation, PEM serialization, and chunked
RSA-OAEP encryption/decryption supporting arbitrary payload lengths.
"""
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives import hashes, serialization
from config.settings import (
    RSA_KEY_SIZE,
    RSA_PUBLIC_EXPONENT,
    DATA_DIR,
)
from core.utils.logger import get_logger

logger = get_logger("RSAEngine")

DEFAULT_PRIVATE_KEY_PATH = DATA_DIR / "keys" / "rsa_private.pem"
DEFAULT_PUBLIC_KEY_PATH = DATA_DIR / "keys" / "rsa_public.pem"


def generate_rsa_keypair(key_size: int = RSA_KEY_SIZE) -> tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey]:
    """Generate RSA private and public keypair."""
    private_key = rsa.generate_private_key(
        public_exponent=RSA_PUBLIC_EXPONENT,
        key_size=key_size
    )
    public_key = private_key.public_key()
    return private_key, public_key


def export_private_key_pem(private_key: rsa.RSAPrivateKey, password: str | None = None) -> bytes:
    """Serialize private key to PEM format (optionally encrypted with password)."""
    if password:
        encryption_algorithm = serialization.BestAvailableEncryption(password.encode("utf-8"))
    else:
        encryption_algorithm = serialization.NoEncryption()

    pem = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=encryption_algorithm
    )
    return pem


def export_public_key_pem(public_key: rsa.RSAPublicKey) -> bytes:
    """Serialize public key to standard SubjectPublicKeyInfo PEM format."""
    pem = public_key.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo
    )
    return pem


def load_private_key_pem(pem_bytes: bytes, password: str | None = None) -> rsa.RSAPrivateKey:
    """Deserialize private key from PEM bytes."""
    pwd_bytes = password.encode("utf-8") if password else None
    return serialization.load_pem_private_key(pem_bytes, password=pwd_bytes)


def load_public_key_pem(pem_bytes: bytes) -> rsa.RSAPublicKey:
    """Deserialize public key from PEM bytes."""
    return serialization.load_pem_public_key(pem_bytes)


def get_oaep_padding() -> padding.OAEP:
    """Standard OAEP padding with SHA-256 for optimal security."""
    return padding.OAEP(
        mgf=padding.MGF1(algorithm=hashes.SHA256()),
        algorithm=hashes.SHA256(),
        label=None
    )


def rsa_encrypt_bytes(data: bytes, public_key: rsa.RSAPublicKey) -> bytes:
    """
    Encrypt raw bytes using RSA-OAEP with automatic chunking.
    Supports arbitrarily large data by processing in chunks of (k_bytes - 66).
    """
    if not data:
        return b""

    key_size_bytes = public_key.key_size // 8
    # OAEP SHA-256 overhead: 2 * hLen + 2 = 2 * 32 + 2 = 66 bytes
    max_chunk_size = key_size_bytes - 66

    oaep = get_oaep_padding()
    encrypted_chunks = bytearray()

    offset = 0
    while offset < len(data):
        chunk = data[offset: offset + max_chunk_size]
        enc_chunk = public_key.encrypt(chunk, oaep)
        encrypted_chunks.extend(enc_chunk)
        offset += max_chunk_size

    return bytes(encrypted_chunks)


def rsa_decrypt_bytes(ciphertext: bytes, private_key: rsa.RSAPrivateKey) -> bytes:
    """
    Decrypt chunked RSA-OAEP ciphertext back into original raw bytes.
    Splits ciphertext into blocks of key_size_bytes and decrypts each block.
    """
    if not ciphertext:
        return b""

    key_size_bytes = private_key.key_size // 8
    if len(ciphertext) % key_size_bytes != 0:
        raise ValueError(
            f"Invalid RSA ciphertext length ({len(ciphertext)} bytes). Must be multiple of {key_size_bytes}."
        )

    oaep = get_oaep_padding()
    decrypted_chunks = bytearray()

    for i in range(0, len(ciphertext), key_size_bytes):
        block = ciphertext[i: i + key_size_bytes]
        dec_chunk = private_key.decrypt(block, oaep)
        decrypted_chunks.extend(dec_chunk)

    return bytes(decrypted_chunks)


def get_or_create_default_keypair(
    key_size: int = RSA_KEY_SIZE
) -> tuple[rsa.RSAPrivateKey, rsa.RSAPublicKey]:
    """
    Load default system RSA keypair from data/keys or generate new ones if absent.
    """
    DEFAULT_PRIVATE_KEY_PATH.parent.mkdir(parents=True, exist_ok=True)

    if DEFAULT_PRIVATE_KEY_PATH.exists() and DEFAULT_PUBLIC_KEY_PATH.exists():
        try:
            with open(DEFAULT_PRIVATE_KEY_PATH, "rb") as f:
                priv = load_private_key_pem(f.read())
            with open(DEFAULT_PUBLIC_KEY_PATH, "rb") as f:
                pub = load_public_key_pem(f.read())
            return priv, pub
        except Exception as e:
            logger.warning(f"Could not load existing RSA keypair: {e}. Generating new keypair.")

    # Generate and persist
    priv, pub = generate_rsa_keypair(key_size)
    with open(DEFAULT_PRIVATE_KEY_PATH, "wb") as f:
        f.write(export_private_key_pem(priv))
    with open(DEFAULT_PUBLIC_KEY_PATH, "wb") as f:
        f.write(export_public_key_pem(pub))

    logger.info(f"Generated new {key_size}-bit RSA keypair in {DEFAULT_PRIVATE_KEY_PATH.parent}")
    return priv, pub
