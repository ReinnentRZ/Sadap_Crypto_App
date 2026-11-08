"""
Sadap GroundStation - USB Hardware Dongle Verifier
Validates physical possession of an authorized USB hardware token via
Volume Serial Number matching, physical USB bus/removable drive verification,
and cryptographic HMAC signature verification.
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
from ctypes import wintypes
import psutil

from config.settings import (
    USB_TOKEN_FILENAME,
    USB_SIGNATURE_MAGIC,
    DATA_DIR,
)
from core.utils.crypto_helpers import constant_time_compare
from core.utils.logger import get_logger

logger = get_logger("USBDongle")

# Master secret key for signing USB Dongle tokens
SYSTEM_DONGLE_MASTER_KEY = b"SADAP-GROUNDSTATION-SECRET-SIGNING-KEY-2026"
LEGACY_DONGLE_MASTER_KEY = b"AEROSAT-GROUNDSTATION-SECRET-SIGNING-KEY-2026"

VALID_TOKEN_FILENAMES = ["sadap.sig", "aerosat.sig"]
VALID_SIGNATURE_MAGICS = ["SADAP-UPLINK-KEY-v1.0", "AEROSAT-UPLINK-KEY-v1.0"]


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
                0,
            )
            if res != 0:
                # Format as Hex string e.g. 'A1B2-C3D4'
                serial_val = volume_serial.value
                high = (serial_val >> 16) & 0xFFFF
                low = serial_val & 0xFFFF
                return f"{high:04X}-{low:04X}"
        except Exception as e:
            logger.debug(f"Error querying volume serial for {drive_path}: {e}")

    # Fallback / Non-windows placeholder
    return "SERIAL-DEFAULT-0001"


def is_physical_usb_drive(mountpoint: str) -> tuple[bool, str]:
    """
    Check if a mountpoint belongs to an actual physical removable USB flash drive or external USB storage.
    Strictly filters out internal system drives (C:) and fixed internal hard drives (D:).
    """
    if platform.system() == "Windows":
        try:
            root = os.path.splitdrive(mountpoint)[0]
            letter = root.replace(":", "").strip()
            if not root.endswith("\\"):
                root += "\\"

            # 1. Primary OS drive (C:) is NEVER a USB dongle
            system_drive = os.environ.get("SystemDrive", "C:").upper().replace(":", "").strip()
            if letter.upper() == system_drive:
                return False, "Internal System Drive (C:)"

            # 2. Check DriveType via Win32 API
            # DRIVE_REMOVABLE = 2 (Standard USB Thumbdrive / Flashdisk)
            # DRIVE_FIXED = 3 (Fixed disk)
            dtype = ctypes.windll.kernel32.GetDriveTypeW(ctypes.c_wchar_p(root))
            if dtype == 2:
                return True, "Removable USB Flash Drive"

            # 3. For USB external HDDs/SSDs formatted as DRIVE_FIXED (3),
            # query low-level hardware bus type via IOCTL_STORAGE_QUERY_PROPERTY
            path = f"\\\\.\\{letter}:"
            FILE_SHARE_READ = 1
            FILE_SHARE_WRITE = 2
            OPEN_EXISTING = 3
            IOCTL_STORAGE_QUERY_PROPERTY = 0x002D1400

            handle = ctypes.windll.kernel32.CreateFileW(
                ctypes.c_wchar_p(path),
                0,
                FILE_SHARE_READ | FILE_SHARE_WRITE,
                None,
                OPEN_EXISTING,
                0,
                None,
            )
            if handle != -1 and handle != 0xFFFFFFFFFFFFFFFF:
                class STORAGE_PROPERTY_QUERY(ctypes.Structure):
                    _fields_ = [
                        ("PropertyId", ctypes.c_ulong),
                        ("QueryType", ctypes.c_ulong),
                        ("AdditionalParameters", ctypes.c_byte * 1),
                    ]

                query = STORAGE_PROPERTY_QUERY(0, 0)
                buf = (ctypes.c_byte * 1024)()
                bytes_returned = wintypes.DWORD()

                ok = ctypes.windll.kernel32.DeviceIoControl(
                    handle,
                    IOCTL_STORAGE_QUERY_PROPERTY,
                    ctypes.byref(query),
                    ctypes.sizeof(query),
                    ctypes.byref(buf),
                    ctypes.sizeof(buf),
                    ctypes.byref(bytes_returned),
                    None,
                )
                ctypes.windll.kernel32.CloseHandle(handle)

                # BusType is at offset 28 in STORAGE_DEVICE_DESCRIPTOR; BusTypeUsb = 0x07
                if ok and buf[28] == 0x07:
                    return True, "External USB Storage Device"

            return False, f"Fixed Internal Drive (Type {dtype})"
        except Exception as e:
            logger.debug(f"Error checking drive {mountpoint}: {e}")
            return False, str(e)
    else:
        # Linux / macOS fallback: check removable mount paths
        m = str(mountpoint).lower()
        if any(m.startswith(p) for p in ("/media", "/mnt", "/volumes", "/run/media")):
            return True, "Removable Storage Mount"
        return False, "System Mount"


def compute_token_signature(token_data: dict, secret_key: bytes = SYSTEM_DONGLE_MASTER_KEY) -> str:
    """Compute HMAC-SHA256 signature for token fields."""
    canonical = f"{token_data.get('magic')}|{token_data.get('token_id')}|{token_data.get('device_serial')}|{token_data.get('operator_callsign')}|{token_data.get('issued_timestamp')}"
    return hmac.new(secret_key, canonical.encode("utf-8"), hashlib.sha256).hexdigest()


def create_dongle_token(
    target_drive_or_dir: str,
    operator_callsign: str = "SADAP-ALPHA-OPERATOR",
    custom_serial: str | None = None,
) -> tuple[bool, str, dict]:
    """
    Initialize a USB drive or directory as an authorized Sadap hardware dongle.
    Writes sadap.sig (and aerosat.sig) with volume serial binding and cryptographic signature.
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

        # Write primary sadap.sig
        primary_file = target_path / USB_TOKEN_FILENAME
        with open(primary_file, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        # Also write legacy aerosat.sig for backward compatibility
        legacy_file = target_path / "aerosat.sig"
        legacy_payload = dict(payload)
        legacy_payload["magic"] = "AEROSAT-UPLINK-KEY-v1.0"
        legacy_payload["signature"] = compute_token_signature(legacy_payload, secret_key=LEGACY_DONGLE_MASTER_KEY)
        with open(legacy_file, "w", encoding="utf-8") as f:
            json.dump(legacy_payload, f, indent=2)

        return True, f"Dongle token written to {target_path} (Serial: {serial_number})", payload
    except Exception as e:
        return False, f"Failed to initialize dongle: {str(e)}", {}


def verify_token_payload(token_data: dict, current_serial: str) -> tuple[bool, str]:
    """Verify internal integrity and hardware serial binding of token payload."""
    magic = token_data.get("magic")
    if magic not in VALID_SIGNATURE_MAGICS:
        return False, "Invalid signature magic header."

    # Try modern and legacy signing keys
    actual_sig = token_data.get("signature", "")
    sig_valid = False
    for key in (SYSTEM_DONGLE_MASTER_KEY, LEGACY_DONGLE_MASTER_KEY):
        expected_sig = compute_token_signature(token_data, secret_key=key)
        if constant_time_compare(expected_sig.encode(), actual_sig.encode()):
            sig_valid = True
            break

    if not sig_valid:
        return False, "Cryptographic signature mismatch (Tampered or forged token)."

    # Verify Hardware Serial Binding
    token_serial = token_data.get("device_serial")
    if token_serial != current_serial:
        return False, f"Hardware serial mismatch: Token bound to {token_serial}, but mounted drive is {current_serial}."

    return True, "Dongle token verified and authentic."


def find_and_verify_dongle(allow_virtual: bool = False) -> tuple[bool, str, dict]:
    """
    Scan all mounted storage drives for an authorized physical USB dongle.
    Only physical removable / USB drives containing a valid signed token are accepted.
    If allow_virtual is True (for automated unit tests only), checks data/virtual_dongle.
    """
    # 1. Scan connected partitions for physical USB drives
    try:
        partitions = psutil.disk_partitions(all=False)
        for part in partitions:
            mount_path = Path(part.mountpoint)

            # Strict Physical USB / Removable Check
            is_usb, desc = is_physical_usb_drive(part.mountpoint)
            if not is_usb and not allow_virtual:
                continue

            # Check for valid token files on the drive
            for filename in VALID_TOKEN_FILENAMES:
                sig_file = mount_path / filename
                if sig_file.exists() and sig_file.is_file():
                    try:
                        with open(sig_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        current_serial = get_volume_serial_number(str(mount_path))
                        is_valid, msg = verify_token_payload(data, current_serial)
                        if is_valid:
                            return True, f"Authorized physical dongle found on {part.mountpoint} ({desc})", data
                    except Exception as e:
                        logger.debug(f"Error reading token on {part.mountpoint}: {e}")
                        continue
    except Exception as e:
        logger.error(f"Error scanning partitions for USB dongle: {e}")

    # 2. Check virtual simulation directory ONLY if explicitly enabled (e.g., test suites)
    if allow_virtual:
        virtual_dir = DATA_DIR / "virtual_dongle"
        for filename in VALID_TOKEN_FILENAMES:
            sig_file = virtual_dir / filename
            if sig_file.exists() and sig_file.is_file():
                try:
                    with open(sig_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    current_serial = get_volume_serial_number(str(virtual_dir))
                    is_valid, msg = verify_token_payload(data, current_serial)
                    if is_valid:
                        return True, f"Authorized test dongle detected in {virtual_dir}", data
                except Exception:
                    pass

    return False, "Hardware USB Dongle not detected. Physical USB Uplink Key required.", {}
