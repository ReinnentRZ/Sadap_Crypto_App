"""
AeroSat GroundStation - Super-Encryption Pipeline
Combines Extended Vigenère (Classical) and RSA-OAEP (Modern Asymmetric) into a unified,
tamper-evident double-layer ciphertext protocol.
"""
import json
import time
from cryptography.hazmat.primitives.asymmetric import rsa

from core.crypto.vigenere import vigenere_encrypt_bytes, vigenere_decrypt_bytes
from core.crypto.rsa_engine import rsa_encrypt_bytes, rsa_decrypt_bytes
from core.utils.crypto_helpers import bytes_to_b64, b64_to_bytes, sha256_hash


def super_encrypt(
    plaintext: str,
    vigenere_key: str,
    public_key: rsa.RSAPublicKey
) -> str:
    """
    Execute 2-layer Super-Encryption:
    Plaintext -> Extended Vigenère (mod 256) -> RSA-OAEP (2048/4096-bit) -> Serialized JSON Token
    """
    if not plaintext:
        raise ValueError("Plaintext cannot be empty.")
    if not vigenere_key:
        raise ValueError("Vigenère key cannot be empty.")

    plain_bytes = plaintext.encode("utf-8")

    # Layer 1: Classical Extended Vigenère
    vigenere_intermediate = vigenere_encrypt_bytes(plain_bytes, vigenere_key)

    # Layer 2: Modern RSA-OAEP
    rsa_ciphertext = rsa_encrypt_bytes(vigenere_intermediate, public_key)

    # Security envelope
    payload_b64 = bytes_to_b64(rsa_ciphertext)
    digest = sha256_hash(rsa_ciphertext)

    packet = {
        "protocol": "AEROSAT-SUPER-CIPHER-v1",
        "layers": ["Extended-Vigenere-mod256", "RSA-OAEP-SHA256"],
        "timestamp": int(time.time()),
        "payload_b64": payload_b64,
        "payload_sha256": digest
    }

    # Output clean serialized token
    raw_json = json.dumps(packet, separators=(",", ":"))
    return bytes_to_b64(raw_json.encode("utf-8"))


def super_decrypt(
    token_str: str,
    vigenere_key: str,
    private_key: rsa.RSAPrivateKey
) -> tuple[bool, str, str]:
    """
    Execute 2-layer Super-Decryption:
    Serialized Token -> RSA-OAEP Decryption -> Extended Vigenère Decryption -> Plaintext
    Returns: (is_success, plaintext_or_empty, status_message)
    """
    if not token_str:
        return False, "", "Ciphertext token is empty."
    if not vigenere_key:
        return False, "", "Vigenère key is required."

    try:
        # Step 1: Unpack security envelope
        try:
            # Check if token is Base64 encoded JSON
            json_bytes = b64_to_bytes(token_str)
            packet = json.loads(json_bytes.decode("utf-8"))
        except Exception:
            # Fallback if raw JSON string was passed
            packet = json.loads(token_str)

        if packet.get("protocol") != "AEROSAT-SUPER-CIPHER-v1":
            return False, "", "Incompatible ciphertext protocol header."

        payload_b64 = packet.get("payload_b64")
        expected_digest = packet.get("payload_sha256")
        rsa_ciphertext = b64_to_bytes(payload_b64)

        # Integrity check
        actual_digest = sha256_hash(rsa_ciphertext)
        if actual_digest != expected_digest:
            return False, "", "Ciphertext integrity verification failed (Payload corrupted or tampered)."

        # Step 2: Modern RSA-OAEP Decryption
        try:
            vigenere_intermediate = rsa_decrypt_bytes(rsa_ciphertext, private_key)
        except Exception as e:
            return False, "", f"RSA Decryption failed (Incorrect private key or corrupt data): {str(e)}"

        # Step 3: Classical Extended Vigenère Decryption
        try:
            plain_bytes = vigenere_decrypt_bytes(vigenere_intermediate, vigenere_key)
            plaintext = plain_bytes.decode("utf-8")
            return True, plaintext, "Super-decryption successful."
        except UnicodeDecodeError:
            return False, "", "Vigenère decryption produced invalid text (Incorrect Vigenère key)."
        except Exception as e:
            return False, "", f"Vigenère decryption error: {str(e)}"

    except Exception as e:
        return False, "", f"Failed to parse super-cipher token: {str(e)}"
