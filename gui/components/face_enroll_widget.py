"""Webcam widget used by the secret dashboard's face enrollment tab."""
import cv2
import numpy as np
from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QPushButton

from gui.components.camera_feed import CameraFeedWidget


class FaceEnrollWidget(CameraFeedWidget):
    """Live preview with face detection overlay and a capture helper."""

    face_detected_signal = pyqtSignal(bool)

    def __init__(self, parent=None):
        self._last_frame: np.ndarray | None = None
        self._last_face_info: np.ndarray | None = None
        self._detected = False
        super().__init__(parent)

    def _init_ui(self) -> None:
        super()._init_ui()
        btn_layout = QHBoxLayout()
        self.toggle_btn = QPushButton("Start Camera")
        self.toggle_btn.clicked.connect(self.toggle_camera)
        btn_layout.addWidget(self.toggle_btn)
        self.set_camera_button(self.toggle_btn)
        self.layout().addLayout(btn_layout)

    def _process_frame(self, frame: np.ndarray) -> np.ndarray:
        display = frame.copy()
        found, face_info, bbox = self.engine.detect_face(frame)
        self._last_frame = frame
        self._last_face_info = face_info if found else None

        if found != self._detected:
            self._detected = found
            self.face_detected_signal.emit(found)

        if found and bbox:
            x, y, w, h = bbox
            cv2.rectangle(display, (x, y), (x + w, y + h), (0, 200, 0), 2)
            cv2.putText(
                display,
                "WAJAH TERDETEKSI",
                (max(10, x), max(25, y - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                (0, 200, 0),
                2,
            )
            self.set_status("Status: Wajah terdeteksi — siap di-capture", "#059669")
        else:
            self.set_status("Status: Mencari wajah...")

        return display

    def capture_face(self) -> tuple[np.ndarray, np.ndarray, tuple[int, int, int, int]] | None:
        """Return (aligned_face, embedding, bbox) for the currently detected face."""
        if self._last_frame is None or self._last_face_info is None:
            return None
        aligned = self.engine.align_face(self._last_frame, self._last_face_info)
        embedding = self.engine.extract_embedding(self._last_frame, self._last_face_info)
        info = self._last_face_info
        bbox = (int(info[0]), int(info[1]), int(info[2]), int(info[3]))
        return aligned, embedding, bbox

    def stop_camera(self) -> None:
        self._last_frame = None
        self._last_face_info = None
        self._detected = False
        super().stop_camera()
