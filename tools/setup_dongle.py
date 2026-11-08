"""
CLI Utility: Initialize Hardware USB Dongle or Virtual Dongle for AeroSat GroundStation
"""
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.auth.usb_dongle import create_dongle_token, find_and_verify_dongle
from config.settings import DATA_DIR
import psutil


def main():
    print("=" * 60)
    print("  AEROSAT GROUNDSTATION - USB DONGLE SETUP UTILITY")
    print("=" * 60)

    # 1. Detect available drives
    partitions = psutil.disk_partitions(all=False)
    print("\n[+] Scanning connected storage drives:")
    drive_list = []
    for i, p in enumerate(partitions, start=1):
        drive_list.append(p.mountpoint)
        print(f"  [{i}] Drive: {p.mountpoint} | FileSystem: {p.fstype} | Opts: {p.opts}")

    virtual_opt_num = len(drive_list) + 1
    print(f"  [{virtual_opt_num}] [VIRTUAL SIMULATION] Create Dongle in {DATA_DIR / 'virtual_dongle'}")

    choice = input(f"\nSelect target (1-{virtual_opt_num}) [Default: {virtual_opt_num}]: ").strip()
    if not choice:
        choice = str(virtual_opt_num)

    try:
        idx = int(choice)
        if idx == virtual_opt_num:
            target_path = str(DATA_DIR / "virtual_dongle")
        elif 1 <= idx <= len(drive_list):
            target_path = drive_list[idx - 1]
        else:
            print("[-] Invalid selection.")
            return
    except ValueError:
        print("[-] Invalid input.")
        return

    callsign = input("Enter Operator Callsign [AEROSAT-ALPHA-01]: ").strip()
    if not callsign:
        callsign = "AEROSAT-ALPHA-01"

    print(f"\n[*] Generating cryptographic signature key for {target_path}...")
    success, msg, payload = create_dongle_token(target_path, operator_callsign=callsign)

    if success:
        print(f"[+] SUCCESS! {msg}")
        print(f"    - Device Serial: {payload.get('device_serial')}")
        print(f"    - Token ID:      {payload.get('token_id')}")
        print(f"    - Signature:     {payload.get('signature')[:16]}...")
        print("\n[*] Testing dongle detection...")
        found, verify_msg, _ = find_and_verify_dongle(allow_virtual=True)
        print(f"    - Scan result: {'[PASS]' if found else '[FAIL]'} {verify_msg}")
    else:
        print(f"[-] ERROR: {msg}")


if __name__ == "__main__":
    main()
