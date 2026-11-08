"""
AeroSat GroundStation - AI Face Biometric Verifier
Utilizes OpenCV YuNet (Face Detection & Alignment) and SFace (128-D Feature Embedding & Cosine Matching).
"""
from pathlib import Path
import cv2
import numpy as np

from config.settings import (
    YUNET_MODEL_PATH,
    SFACE_MODEL_PATH,
    BIOMETRIC_TEMPLATE_PATH,
    FACE_COSINE_THRESHOLD,
)
from core.utils.logger import get_logger

logger = get_logger("FaceRecog")


class FaceBiometricEngine:
    """Singleton-style Biometric Engine managing YuNet and SFace models."""

    def __init__(self):
        self._detector: cv2.FaceDetectorYN | None = None
        self._recognizer: cv2.FaceRecognizerSF | None = None
        self._load_models()

    def _load_models(self):
        """Initialize YuNet and SFace ONNX models."""
        if not Path(YUNET_MODEL_PATH).exists() or not Path(SFACE_MODEL_PATH).exists():
            raise FileNotFoundError(
                f"Face models missing in {YUNET_MODEL_PATH.parent}. Ensure ONNX files are downloaded."
            )

        # Default input size (will be updated dynamically during detection)
        self._detector = cv2.FaceDetectorYN_create(
            str(YUNET_MODEL_PATH),
            "",
            (320, 320),
            score_threshold=0.6,
            nms_threshold=0.3,
            top_k=5000
        )
        self._recognizer = cv2.FaceRecognizerSF_create(
            str(SFACE_MODEL_PATH),
            ""
        )
        logger.info("YuNet Face Detector & SFace Feature Recognizer loaded.")

    def detect_face(self, frame: np.ndarray) -> tuple[bool, np.ndarray | None, tuple[int, int, int, int] | None]:
        """
        Detect the most prominent face in a frame.
        Returns: (face_found, face_info_array, (x, y, w, h))
        """
        if frame is None or frame.size == 0:
            return False, None, None

        h, w = frame.shape[:2]
        self._detector.setInputSize((w, h))

        _, faces = self._detector.detect(frame)
        if faces is None or len(faces) == 0:
            return False, None, None

        # Select face with highest confidence score (index 14)
        best_face = faces[0]
        bbox = (
            int(best_face[0]),
            int(best_face[1]),
            int(best_face[2]),
            int(best_face[3])
        )
        return True, best_face, bbox

    def extract_embedding(self, frame: np.ndarray, face_info: np.ndarray) -> np.ndarray:
        """Align, crop, and compute 128-D facial feature embedding vector."""
        aligned_face = self._recognizer.alignCrop(frame, face_info)
        feature = self._recognizer.feature(aligned_face)
        return feature

    def compute_similarity(self, feat1: np.ndarray, feat2: np.ndarray) -> float:
        """Compute cosine similarity score between two face feature vectors."""
        score = self._recognizer.match(feat1, feat2, cv2.FaceRecognizerSF_FR_COSINE)
        return float(score)

    def is_match(self, feat1: np.ndarray, feat2: np.ndarray, threshold: float = FACE_COSINE_THRESHOLD) -> tuple[bool, float]:
        """Determine if two embeddings belong to the same person based on threshold."""
        score = self.compute_similarity(feat1, feat2)
        return (score >= threshold), score

    def save_template(
        self,
        embedding: np.ndarray,
        operator_name: str = "Authorized Operator",
        file_path: Path = BIOMETRIC_TEMPLATE_PATH
    ) -> bool:
        """Save registered face embedding to npz file."""
        try:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(
                file_path,
                embedding=embedding,
                operator_name=operator_name
            )
            logger.info(f"Biometric template registered for {operator_name} at {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save biometric template: {e}")
            return False

    def load_template(self, file_path: Path = BIOMETRIC_TEMPLATE_PATH) -> tuple[np.ndarray | None, str | None]:
        """Load registered face embedding from npz file."""
        if not file_path.exists():
            return None, None
        try:
            data = np.load(file_path, allow_pickle=True)
            embedding = data["embedding"]
            name = str(data["operator_name"])
            return embedding, name
        except Exception as e:
            logger.error(f"Failed to load biometric template: {e}")
            return None, None

    def verify_frame(
        self,
        frame: np.ndarray,
        template_embedding: np.ndarray | None = None
    ) -> tuple[bool, float, str, tuple[int, int, int, int] | None]:
        """
        Full verification pipeline for a camera frame against registered template.
        Returns: (is_verified, score, message, bbox)
        """
        if template_embedding is None:
            template_embedding, _ = self.load_template()
            if template_embedding is None:
                return False, 0.0, "No biometric template registered in system.", None

        found, face_info, bbox = self.detect_face(frame)
        if not found or face_info is None:
            return False, 0.0, "No face detected in camera view.", None

        current_embedding = self.extract_embedding(frame, face_info)
        matched, score = self.is_match(current_embedding, template_embedding)

        if matched:
            return True, score, f"Operator verified (Match Score: {score:.3f})", bbox
        else:
            return False, score, f"Identity rejected (Similarity {score:.3f} below threshold)", bbox


# Global instance
_face_engine_instance: FaceBiometricEngine | None = None


def get_face_engine() -> FaceBiometricEngine:
    """Return shared FaceBiometricEngine instance."""
    global _face_engine_instance
    if _face_engine_instance is None:
        _face_engine_instance = FaceBiometricEngine()
    return _face_engine_instance
