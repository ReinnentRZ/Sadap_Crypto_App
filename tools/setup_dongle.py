"""
CLI Utility: Inject Hardware USB Dongle Authorization Key for Sadap GroundStation
Scans connected drives, identifies removable USB flash drives, and injects
cryptographically signed token files (sadap.sig) bound to the physical Volume Serial Number.
"""
import sys
from pathlib import Path
import psutil

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.auth.usb_dongle import (
    create_dongle_token,
    find_and_verify_dongle,
    is_physical_usb_drive,
    get_volume_serial_number,
)
from config.settings import DATA_DIR


def main():
    print("=" * 65)
    print("  SADAP GROUNDSTATION — USB HARDWARE DONGLE INJECTION TOOL")
    print("=" * 65)
    print("Menghubungkan token otorisasi kriptografi ke flashdisk USB fisik.")
    print("Flashdisk harus tercolok ke port USB komputer.\n")

    # 1. Scan and classify connected storage drives
    partitions = psutil.disk_partitions(all=False)
    drive_list = []
    print("[+] Memindai drive penyimpanan yang terpasang:")

    usb_found = 0
    for i, p in enumerate(partitions, start=1):
        drive_list.append(p.mountpoint)
        is_usb, desc = is_physical_usb_drive(p.mountpoint)
        serial = get_volume_serial_number(p.mountpoint)
        badge = " [REMOVABLE USB FLASHDISK]" if is_usb else f" [{desc}]"
        if is_usb:
            usb_found += 1
        print(f"  [{i}] Drive: {p.mountpoint:<6} | Serial: {serial:<12} | FS: {p.fstype:<6}{badge}")

    if usb_found == 0:
        print("\n[!] PERINGATAN: Tidak ada USB Flashdisk fisik yang terdeteksi saat ini.")
        print("    Silakan colokkan USB flashdisk Anda ke port USB sekarang, lalu jalankan ulang tool ini.")
        print("    Atau Anda dapat memilih drive secara manual di bawah ini.")

    print("\nOpsi Target:")
    print("  - Masukkan nomor pilihan (1-{0})".format(len(drive_list)))
    print("  - Atau ketik langsung huruf drive USB (contoh: E:\\ atau F:\\)")

    choice = input("\nPilih Drive Target: ").strip()
    if not choice:
        print("[-] Dibatalkan. Tidak ada target yang dipilih.")
        return

    # Determine target path
    target_path = None
    if choice.isdigit():
        idx = int(choice)
        if 1 <= idx <= len(drive_list):
            target_path = drive_list[idx - 1]
        else:
            print("[-] Nomor pilihan tidak valid.")
            return
    else:
        # User entered drive letter like "E" or "E:" or "E:\"
        target_path = choice.upper()
        if not target_path.endswith("\\"):
            target_path += "\\"
        if not target_path.endswith(":\\") and len(target_path) == 2 and target_path[1] == "\\":
            target_path = target_path[0] + ":\\"

    print(f"\n[*] Target terpilih: {target_path}")
    serial = get_volume_serial_number(target_path)
    is_usb, desc = is_physical_usb_drive(target_path)
    print(f"    - Hardware Serial: {serial}")
    print(f"    - Drive Class:     {desc}")

    if not is_usb:
        confirm = input("\n[!] Drive ini bukan USB Removable Flashdisk. Tetap lanjutkan? (y/N): ").strip().lower()
        if confirm != "y":
            print("[-] Dibatalkan.")
            return

    callsign = input("\nMasukkan Operator Callsign [SADAP-ALPHA-OPERATOR]: ").strip()
    if not callsign:
        callsign = "SADAP-ALPHA-OPERATOR"

    print(f"\n[*] Meng-generate token otorisasi kriptografi HMAC-SHA256 untuk {target_path}...")
    success, msg, payload = create_dongle_token(target_path, operator_callsign=callsign)

    if success:
        print("\n" + "=" * 65)
        print("  ✓ INJEKSI TOKEN BERHASIL!")
        print("=" * 65)
        print(f"  - Lokasi Berkas : {target_path}sadap.sig")
        print(f"  - Device Serial : {payload.get('device_serial')}")
        print(f"  - Operator      : {payload.get('operator_callsign')}")
        print(f"  - Token ID      : {payload.get('token_id')}")
        print(f"  - HMAC Signature: {payload.get('signature')[:24]}...")
        print("=" * 65)

        print("\n[*] Menjalankan uji verifikasi pendeteksian dongle...")
        found, verify_msg, _ = find_and_verify_dongle(allow_virtual=False)
        if found:
            print(f"  ✓ HASIL UJI: [PASS] {verify_msg}")
            print("\n>> Flashdisk siap digunakan sebagai Kunci Keras Faktor 1 pada Sadap GroundStation! <<")
        else:
            print(f"  ! HASIL UJI: {verify_msg}")
    else:
        print(f"\n[-] GAGAL: {msg}")


if __name__ == "__main__":
    main()
