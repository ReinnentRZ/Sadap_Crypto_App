"""
Shared webcam preview infrastructure for the Sadap GroundStation.

The preview label keeps the native camera aspect ratio instead of forcing every
feed into a fixed 4:3 box, so faces are never stretched or cropped on screen.
"""
import cv2
import numpy as np
from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from core.auth.face_recog import get_face_engine
from core.utils.logger import get_logger

logger = get_logger("CameraFeed")


class AspectRatioLabel(QLabel):
    """QLabel that scales its pixmap to the available space without cropping."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(320, 210)
        self.setStyleSheet(
            "background-color: #0F172A; color: #64748B; font-weight: 600; "
            "border: 2px solid #CBD5E1; border-radius: 8px;"
        )
        self._pixmap = QPixmap()

    def setFrame(self, frame: np.ndarray) -> None:
        """Display a BGR OpenCV frame using its original aspect ratio."""
        if frame is None or frame.size == 0:
            return
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, channels = rgb.shape
        image = QImage(rgb.data, w, h, channels * w, QImage.Format.Format_RGB888)
        # Copy detaches the Qt buffer from the numpy array before the frame is GC'd.
        self._pixmap = QPixmap.fromImage(image.copy())
        self._rescale()

    def clearFrame(self, text: str) -> None:
        """Drop the current frame and show a placeholder message."""
        self._pixmap = QPixmap()
        self.setText(text)

    def resizeEvent(self, event) -> None:  # noqa: ANN001 - Qt signature
        super().resizeEvent(event)
        self._rescale()

    def _rescale(self) -> None:
        if self._pixmap.isNull() or self.width() <= 0 or self.height() <= 0:
            return
        scaled = self._pixmap.scaled(
            self.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        super().setPixmap(scaled)


class CameraFeedWidget(QWidget):
    """Base widget: webcam lifecycle, mirrored frames, and responsive preview."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.engine = get_face_engine()
        self.cap: cv2.VideoCapture | None = None
        self.is_camera_running = False
        self.camera_button = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_frame)
        self._init_ui()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.video_label = AspectRatioLabel()
        self.video_label.setText("Initializing Camera Feed...")
        layout.addWidget(self.video_label, stretch=1)

        self.status_label = QLabel("Camera standby")
        self.status_label.setStyleSheet("color: #64748B; font-weight: 600; font-size: 11px;")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

    def set_camera_button(self, button) -> None:
        """Register the subclass button whose caption follows the camera state."""
        self.camera_button = button

    def set_status(self, text: str, color: str = "#64748B") -> None:
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color}; font-weight: 600; font-size: 11px;")

    def start_camera(self) -> bool:
        """Open webcam 0 and start the capture loop."""
        if self.is_camera_running:
            return True

        self.cap = cv2.VideoCapture(0)
        if not self.cap.isOpened():
            self.cap = None
            self.video_label.clearFrame("Webcam tidak terdeteksi.\nPastikan kamera terhubung dan tidak dipakai aplikasi lain.")
            self.set_status("Status: Webcam tidak tersedia", "#DC2626")
            return False

        self.is_camera_running = True
        if self.camera_button is not None:
            self.camera_button.setText("Stop Camera")
        self.timer.start(30)  # ~30 FPS
        return True

    def stop_camera(self) -> None:
        """Stop the capture loop and release the webcam."""
        if not self.is_camera_running and self.cap is None:
            return
        self.timer.stop()
        if self.cap is not None:
            self.cap.release()
            self.cap = None
        self.is_camera_running = False
        if self.camera_button is not None:
            self.camera_button.setText("Start Camera")
        self.video_label.clearFrame("Camera Feed Stopped")
        self.set_status("Status: Camera stopped")

    def toggle_camera(self) -> None:
        if self.is_camera_running:
            self.stop_camera()
        else:
            self.start_camera()

    def _update_frame(self) -> None:
        if self.cap is None or not self.cap.isOpened():
            return
        ret, frame = self.cap.read()
        if not ret or frame is None:
            return

        frame = cv2.flip(frame, 1)  # Mirror view
        display_frame = self._process_frame(frame)
        self.video_label.setFrame(display_frame)

    def _process_frame(self, frame: np.ndarray) -> np.ndarray:
        """Hook for subclasses: annotate the frame before it is displayed."""
        return frame

    def closeEvent(self, event) -> None:  # noqa: ANN001 - Qt signature
        self.stop_camera()
        super().closeEvent(event)
