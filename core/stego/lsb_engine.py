"""
AeroSat GroundStation - LSB Image Steganography Engine
Embeds and extracts arbitrary secret payloads into the Least Significant Bit (LSB)
of lossless image color channels (PNG/BMP) with optional AES-256 pre-encryption.
"""
import math
import struct
from pathlib import Path
import numpy as np
from PIL import Image

from config.settings import STEGO_MAGIC_BYTES
from core.crypto.file_aes import encrypt_bytes, decrypt_bytes
from core.utils.logger import get_logger

logger = get_logger("StegoEngine")

# Header: [MAGIC 4B] + [FLAGS 1B] + [PAYLOAD_LEN 4B] = 9 Bytes (72 bits)
HEADER_SIZE_BYTES = 9
FLAG_ENCRYPTED = 0x01


def calculate_image_capacity(img_width: int, img_height: int) -> int:
    """
    Calculate maximum secret payload capacity in bytes for an RGB image.
    Formula: floor((Width * Height * 3) / 8) - HEADER_SIZE_BYTES
    """
    total_channel_bytes = img_width * img_height * 3
    max_bytes = (total_channel_bytes // 8) - HEADER_SIZE_BYTES
    return max(0, max_bytes)


def calculate_psnr(original_arr: np.ndarray, stego_arr: np.ndarray) -> float:
    """
    Compute Peak Signal-to-Noise Ratio (PSNR) in decibels between original and stego image.
    Values > 50 dB indicate distortion is completely imperceptible to human eyes.
    """
    mse = np.mean((original_arr.astype(np.float64) - stego_arr.astype(np.float64)) ** 2)
    if mse == 0:
        return 100.0  # Perfect match
    max_pixel = 255.0
    psnr = 20 * math.log10(max_pixel / math.sqrt(mse))
    return float(psnr)


def embed_payload_into_image(
    cover_image_path: str | Path,
    output_image_path: str | Path,
    payload_data: bytes | str,
    passphrase: str | None = None
) -> tuple[bool, str, dict]:
    """
    Embed secret payload into cover image using LSB steganography.
    If passphrase is provided, payload is pre-encrypted with AES-256-GCM.
    """
    try:
        cover_p = Path(cover_image_path)
        out_p = Path(output_image_path)

        if not cover_p.exists():
            return False, f"Cover image not found: {cover_p}", {}

        # Load image and ensure RGB mode
        with Image.open(cover_p) as img:
            rgb_img = img.convert("RGB")
            w, h = rgb_img.size
            img_arr = np.array(rgb_img, dtype=np.uint8)

        # Prepare payload
        if isinstance(payload_data, str):
            raw_payload = payload_data.encode("utf-8")
        else:
            raw_payload = payload_data

        flags = 0
        if passphrase:
            flags |= FLAG_ENCRYPTED
            final_payload = encrypt_bytes(raw_payload, passphrase)
        else:
            final_payload = raw_payload

        # Build 9-byte binary header
        header = (
            STEGO_MAGIC_BYTES +
            struct.pack("!B", flags) +
            struct.pack("!I", len(final_payload))
        )
        data_to_embed = header + final_payload

        total_bits_needed = len(data_to_embed) * 8
        total_available_pixels = w * h * 3

        if total_bits_needed > total_available_pixels:
            max_capacity = calculate_image_capacity(w, h)
            return False, (
                f"Payload exceeds image capacity! Required: {len(final_payload)} bytes, "
                f"Maximum allowed: {max_capacity} bytes."
            ), {}

        # Unpack bytes into array of individual bits (0 or 1)
        bits = np.unpackbits(np.frombuffer(data_to_embed, dtype=np.uint8))

        # Flatten image array for fast vectorized LSB substitution
        stego_arr = img_arr.copy()
        flat = stego_arr.reshape(-1)

        # Vectorized bit embedding: clear LSB with 0xFE and OR with secret bit
        flat[:len(bits)] = (flat[:len(bits)] & 0xFE) | bits

        # Reshape back to (H, W, 3)
        stego_arr = flat.reshape((h, w, 3))

        # Save as lossless PNG
        out_p.parent.mkdir(parents=True, exist_ok=True)
        stego_img = Image.fromarray(stego_arr, mode="RGB")
        stego_img.save(out_p, format="PNG")

        # Quality metrics
        psnr_score = calculate_psnr(img_arr, stego_arr)

        metadata = {
            "image_width": w,
            "image_height": h,
            "payload_bytes": len(raw_payload),
            "is_encrypted": bool(passphrase),
            "psnr_db": round(psnr_score, 2),
            "capacity_used_percent": round((total_bits_needed / total_available_pixels) * 100, 2),
        }

        return True, f"Secret payload embedded successfully (PSNR: {psnr_score:.2f} dB).", metadata

    except Exception as e:
        return False, f"Embedding failed: {str(e)}", {}


def extract_payload_from_image(
    stego_image_path: str | Path,
    passphrase: str | None = None
) -> tuple[bool, str, bytes | str | None, dict]:
    """
    Extract secret payload from a stego image by reading LSB header and payload bits.
    Returns: (success, message, extracted_data_bytes_or_str, metadata)
    """
    try:
        stego_p = Path(stego_image_path)
        if not stego_p.exists():
            return False, f"Image file not found: {stego_p}", None, {}

        with Image.open(stego_p) as img:
            rgb_img = img.convert("RGB")
            w, h = rgb_img.size
            img_arr = np.array(rgb_img, dtype=np.uint8)

        flat = img_arr.reshape(-1)
        total_pixels = len(flat)

        # 1. Read Header Bits: 9 Bytes * 8 = 72 Bits
        header_bits_count = HEADER_SIZE_BYTES * 8
        if total_pixels < header_bits_count:
            return False, "Image too small to contain AeroSat stego header.", None, {}

        header_bits = flat[:header_bits_count] & 1
        header_bytes = np.packbits(header_bits).tobytes()

        # 2. Parse Header
        magic = header_bytes[:4]
        if magic != STEGO_MAGIC_BYTES:
            return False, "No AeroSat stego signature detected in this image.", None, {}

        flags = header_bytes[4]
        is_encrypted = bool(flags & FLAG_ENCRYPTED)
        payload_len = struct.unpack("!I", header_bytes[5:9])[0]

        total_bits_needed = (HEADER_SIZE_BYTES + payload_len) * 8
        if total_bits_needed > total_pixels:
            return False, f"Corrupted stego header: payload length ({payload_len} B) exceeds image capacity.", None, {}

        # 3. Read Payload Bits
        all_bits = flat[:total_bits_needed] & 1
        all_bytes = np.packbits(all_bits).tobytes()
        embedded_payload = all_bytes[HEADER_SIZE_BYTES: HEADER_SIZE_BYTES + payload_len]

        # 4. Decrypt if pre-encrypted
        if is_encrypted:
            if not passphrase:
                return (
                    False,
                    "Payload is protected with AES-256 encryption. Passphrase required to extract.",
                    None,
                    {"is_encrypted": True, "payload_len": payload_len}
                )
            try:
                decrypted_bytes = decrypt_bytes(embedded_payload, passphrase)
                final_data = decrypted_bytes
            except Exception:
                return False, "Decryption failed! Incorrect passphrase or corrupted stego data.", None, {}
        else:
            final_data = embedded_payload

        # Attempt UTF-8 text decode for convenience if valid text
        try:
            result_output = final_data.decode("utf-8")
        except UnicodeDecodeError:
            result_output = final_data

        metadata = {
            "image_width": w,
            "image_height": h,
            "payload_length_bytes": len(final_data),
            "is_encrypted": is_encrypted,
        }

        return True, "Payload extracted successfully.", result_output, metadata

    except Exception as e:
        return False, f"Extraction failed: {str(e)}", None, {}
