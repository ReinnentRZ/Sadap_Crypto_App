"""
Secret dashboard tab: enroll, manage, and inspect encrypted face snapshots.

Enrollment is deliberately available only inside the vault. Every snapshot is
encrypted with an operator-supplied passphrase via the existing AES-256-GCM
file engine; no raw face image is ever left on disk.
"""
import re
import tempfile
from datetime import datetime
from pathlib import Path

import cv2
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from config.settings import FACE_SNAPSHOT_DIR
from core.auth.face_recog import get_face_engine
from core.crypto.file_aes import decrypt_file, encrypt_file
from core.database.db_manager import get_vault_db
from core.utils.logger import get_logger
from gui.components.face_enroll_widget import FaceEnrollWidget
from gui.components.password_line_edit import PasswordLineEdit

logger = get_logger("FaceEnrollment")


def _safe_name(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9_-]+", "_", name).strip("_") or "operator"


class SnapshotPreviewDialog(QDialog):
    """Shows a temporarily decrypted snapshot; the caller removes the temp dir."""

    def __init__(self, operator_name: str, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Snapshot Wajah — {operator_name}")
        self.setMinimumSize(520, 460)
        layout = QVBoxLayout(self)

        image_label = QLabel()
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_label.setPixmap(
            pixmap.scaled(
                500,
                380,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        layout.addWidget(image_label)

        note = QLabel("Didekripsi sementara untuk ditampilkan. File asli tetap terenkripsi (.enc).")
        note.setStyleSheet("color: #64748B; font-size: 11px;")
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(note)

        close_btn = QPushButton("Tutup")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)


class TabFaceEnrollment(QWidget):
    """Multi-operator face registry with encrypted snapshot storage."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.engine = get_face_engine()
        self._init_ui()
        self._refresh_list()

    def _init_ui(self) -> None:
        main = QVBoxLayout(self)
        main.setContentsMargins(16, 14, 16, 14)
        main.setSpacing(12)

        # --- Capture ---
        capture_group = QGroupBox("1. Pendaftaran Wajah (Kamera saja)")
        capture_layout = QVBoxLayout(capture_group)

        form = QFormLayout()
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nama / callsign operator, mis. SADAP-ALPHA")
        form.addRow("Nama Operator:", self.name_input)

        self.passphrase_input = PasswordLineEdit(
            placeholder="Passphrase enkripsi snapshot (wajib, tidak disimpan)"
        )
        form.addRow("Passphrase Snapshot:", self.passphrase_input)
        capture_layout.addLayout(form)

        self.camera = FaceEnrollWidget(self)
        self.camera.setMinimumHeight(240)
        capture_layout.addWidget(self.camera, stretch=1)

        capture_btn = QPushButton("📸 Capture & Daftar Wajah")
        capture_btn.clicked.connect(self._capture)
        capture_layout.addWidget(capture_btn)
        main.addWidget(capture_group, stretch=3)

        # --- Registry ---
        registry_group = QGroupBox("2. Operator Terdaftar & Snapshot Terenkripsi")
        registry_layout = QVBoxLayout(registry_group)

        self.operator_list = QListWidget()
        registry_layout.addWidget(self.operator_list)

        actions = QHBoxLayout()
        refresh_btn = QPushButton("🔄 Refresh Daftar")
        refresh_btn.setObjectName("secondaryBtn")
        refresh_btn.clicked.connect(self._refresh_list)
        actions.addWidget(refresh_btn)

        view_btn = QPushButton("👁️ Lihat Snapshot")
        view_btn.setObjectName("secondaryBtn")
        view_btn.clicked.connect(self._view_snapshot)
        actions.addWidget(view_btn)

        delete_btn = QPushButton("🗑️ Hapus Operator")
        delete_btn.setObjectName("secondaryBtn")
        delete_btn.clicked.connect(self._delete_operator)
        actions.addWidget(delete_btn)
        registry_layout.addLayout(actions)
        main.addWidget(registry_group, stretch=2)

        self.status_label = QLabel(
            "Beberapa wajah dapat didaftarkan. Wajah mana pun yang cocok dapat membuka brankas."
        )
        self.status_label.setStyleSheet("color: #475569; font-size: 11px;")
        main.addWidget(self.status_label)

    def _audit(self, event_type: str, details: str) -> None:
        try:
            get_vault_db().add_audit_log(
                event_type=event_type,
                details=details,
                operator="FACE-REGISTRAR",
            )
        except Exception as exc:
            logger.debug(f"Face enrollment audit log skipped: {exc}")

    def _status(self, text: str, color: str = "#475569") -> None:
        self.status_label.setText(text)
        self.status_label.setStyleSheet(f"color: {color}; font-size: 11px;")

    def _refresh_list(self) -> None:
        self.operator_list.clear()
        self.operator_list.addItems(self.engine.list_template_names())

    def _capture(self) -> None:
        name = self.name_input.text().strip()
        passphrase = self.passphrase_input.text()
        if not name:
            QMessageBox.warning(self, "Peringatan", "Nama operator wajib diisi.")
            return
        if not passphrase:
            QMessageBox.warning(
                self, "Peringatan", "Passphrase enkripsi snapshot wajib diisi dan tidak akan disimpan."
            )
            return

        captured = self.camera.capture_face()
        if captured is None:
            QMessageBox.warning(self, "Peringatan", "Wajah belum terdeteksi di kamera. Nyalakan kamera dan ulangi.")
            return
        aligned, embedding, bbox = captured

        filename = f"{_safe_name(name)}_{datetime.now():%Y%m%d_%H%M%S}.png"
        encrypted_path = FACE_SNAPSHOT_DIR / f"{filename}.enc"
        try:
            with tempfile.TemporaryDirectory(prefix="sadap_face_capture_") as tmp_dir:
                plain_path = Path(tmp_dir) / filename
                if not cv2.imwrite(str(plain_path), aligned):
                    raise OSError("Gagal menulis PNG sementara untuk wajah.")
                ok, msg, _ = encrypt_file(plain_path, encrypted_path, passphrase)
            if not ok:
                raise OSError(msg)
        except Exception as exc:
            logger.error(f"Encrypted face snapshot failed: {exc}")
            QMessageBox.critical(self, "Gagal", f"Snapshot gagal dienkripsi: {exc}")
            self._status("Snapshot gagal dibuat; template belum disimpan.", "#DC2626")
            return

        if not self.engine.save_template(embedding, name):
            encrypted_path.unlink(missing_ok=True)
            QMessageBox.critical(self, "Gagal", "Gagal menyimpan template biometrik operator.")
            return

        self._audit("FACE_ENROLLED", f"{name} terdaftar; snapshot {encrypted_path.name} terenkripsi AES-256-GCM.")
        self.passphrase_input.clear()
        self._refresh_list()
        self._status(f"Operator '{name}' terdaftar. Snapshot: {encrypted_path.name}", "#059669")
        QMessageBox.information(
            self,
            "Berhasil",
            f"Wajah '{name}' terdaftar.\n\nSnapshot dienkripsi ke:\n{encrypted_path}\n\n"
            "Simpan passphrase yang Anda gunakan; tanpanya snapshot tidak dapat dilihat kembali.",
        )

    def _selected_name(self) -> str:
        item = self.operator_list.currentItem()
        return item.text() if item is not None else ""

    def _delete_operator(self) -> None:
        name = self._selected_name()
        if not name:
            QMessageBox.warning(self, "Peringatan", "Pilih operator terlebih dahulu.")
            return
        reply = QMessageBox.question(
            self,
            "Hapus Operator",
            f"Hapus wajah operator '{name}' beserta seluruh snapshot terenkripsinya?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        removed = self.engine.delete_template(name)
        deleted_files = 0
        for snapshot in FACE_SNAPSHOT_DIR.glob(f"{_safe_name(name)}_*.enc"):
            snapshot.unlink(missing_ok=True)
            deleted_files += 1

        self._audit("FACE_DELETED", f"{name} dihapus; {deleted_files} snapshot terenkripsi dihapus.")
        self._refresh_list()
        self._status(f"Operator '{name}' dihapus ({deleted_files} snapshot dihapus).", "#059669")

    def _view_snapshot(self) -> None:
        name = self._selected_name()
        if not name:
            QMessageBox.warning(self, "Peringatan", "Pilih operator terlebih dahulu.")
            return
        passphrase = self.passphrase_input.text()
        if not passphrase:
            QMessageBox.warning(self, "Peringatan", "Masukkan passphrase enkripsi snapshot terlebih dahulu.")
            return

        candidates = sorted(FACE_SNAPSHOT_DIR.glob(f"{_safe_name(name)}_*.enc"), reverse=True)
        if not candidates:
            QMessageBox.information(self, "Info", f"Tidak ada snapshot terenkripsi untuk '{name}'.")
            return

        try:
            with tempfile.TemporaryDirectory(prefix="sadap_face_view_") as tmp_dir:
                ok, msg, decrypted = decrypt_file(candidates[0], tmp_dir, passphrase)
                if not ok or decrypted is None:
                    QMessageBox.critical(self, "Gagal", msg)
                    return
                pixmap = QPixmap(str(decrypted))
                if pixmap.isNull():
                    QMessageBox.critical(self, "Gagal", "Snapshot berhasil didekripsi tetapi gagal ditampilkan.")
                    return
                SnapshotPreviewDialog(name, pixmap, self).exec()
        except Exception as exc:
            logger.error(f"Encrypted face snapshot view failed: {exc}")
            QMessageBox.critical(self, "Gagal", str(exc))
            return

        self._audit("FACE_SNAPSHOT_VIEWED", f"Snapshot terenkripsi operator {name} dilihat.")
        self._status(f"Snapshot '{name}' ditampilkan sementara; file asli tetap .enc.", "#059669")
