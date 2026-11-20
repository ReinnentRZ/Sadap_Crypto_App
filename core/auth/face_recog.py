"""
Sadap GroundStation - AI Face Biometric Verifier
Utilizes OpenCV YuNet (Face Detection & Alignment) and SFace (128-D Feature Embedding & Cosine Matching).

The template store supports multiple enrolled operators. The original single-face
npz layout (``embedding`` + ``operator_name``) is read transparently and upgraded
on the next write.
"""
import os
import tempfile
from dataclasses import dataclass
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

TEMPLATE_SCHEMA_VERSION = 2


@dataclass
class FaceTemplate:
    """One enrolled operator's SFace embedding."""

    name: str
    embedding: np.ndarray


@dataclass
class FaceMatchResult:
    """Best match found for a frame across every enrolled template."""

    matched: bool
    score: float
    message: str
    bbox: tuple[int, int, int, int] | None
    operator_name: str


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

    def align_face(self, frame: np.ndarray, face_info: np.ndarray) -> np.ndarray:
        """Return the geometrically aligned face crop used by SFace."""
        return self._recognizer.alignCrop(frame, face_info)

    def extract_embedding(self, frame: np.ndarray, face_info: np.ndarray) -> np.ndarray:
        """Align, crop, and compute 128-D facial feature embedding vector."""
        aligned_face = self.align_face(frame, face_info)
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

    # ------------------------------------------------------------------
    # Multi-operator template store
    # ------------------------------------------------------------------
    def load_templates(self, file_path: Path = BIOMETRIC_TEMPLATE_PATH) -> list[FaceTemplate]:
        """Load every enrolled operator, including legacy single-face templates."""
        path = Path(file_path)
        if not path.exists():
            return []

        try:
            data = np.load(path, allow_pickle=True)

            if "embeddings" in data:
                names = data["operator_names"]
                if np.ndim(names) == 0:
                    names = [str(names)]
                else:
                    names = [str(name) for name in names.tolist()]

                templates = []
                for index, embedding in enumerate(data["embeddings"]):
                    name = names[index] if index < len(names) else f"OPERATOR-{index + 1}"
                    templates.append(FaceTemplate(name, np.asarray(embedding, dtype=np.float32).reshape(1, 128)))
                return templates

            # Legacy v1 file: one embedding + one operator name.
            if "embedding" in data:
                name = str(data["operator_name"]) if "operator_name" in data else "Authorized Operator"
                if name in ("None", ""):
                    name = "Authorized Operator"
                embedding = np.asarray(data["embedding"], dtype=np.float32).reshape(1, 128)
                return [FaceTemplate(name, embedding)]
        except Exception as exc:
            logger.error(f"Failed to load biometric templates: {exc}")
        return []

    def save_templates(self, templates: list[FaceTemplate], file_path: Path = BIOMETRIC_TEMPLATE_PATH) -> bool:
        """Atomically write the whole operator registry."""
        path = Path(file_path)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            embeddings = np.vstack([np.asarray(t.embedding, dtype=np.float32).reshape(1, 128) for t in templates])
            names = np.asarray([t.name for t in templates], dtype=str)

            # Write then replace so an interrupted write cannot corrupt the store.
            fd, temp_name = tempfile.mkstemp(prefix=f"{path.stem}_", suffix=".npz", dir=str(path.parent))
            os.close(fd)
            temp_path = Path(temp_name)
            try:
                np.savez_compressed(
                    temp_path,
                    schema_version=TEMPLATE_SCHEMA_VERSION,
                    embeddings=embeddings,
                    operator_names=names,
                )
                os.replace(temp_path, path)
            finally:
                temp_path.unlink(missing_ok=True)

            logger.info(f"Biometric template store updated with {len(templates)} operator(s) at {path}")
            return True
        except Exception as exc:
            logger.error(f"Failed to save biometric templates: {exc}")
            return False

    def save_template(
        self,
        embedding: np.ndarray,
        operator_name: str = "Authorized Operator",
        file_path: Path = BIOMETRIC_TEMPLATE_PATH
    ) -> bool:
        """Register (or re-register) one operator without touching the others."""
        name = operator_name.strip() or "Authorized Operator"
        templates = self.load_templates(file_path)
        replaced = False
        for template in templates:
            if template.name == name:
                template.embedding = np.asarray(embedding, dtype=np.float32).reshape(1, 128)
                replaced = True
                break
        if not replaced:
            templates.append(FaceTemplate(name, np.asarray(embedding, dtype=np.float32).reshape(1, 128)))

        ok = self.save_templates(templates, file_path)
        if ok:
            action = "updated" if replaced else "registered"
            logger.info(f"Biometric template {action} for {name} at {file_path}")
        return ok

    def list_template_names(self, file_path: Path = BIOMETRIC_TEMPLATE_PATH) -> list[str]:
        """Return callsigns of all enrolled operators."""
        return [template.name for template in self.load_templates(file_path)]

    def delete_template(self, operator_name: str, file_path: Path = BIOMETRIC_TEMPLATE_PATH) -> bool:
        """Remove one operator from the registry. Returns True when something was removed."""
        templates = self.load_templates(file_path)
        remaining = [t for t in templates if t.name != operator_name]
        if len(remaining) == len(templates):
            return False
        if not remaining:
            # Keep an empty but valid v2 store instead of deleting the file.
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            np.savez_compressed(
                path,
                schema_version=TEMPLATE_SCHEMA_VERSION,
                embeddings=np.empty((0, 128), dtype=np.float32),
                operator_names=np.asarray([], dtype=str),
            )
            return True
        return self.save_templates(remaining, file_path)

    def load_template(self, file_path: Path = BIOMETRIC_TEMPLATE_PATH) -> tuple[np.ndarray | None, str | None]:
        """Backward-compatible accessor returning the first enrolled operator."""
        templates = self.load_templates(file_path)
        if not templates:
            return None, None
        return templates[0].embedding, templates[0].name

    def match_embedding(
        self, embedding: np.ndarray, templates: list[FaceTemplate] | None = None
    ) -> tuple[bool, float, str]:
        """Compare an embedding against every template and return the best match."""
        if templates is None:
            templates = self.load_templates()
        if not templates:
            return False, 0.0, ""

        best_name = ""
        best_score = -1.0
        for template in templates:
            score = self.compute_similarity(embedding, template.embedding)
            if score > best_score:
                best_score = score
                best_name = template.name

        return best_score >= FACE_COSINE_THRESHOLD, best_score, best_name

    def verify_frame(
        self,
        frame: np.ndarray,
        templates: list[FaceTemplate] | None = None
    ) -> FaceMatchResult:
        """
        Full verification pipeline for a camera frame against all registered templates.
        Returns a FaceMatchResult with the matched operator's callsign.
        """
        if templates is None:
            templates = self.load_templates()
        if not templates:
            return FaceMatchResult(False, 0.0, "No biometric template registered in system.", None, "")

        found, face_info, bbox = self.detect_face(frame)
        if not found or face_info is None:
            return FaceMatchResult(False, 0.0, "No face detected in camera view.", None, "")

        current_embedding = self.extract_embedding(frame, face_info)
        matched, score, name = self.match_embedding(current_embedding, templates)

        if matched:
            return FaceMatchResult(
                True, score, f"Operator {name} verified (Match Score: {score:.3f})", bbox, name
            )
        return FaceMatchResult(
            False, score, f"Identity rejected (Similarity {score:.3f} below threshold)", bbox, ""
        )


# Global instance
_face_engine_instance: FaceBiometricEngine | None = None


def get_face_engine() -> FaceBiometricEngine:
    """Return shared FaceBiometricEngine instance."""
    global _face_engine_instance
    if _face_engine_instance is None:
        _face_engine_instance = FaceBiometricEngine()
    return _face_engine_instance
