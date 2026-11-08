"""
AeroSat GroundStation - USB Hardware Dongle Verifier
Validates physical possession of an authorized USB hardware token via
Volume Serial Number matching and cryptographic HMAC signature verification.
"""
import ctypes
import hmac
import hashlib
import json
import os
import platform
import uuid
import time
from pathlib import Path
import psutil

from config.settings import (
    USB_TOKEN_FILENAME,
    USB_SIGNATURE_MAGIC,
    DATA_DIR,
)
from core.utils.crypto_helpers import constant_time_compare

# System-level master secret for signing USB Dongle tokens
SYSTEM_DONGLE_MASTER_KEY = b"AEROSAT-GROUNDSTATION-SECRET-SIGNING-KEY-2026"


def get_volume_serial_number(drive_path: str) -> str:
    """
    Retrieve the Hardware Volume Serial Number of a drive.
    On Windows, uses kernel32.GetVolumeInformationW.
    """
    if platform.system() == "Windows":
        try:
            # Ensure format is 'X:\\'
            root = os.path.splitdrive(drive_path)[0]
            if not root.endswith("\\"):
                root += "\\"

            volume_serial = ctypes.c_ulong()
            max_comp_len = ctypes.c_ulong()
            file_system_flags = ctypes.c_ulong()

            res = ctypes.windll.kernel32.GetVolumeInformationW(
                ctypes.c_wchar_p(root),
                None,
                0,
                ctypes.byref(volume_serial),
                ctypes.byref(max_comp_len),
                ctypes.byref(file_system_flags),
                None,
                0
            )
            if res != 0:
                # Format as Hex string e.g. 'A1B2-C3D4'
                serial_val = volume_serial.value
                high = (serial_val >> 16) & 0xFFFF
                low = serial_val & 0xFFFF
                return f"{high:04X}-{low:04X}"
        except Exception:
            pass

    # Fallback / Non-windows placeholder
    return "SERIAL-DEFAULT-0001"


def compute_token_signature(token_data: dict, secret_key: bytes = SYSTEM_DONGLE_MASTER_KEY) -> str:
    """Compute HMAC-SHA256 signature for token fields."""
    canonical = f"{token_data.get('magic')}|{token_data.get('token_id')}|{token_data.get('device_serial')}|{token_data.get('operator_callsign')}|{token_data.get('issued_timestamp')}"
    return hmac.new(secret_key, canonical.encode("utf-8"), hashlib.sha256).hexdigest()


def create_dongle_token(
    target_drive_or_dir: str,
    operator_callsign: str = "AEROSAT-ALPHA-OPERATOR",
    custom_serial: str | None = None
) -> tuple[bool, str, dict]:
    """
    Initialize a USB drive or directory as an authorized AeroSat hardware dongle.
    Writes aerosat.sig with volume serial binding and cryptographic signature.
    """
    try:
        target_path = Path(target_drive_or_dir)
        if not target_path.exists():
            target_path.mkdir(parents=True, exist_ok=True)

        # Detect serial number of drive or use custom/virtual serial
        serial_number = custom_serial or get_volume_serial_number(str(target_path))

        token_id = str(uuid.uuid4())
        issued_timestamp = int(time.time())

        payload = {
            "magic": USB_SIGNATURE_MAGIC,
            "token_id": token_id,
            "device_serial": serial_number,
            "operator_callsign": operator_callsign,
            "issued_timestamp": issued_timestamp,
        }

        signature = compute_token_signature(payload)
        payload["signature"] = signature

        out_file = target_path / USB_TOKEN_FILENAME
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        return True, f"Dongle initialized at {out_file}", payload
    except Exception as e:
        return False, f"Failed to initialize dongle: {str(e)}", {}


def verify_token_payload(token_data: dict, current_serial: str) -> tuple[bool, str]:
    """Verify internal integrity and hardware serial binding of token payload."""
    magic = token_data.get("magic")
    if magic != USB_SIGNATURE_MAGIC:
        return False, "Invalid signature magic header."

    expected_sig = compute_token_signature(token_data)
    actual_sig = token_data.get("signature", "")

    if not constant_time_compare(expected_sig.encode(), actual_sig.encode()):
        return False, "Cryptographic signature mismatch (Tampered token)."

    # Verify Hardware Serial Binding
    token_serial = token_data.get("device_serial")
    if token_serial != current_serial:
        return False, f"Hardware serial mismatch: Token is bound to {token_serial}, but inserted drive is {current_serial}."

    return True, "Dongle token verified and authentic."


def find_and_verify_dongle(allow_virtual: bool = True) -> tuple[bool, str, dict]:
    """
    Scan all mounted removable/storage drives for the authorized USB dongle.
    If allow_virtual is True, also checks data/virtual_dongle for simulation/testing.
    """
    # 1. Scan physical disk partitions
    try:
        partitions = psutil.disk_partitions(all=False)
        for part in partitions:
            # Check for drive containing the signature file
            mount_path = Path(part.mountpoint)
            sig_file = mount_path / USB_TOKEN_FILENAME
            if sig_file.exists() and sig_file.is_file():
                try:
                    with open(sig_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    current_serial = get_volume_serial_number(str(mount_path))
                    is_valid, msg = verify_token_payload(data, current_serial)
                    if is_valid:
                        return True, f"Authorized physical dongle found on {part.mountpoint} ({msg})", data
                except Exception:
                    continue
    except Exception:
        pass

    # 2. Check virtual dongle simulation directory if permitted
    if allow_virtual:
        virtual_dir = DATA_DIR / "virtual_dongle"
        sig_file = virtual_dir / USB_TOKEN_FILENAME
        if sig_file.exists():
            try:
                with open(sig_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                current_serial = get_volume_serial_number(str(virtual_dir))
                is_valid, msg = verify_token_payload(data, current_serial)
                if is_valid:
                    return True, f"Authorized virtual dongle detected in {virtual_dir}", data
            except Exception:
                pass

    return False, "Hardware USB Dongle not detected. Uplink Key required.", {}
