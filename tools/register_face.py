"""
CLI Utility: Multi-Operator Face Enrollment for Sadap GroundStation

Camera-only enrollment via webcam. Each capture stores a 128-D SFace embedding
in data/keys/face_template.npz and an AES-256-GCM encrypted PNG snapshot in
data/keys/faces/. The snapshot passphrase is supplied interactively and never
written to disk.
"""
import getpass
import re
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cv2

from config.settings import BIOMETRIC_TEMPLATE_PATH, FACE_SNAPSHOT_DIR
from core.auth.face_recog import get_face_engine
from core.crypto.file_aes import encrypt_file


def _safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_") or "operator"


def list_operators() -> None:
    names = get_face_engine().list_template_names()
    if not names:
        print("[-] Belum ada operator terdaftar.")
        return
    print(f"[*] {len(names)} operator terdaftar:")
    for index, name in enumerate(names, 1):
        print(f"    [{index}] {name}")


def delete_operator(name: str) -> bool:
    engine = get_face_engine()
    if not engine.delete_template(name):
        print(f"[-] Operator '{name}' tidak ditemukan.")
        return False
    removed = 0
    for snapshot in FACE_SNAPSHOT_DIR.glob(f"{_safe_name(name)}_*.enc"):
        snapshot.unlink(missing_ok=True)
        removed += 1
    print(f"[+] Operator '{name}' dihapus ({removed} snapshot terenkripsi dihapus).")
    return True


def prompt_passphrase() -> str:
    """Ask twice for the snapshot encryption passphrase without echoing it."""
    while True:
        first = getpass.getpass("Passphrase enkripsi snapshot: ").strip()
        if not first:
            print("[-] Passphrase tidak boleh kosong.")
            continue
        second = getpass.getpass("Ulangi passphrase: ").strip()
        if first != second:
            print("[-] Passphrase tidak cocok. Coba lagi.")
            continue
        return first


def register_from_webcam(operator_name: str, passphrase: str) -> bool:
    """Enroll a face from the live webcam and save an encrypted snapshot."""
    print("\n[*] Menghubungkan ke webcam... (SPASI = simpan, Q = batal)")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[-] Tidak dapat mengakses perangkat webcam.")
        return False

    engine = get_face_engine()
    saved = False

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame_mirrored = cv2.flip(frame, 1)
        found, face_info, bbox = engine.detect_face(frame_mirrored)
        display = frame_mirrored.copy()

        if found and bbox:
            x, y, w, h = bbox
            cv2.rectangle(display, (x, y), (x + w, y + h), (0, 200, 0), 2)
            cv2.putText(
                display,
                "WAJAH TERDETEKSI - SPASI: Simpan",
                (x, max(25, y - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 200, 0),
                2,
            )
        else:
            cv2.putText(
                display,
                "Mencari Wajah...",
                (20, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 220),
                2,
            )

        cv2.imshow("Sadap Biometric Enrollment - SPASI: Simpan | Q: Batal", display)
        key = cv2.waitKey(1) & 0xFF

        if key == ord(" ") and found and face_info is not None:
            aligned = engine.align_face(frame_mirrored, face_info)
            embedding = engine.extract_embedding(frame_mirrored, face_info)

            filename = f"{_safe_name(operator_name)}_{datetime.now():%Y%m%d_%H%M%S}.png"
            encrypted_path = FACE_SNAPSHOT_DIR / f"{filename}.enc"
            try:
                with tempfile.TemporaryDirectory(prefix="sadap_face_capture_") as tmp_dir:
                    plain_path = Path(tmp_dir) / filename
                    if not cv2.imwrite(str(plain_path), aligned):
                        raise OSError("Gagal menulis PNG sementara.")
                    ok, msg, _ = encrypt_file(plain_path, encrypted_path, passphrase)
                if not ok:
                    raise OSError(msg)
            except Exception as exc:
                print(f"[-] Snapshot gagal dienkripsi: {exc}")
                break

            if not engine.save_template(embedding, operator_name):
                encrypted_path.unlink(missing_ok=True)
                print("[-] Gagal menyimpan template biometrik.")
                break

            saved = True
            print("\n" + "=" * 65)
            print("  [+] PENDAFTARAN BIOMETRIK WAJAH BERHASIL")
            print("=" * 65)
            print(f"  - Nama Operator : {operator_name}")
            print(f"  - Sumber        : Kamera Webcam Live")
            print(f"  - Template File : {BIOMETRIC_TEMPLATE_PATH}")
            print(f"  - Snapshot      : {encrypted_path} (AES-256-GCM .enc)")
            print("=" * 65)
            break
        elif key in (ord("q"), 27):
            print("[*] Pendaftaran dibatalkan oleh pengguna.")
            break

    cap.release()
    cv2.destroyAllWindows()
    return saved


def main() -> None:
    print("=" * 65)
    print("  SADAP GROUNDSTATION — BIOMETRIC FACE ENROLLMENT UTILITY")
    print("=" * 65)
    print("Mendaftarkan beberapa operator wajah melalui webcam.")
    print("Template: data/keys/face_template.npz")
    print("Snapshot terenkripsi: data/keys/faces/*.enc\n")

    while True:
        print("\nPilih aksi:")
        print("  [1] Daftarkan / perbarui wajah (kamera)")
        print("  [2] Lihat daftar operator")
        print("  [3] Hapus operator")
        print("  [4] Keluar")
        choice = input("\nPilihan (1/2/3/4) [Default: 1]: ").strip() or "1"

        if choice == "1":
            name = input("Nama/Callsign Operator [Sadap Commander]: ").strip() or "Sadap Commander"
            register_from_webcam(name, prompt_passphrase())
        elif choice == "2":
            list_operators()
        elif choice == "3":
            name = input("Nama operator yang akan dihapus: ").strip()
            if name:
                delete_operator(name)
        elif choice == "4":
            print("[*] Selesai.")
            break
        else:
            print("[-] Pilihan tidak dikenali.")


if __name__ == "__main__":
    main()
