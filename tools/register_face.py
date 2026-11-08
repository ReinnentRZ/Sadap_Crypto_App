"""
CLI Utility: Register Biometric Face Template for AeroSat GroundStation
Allows enrolling an operator via live webcam or via a portrait photo.
"""
import sys
from pathlib import Path
import cv2

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.auth.face_recog import get_face_engine


def register_from_image(image_path: str, operator_name: str) -> bool:
    """Enroll face from a photo file."""
    p = Path(image_path)
    if not p.exists():
        print(f"[-] File not found: {image_path}")
        return False

    img = cv2.imread(str(p))
    if img is None:
        print("[-] Could not decode image.")
        return False

    engine = get_face_engine()
    found, face_info, bbox = engine.detect_face(img)
    if not found or face_info is None:
        print("[-] No face detected in the image.")
        return False

    embedding = engine.extract_embedding(img, face_info)
    ok = engine.save_template(embedding, operator_name=operator_name)
    if ok:
        print(f"[+] Successfully enrolled '{operator_name}' from {image_path}")
    return ok


def register_from_webcam(operator_name: str) -> bool:
    """Enroll face using live webcam capture."""
    print("[*] Opening camera... (Press SPACE to capture, Q to quit)")
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("[-] Could not open webcam.")
        return False

    engine = get_face_engine()
    saved = False

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        found, face_info, bbox = engine.detect_face(frame)
        display = frame.copy()

        if found and bbox:
            x, y, w, h = bbox
            cv2.rectangle(display, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(
                display,
                "Face Detected - Press SPACE to Save",
                (x, max(20, y - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2
            )
        else:
            cv2.putText(
                display,
                "No Face Detected",
                (20, 30),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 0, 255),
                2
            )

        cv2.imshow("AeroSat Biometric Enrollment - Press SPACE to capture, Q to cancel", display)
        key = cv2.waitKey(1) & 0xFF

        if key == ord(' ') and found and face_info is not None:
            embedding = engine.extract_embedding(frame, face_info)
            saved = engine.save_template(embedding, operator_name=operator_name)
            if saved:
                print(f"[+] Successfully enrolled '{operator_name}' from webcam!")
            break
        elif key == ord('q') or key == 27:
            print("[*] Enrollment cancelled by user.")
            break

    cap.release()
    cv2.destroyAllWindows()
    return saved


def main():
    print("=" * 60)
    print("  AEROSAT GROUNDSTATION - BIOMETRIC ENROLLMENT UTILITY")
    print("=" * 60)

    name = input("Enter Operator Name [AeroSat Commander]: ").strip()
    if not name:
        name = "AeroSat Commander"

    print("\nSelect enrollment method:")
    print("  [1] Live Webcam Capture")
    print("  [2] Load from Photo File (PNG/JPG)")
    choice = input("Choice (1/2) [Default: 1]: ").strip()

    if choice == "2":
        path = input("Enter path to photo: ").strip().strip('"')
        register_from_image(path, name)
    else:
        register_from_webcam(name)


if __name__ == "__main__":
    main()
