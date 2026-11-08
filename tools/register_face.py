"""
CLI Utility: Register Biometric Face Template for Sadap GroundStation
Allows enrolling an authorized operator via live webcam capture or via a portrait photo.
Extracts 128-dimensional Deep Learning embeddings via YuNet & SFace, saving to data/keys/face_template.npz.
"""
import sys
from pathlib import Path
import cv2

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.auth.face_recog import get_face_engine
from config.settings import BIOMETRIC_TEMPLATE_PATH


def register_from_image(image_path: str, operator_name: str) -> bool:
    """Enroll face from a photo file."""
    p = Path(image_path)
    if not p.exists():
        print(f"[-] Berkas foto tidak ditemukan: {image_path}")
        return False

    img = cv2.imread(str(p))
    if img is None:
        print("[-] Gagal mendecode gambar foto.")
        return False

    engine = get_face_engine()
    found, face_info, bbox = engine.detect_face(img)
    if not found or face_info is None:
        print("[-] Tidak ada wajah manusia yang terdeteksi di dalam foto.")
        return False

    embedding = engine.extract_embedding(img, face_info)
    ok = engine.save_template(embedding, operator_name=operator_name, file_path=BIOMETRIC_TEMPLATE_PATH)
    if ok:
        print("\n" + "=" * 65)
        print("  ✓ PENDAFTARAN BIOMETRIK WAJAH BERHASIL!")
        print("=" * 65)
        print(f"  - Nama Operator : {operator_name}")
        print(f"  - Sumber Foto   : {image_path}")
        print(f"  - Template File : {BIOMETRIC_TEMPLATE_PATH}")
        print("  - Vektor Fitur  : 128-D Normalized SFace Embedding")
        print("=" * 65)
    return ok


def register_from_webcam(operator_name: str) -> bool:
    """Enroll face using live webcam capture."""
    print("\n[*] Menghubungkan ke webcam... (Tekan SPASI untuk ambil foto, Q untuk batal)")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[-] Tidak dapat mengakses perangkat webcam.")
        print("    Gunakan opsi [2] untuk mendaftarkan wajah dari berkas foto potret.")
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
            cv2.rectangle(display, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(
                display,
                "WAJAH TERDETEKSI - Tekan SPASI untuk Menyimpan",
                (x, max(25, y - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2,
            )
        else:
            cv2.putText(
                display,
                "Mencari Wajah...",
                (20, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2,
            )

        cv2.imshow("Sadap Biometric Enrollment - Tekan SPASI: Simpan | Q: Batal", display)
        key = cv2.waitKey(1) & 0xFF

        if key == ord(" ") and found and face_info is not None:
            embedding = engine.extract_embedding(frame_mirrored, face_info)
            saved = engine.save_template(embedding, operator_name=operator_name, file_path=BIOMETRIC_TEMPLATE_PATH)
            if saved:
                print("\n" + "=" * 65)
                print("  ✓ PENDAFTARAN BIOMETRIK WAJAH BERHASIL!")
                print("=" * 65)
                print(f"  - Nama Operator : {operator_name}")
                print(f"  - Sumber        : Kamera Webcam Live")
                print(f"  - Template File : {BIOMETRIC_TEMPLATE_PATH}")
                print("=" * 65)
            break
        elif key == ord("q") or key == 27:
            print("[*] Pendaftaran dibatalkan oleh pengguna.")
            break

    cap.release()
    cv2.destroyAllWindows()
    return saved


def main():
    print("=" * 65)
    print("  SADAP GROUNDSTATION — BIOMETRIC FACE ENROLLMENT UTILITY")
    print("=" * 65)
    print("Mendaftarkan wajah operator ke dalam sistem pengenalan wajah biometrik AI.")
    print("Template disimpan dalam format vektor terkompresi di data/keys/face_template.npz.\n")

    name = input("Masukkan Nama/Callsign Operator [Sadap Commander]: ").strip()
    if not name:
        name = "Sadap Commander"

    print("\nPilih metode pendaftaran:")
    print("  [1] Ambil Langsung via Kamera Webcam")
    print("  [2] Ambil dari Berkas Foto Potret (PNG/JPG)")
    choice = input("\nPilihan (1/2) [Default: 1]: ").strip()

    if choice == "2":
        path = input("Masukkan path lengkap berkas foto potret: ").strip().strip('"')
        register_from_image(path, name)
    else:
        register_from_webcam(name)


if __name__ == "__main__":
    main()
