"""
AeroSat GroundStation - Extended Vigenère Cipher (Classical Cryptography)
Operates on the full byte space (modulo 256) to ensure 100% loss-free encryption
and decryption of UTF-8 characters, spaces, punctuation, numbers, and newlines.
"""
from core.utils.crypto_helpers import bytes_to_b64, b64_to_bytes


def vigenere_encrypt_bytes(data: bytes, key: str | bytes) -> bytes:
    """
    Encrypt raw bytes using Extended Vigenère Cipher (modulo 256).
    C_i = (P_i + K_(i mod len(K))) mod 256
    """
    if not data:
        return b""

    key_bytes = key.encode("utf-8") if isinstance(key, str) else key
    if not key_bytes:
        raise ValueError("Vigenère key cannot be empty.")

    key_len = len(key_bytes)
    ciphertext = bytearray(len(data))

    for i in range(len(data)):
        p_byte = data[i]
        k_byte = key_bytes[i % key_len]
        ciphertext[i] = (p_byte + k_byte) % 256

    return bytes(ciphertext)


def vigenere_decrypt_bytes(ciphertext: bytes, key: str | bytes) -> bytes:
    """
    Decrypt raw bytes using Extended Vigenère Cipher (modulo 256).
    P_i = (C_i - K_(i mod len(K))) mod 256
    """
    if not ciphertext:
        return b""

    key_bytes = key.encode("utf-8") if isinstance(key, str) else key
    if not key_bytes:
        raise ValueError("Vigenère key cannot be empty.")

    key_len = len(key_bytes)
    plaintext = bytearray(len(ciphertext))

    for i in range(len(ciphertext)):
        c_byte = ciphertext[i]
        k_byte = key_bytes[i % key_len]
        plaintext[i] = (c_byte - k_byte) % 256

    return bytes(plaintext)


def vigenere_encrypt_text(plaintext: str, key: str) -> str:
    """
    Encrypt UTF-8 plaintext string using Extended Vigenère.
    Returns Base64 encoded string for safe text representation.
    """
    if not plaintext:
        return ""
    plain_bytes = plaintext.encode("utf-8")
    cipher_bytes = vigenere_encrypt_bytes(plain_bytes, key)
    return bytes_to_b64(cipher_bytes)


def vigenere_decrypt_text(b64_ciphertext: str, key: str) -> str:
    """
    Decrypt Base64 ciphertext string back to UTF-8 plaintext using Extended Vigenère.
    """
    if not b64_ciphertext:
        return ""
    cipher_bytes = b64_to_bytes(b64_ciphertext)
    plain_bytes = vigenere_decrypt_bytes(cipher_bytes, key)
    return plain_bytes.decode("utf-8")
