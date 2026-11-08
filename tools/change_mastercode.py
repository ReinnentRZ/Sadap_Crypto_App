"""
CLI Utility: Change or Reset Master Clearance Passcode for Sadap GroundStation
Allows updating the PBKDF2-HMAC-SHA256 master passcode hash stored in data/keys/master_credential.hash.
"""
import sys
import getpass
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config.settings import DATA_DIR
from core.auth.hasher import hash_password, verify_password

CREDENTIAL_FILE = DATA_DIR / "keys" / "master_credential.hash"
DEFAULT_MASTER_PASSCODE = "Sadap-Commander-2026!"


def get_current_hash() -> str:
    """Read current master passcode hash from file or initialize default."""
    CREDENTIAL_FILE.parent.mkdir(parents=True, exist_ok=True)
    if CREDENTIAL_FILE.exists():
        try:
            return CREDENTIAL_FILE.read_text(encoding="utf-8").strip()
        except Exception:
            pass
    h = hash_password(DEFAULT_MASTER_PASSCODE)
    CREDENTIAL_FILE.write_text(h, encoding="utf-8")
    return h


def set_master_passcode(new_passcode: str) -> bool:
    """Hash and save new master passcode."""
    try:
        new_hash = hash_password(new_passcode)
        CREDENTIAL_FILE.write_text(new_hash, encoding="utf-8")
        return True
    except Exception as e:
        print(f"[-] Gagal menyimpan passcode baru: {e}")
        return False


def main():
    print("=" * 65)
    print("  SADAP GROUNDSTATION — MASTER PASSCODE MANAGEMENT UTILITY")
    print("=" * 65)
    print("Mengganti Master Clearance Passcode (Faktor 3 Otorisasi Gatekeeper)")
    print(f"Lokasi Hash: {CREDENTIAL_FILE}\n")

    current_hash = get_current_hash()
    is_reset_mode = "--reset" in sys.argv or "--force" in sys.argv

    if not is_reset_mode:
        # Step 1: Verify current passcode
        try:
            old_code = getpass.getpass("Masukkan Master Passcode saat ini: ")
        except Exception:
            old_code = input("Masukkan Master Passcode saat ini: ")

        if not verify_password(old_code, current_hash):
            print("\n[-] Akses Ditolak: Master Passcode lama tidak cocok!")
            print("    Jika Anda lupa passcode lama, jalankan: python tools/change_mastercode.py --reset")
            return
        print("[+] Master Passcode lama diverifikasi valid.\n")
    else:
        print("[!] MODE RESET AKTIF: Melewati verifikasi passcode lama.")

    # Step 2: Input new passcode
    while True:
        try:
            new_code = getpass.getpass("Masukkan Master Passcode baru: ")
        except Exception:
            new_code = input("Masukkan Master Passcode baru: ")

        new_code = new_code.strip()
        if len(new_code) < 8:
            print("[-] Passcode baru terlalu pendek! Minimal 8 karakter demi keamanan.")
            continue

        try:
            confirm_code = getpass.getpass("Konfirmasi Master Passcode baru: ")
        except Exception:
            confirm_code = input("Konfirmasi Master Passcode baru: ")

        if new_code != confirm_code:
            print("[-] Konfirmasi passcode tidak cocok! Silakan coba lagi.\n")
            continue
        break

    # Step 3: Hash with PBKDF2-HMAC-SHA256 (200k iterations) and save
    print("\n[*] Menghitung derivasi PBKDF2-HMAC-SHA256 dengan salt kriptografis baru...")
    if set_master_passcode(new_code):
        print("=" * 65)
        print("  ✓ MASTER PASSCODE BERHASIL DIPERBARUI!")
        print("=" * 65)
        print(f"  - File Disimpan : {CREDENTIAL_FILE}")
        print("  - Algoritma     : PBKDF2-HMAC-SHA256 (200,000 Iterasi)")
        print("  - Status        : Aktif segera untuk otorisasi berikutnya.")
        print("=" * 65)


if __name__ == "__main__":
    main()
