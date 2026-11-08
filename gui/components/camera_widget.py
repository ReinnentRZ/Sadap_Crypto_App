"""
AeroSat GroundStation - Camera Face Recognition Widget
Displays live webcam feed with YuNet face bounding box overlay and SFace matching indicator.
Provides graceful simulation fallback if no physical webcam is detected.
"""
from pathlib import Path
import cv2
import numpy as np
from PyQt6.QtCore import QTimer, pyqtSignal, Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel,
    QPushButton,
    QHBoxLayout,
    QFileDialog,
)

from core.auth.face_recog import get_face_engine
from core.utils.logger import get_logger

logger = get_logger("CameraWidget")


class CameraWidget(QWidget):
    """Webcam video widget with real-time face detection and recognition."""

    face_verified_signal = pyqtSignal(bool, float, str)  # (is_match, score, message)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.engine = get_face_engine()
        self.cap: cv2.VideoCapture | None = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_frame)

        self.template_embedding, self.operator_name = self.engine.load_template()
        self.is_camera_running = False
        self.last_matched = False

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Video Frame Display
        self.video_label = QLabel()
        self.video_label.setFixedSize(360, 270)
        self.video_label.setStyleSheet(
            "background-color: #0F172A; border: 2px solid #CBD5E1; border-radius: 8px;"
        )
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setText("Initializing Camera Feed...")
        self.video_label.setStyleSheet("color: #64748B; font-weight: 600;")
        layout.addWidget(self.video_label, alignment=Qt.AlignmentFlag.AlignCenter)

        # Status Label
        self.status_label = QLabel("Camera standby")
        self.status_label.setStyleSheet("color: #64748B; font-weight: 600; font-size: 11px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        # Fallback controls (load photo if no camera)
        btn_layout = QHBoxLayout()
        self.toggle_btn = QPushButton("Start Camera")
        self.toggle_btn.clicked.connect(self.toggle_camera)
        btn_layout.addWidget(self.toggle_btn)

        self.load_photo_btn = QPushButton("Verify via Photo...")
        self.load_photo_btn.setObjectName("secondaryBtn")
        self.load_photo_btn.clicked.connect(self._verify_via_photo)
        btn_layout.addWidget(self.load_photo_btn)

        layout.addLayout(btn_layout)

    def start_camera(self):
        """Open webcam and start capture loop."""
        # Reload template in case it was enrolled while app is running
        self.template_embedding, self.operator_name = self.engine.load_template()

        if not self.is_camera_running:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                self.video_label.setText("Physical camera not accessible.\nUse 'Verify via Photo' below.")
                self.status_label.setText("Status: Webcam unavailable")
                return

            self.is_camera_running = True
            self.toggle_btn.setText("Stop Camera")
            self.timer.start(30)  # ~30 FPS

    def stop_camera(self):
        """Stop capture loop and release webcam."""
        if self.is_camera_running:
            self.timer.stop()
            if self.cap:
                self.cap.release()
                self.cap = None
            self.is_camera_running = False
            self.toggle_btn.setText("Start Camera")
            self.video_label.setText("Camera Feed Stopped")
            self.status_label.setText("Status: Camera stopped")

    def toggle_camera(self):
        """Toggle camera state."""
        if self.is_camera_running:
            self.stop_camera()
        else:
            self.start_camera()

    def _update_frame(self):
        """Read frame from webcam, perform face recognition, and render to QLabel."""
        if not self.cap or not self.cap.isOpened():
            return

        ret, frame = self.cap.read()
        if not ret:
            return

        frame = cv2.flip(frame, 1)  # Mirror view
        found, face_info, bbox = self.engine.detect_face(frame)

        if found and face_info is not None and bbox:
            x, y, w, h = bbox

            if self.template_embedding is not None:
                current_emb = self.engine.extract_embedding(frame, face_info)
                matched, score = self.engine.is_match(current_emb, self.template_embedding)
                self.last_matched = matched

                color = (0, 200, 0) if matched else (0, 0, 220)  # Green or Red (BGR)
                status_text = f"OPERATOR VERIFIED ({score:.2f})" if matched else f"UNRECOGNIZED ({score:.2f})"
                self.face_verified_signal.emit(matched, score, status_text)
                self.status_label.setText(f"Status: {status_text}")
            else:
                self.last_matched = False
                color = (0, 0, 220)
                status_text = "NO TEMPLATE ENROLLED"
                self.face_verified_signal.emit(False, 0.0, "No template enrolled")
                self.status_label.setText("Status: No template enrolled (Run tools/register_face.py)")

            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)
            cv2.putText(
                frame,
                status_text,
                (max(10, x), max(25, y - 10)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.55,
                color,
                2
            )
        else:
            self.status_label.setText("Status: Searching for face...")

        # Convert frame to QPixmap and display
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888)
        self.video_label.setPixmap(
            QPixmap.fromImage(q_img).scaled(
                self.video_label.width(),
                self.video_label.height(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
        )

    def _verify_via_photo(self):
        """Fallback verification from static portrait photo file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Operator Portrait Photo",
            "",
            "Images (*.png *.jpg *.jpeg *.bmp)"
        )
        if not file_path:
            return

        img = cv2.imread(file_path)
        if img is None:
            self.status_label.setText("Status: Error reading photo")
            return

        found, face_info, bbox = self.engine.detect_face(img)
        if not found or face_info is None:
            self.status_label.setText("Status: No face found in photo")
            self.face_verified_signal.emit(False, 0.0, "No face found in photo")
            return

        # Reload template in case it was enrolled while app is running
        self.template_embedding, self.operator_name = self.engine.load_template()

        if self.template_embedding is not None:
            emb = self.engine.extract_embedding(img, face_info)
            matched, score = self.engine.is_match(emb, self.template_embedding)
            self.last_matched = matched
            msg = f"Photo Verified (Score {score:.2f})" if matched else f"Photo Rejected ({score:.2f})"
            self.status_label.setText(f"Status: {msg}")
            self.face_verified_signal.emit(matched, score, msg)
        else:
            self.last_matched = False
            self.status_label.setText("Status: No face template enrolled. Please run tools/register_face.py.")
            self.face_verified_signal.emit(False, 0.0, "No face template enrolled")

    def closeEvent(self, event):
        self.stop_camera()
        super().closeEvent(event)
