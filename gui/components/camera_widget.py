"""
Sadap GroundStation - Camera Face Recognition Widget
Displays a live webcam feed with YuNet face bounding box overlay and SFace
matching against every enrolled operator. Camera-only verification: static
photo verification is intentionally not supported.
"""
import cv2
import numpy as np
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QPushButton

from gui.components.camera_feed import CameraFeedWidget
from core.auth.face_recog import FaceTemplate
from core.utils.logger import get_logger

logger = get_logger("CameraWidget")


class CameraWidget(CameraFeedWidget):
    """Webcam video widget with real-time face detection and recognition."""

    # (is_match, score, message, operator_name)
    face_verified_signal = pyqtSignal(bool, float, str, str)

    def __init__(self, parent=None):
        self.templates: list[FaceTemplate] = []
        self.last_matched = False
        self.matched_operator = ""
        super().__init__(parent)
        self.templates = self.engine.load_templates()

    def _init_ui(self) -> None:
        super()._init_ui()
        btn_layout = QHBoxLayout()
        self.toggle_btn = QPushButton("Start Camera")
        self.toggle_btn.clicked.connect(self.toggle_camera)
        btn_layout.addWidget(self.toggle_btn)
        self.set_camera_button(self.toggle_btn)
        self.layout().addLayout(btn_layout)

    def start_camera(self) -> bool:
        """Reload the operator registry before starting the feed."""
        self.templates = self.engine.load_templates()
        return super().start_camera()

    def _process_frame(self, frame: np.ndarray) -> np.ndarray:
        display = frame.copy()
        found, face_info, bbox = self.engine.detect_face(frame)

        if found and face_info is not None and bbox:
            x, y, w, h = bbox

            if self.templates:
                current_embedding = self.engine.extract_embedding(frame, face_info)
                matched, score, name = self.engine.match_embedding(current_embedding, self.templates)
                self.last_matched = matched
                self.matched_operator = name if matched else ""

                color = (0, 200, 0) if matched else (0, 0, 220)  # BGR
                status = f"{name} VERIFIED ({score:.2f})" if matched else f"UNRECOGNIZED ({score:.2f})"
                self.face_verified_signal.emit(matched, score, status, self.matched_operator)
                self.set_status(f"Status: {status}", "#059669" if matched else "#DC2626")
            else:
                self.last_matched = False
                self.matched_operator = ""
                color = (0, 0, 220)
                status = "NO TEMPLATE ENROLLED"
                self.face_verified_signal.emit(False, 0.0, "No template enrolled", "")
                self.set_status("Status: Belum ada wajah terdaftar", "#DC2626")

            cv2.rectangle(display, (x, y), (x + w, y + h), color, 2)
            cv2.putText(
                display,
                status,
                (max(10, x), max(25, y - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                color,
                2
            )
        else:
            self.set_status("Status: Mencari wajah...")

        return display
