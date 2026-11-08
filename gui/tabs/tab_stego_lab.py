"""
AeroSat GroundStation - Tab 3: Satellite Stego Lab
Embeds and extracts secret directives into high-resolution satellite imagery (LSB).
"""
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QFileDialog,
    QMessageBox,
)
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import Qt

from config.settings import SAMPLE_IMAGES_DIR
from gui.components.password_line_edit import PasswordLineEdit
from core.stego.lsb_engine import (
    embed_payload_into_image,
    extract_payload_from_image,
    calculate_image_capacity,
)
from core.database.db_manager import get_vault_db
from core.utils.logger import get_logger

logger = get_logger("TabStegoLab")


class TabStegoLab(QWidget):
    """GUI tab for LSB Image Steganography."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.default_sample_path = SAMPLE_IMAGES_DIR / "satellite_base.png"
        self._init_ui()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # ==========================================
        # LEFT PANEL: EMBEDDING
        # ==========================================
        emb_group = QGroupBox("1. Steganography Embedding (Hide Data into Satellite Image)")
        e_layout = QVBoxLayout(emb_group)
        e_layout.setSpacing(8)

        # Cover Image Picker
        cov_layout = QHBoxLayout()
        self.cover_input = QLineEdit()
        if self.default_sample_path.exists():
            self.cover_input.setText(str(self.default_sample_path))
        self.cover_input.setPlaceholderText("Select cover satellite image (.png, .bmp)...")
        cov_layout.addWidget(self.cover_input)

        self.btn_browse_cover = QPushButton("📁 Browse...")
        self.btn_browse_cover.clicked.connect(self._browse_cover)
        cov_layout.addWidget(self.btn_browse_cover)
        e_layout.addLayout(cov_layout)

        # Thumbnail Preview & Capacity
        self.cover_preview = QLabel("Cover Image Preview")
        self.cover_preview.setFixedSize(220, 140)
        self.cover_preview.setStyleSheet("background-color: #F1F5F9; border: 1px solid #CBD5E1; border-radius: 6px;")
        self.cover_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        e_layout.addWidget(self.cover_preview, alignment=Qt.AlignmentFlag.AlignCenter)

        self.capacity_label = QLabel("Payload Capacity: Computing...")
        self.capacity_label.setStyleSheet("color: #0284C7; font-weight: 600; font-size: 11px;")
        e_layout.addWidget(self.capacity_label)

        # Secret Payload Input
        e_layout.addWidget(QLabel("Secret Message to Hide:"))
        self.secret_text_input = QTextEdit()
        self.secret_text_input.setPlaceholderText("Enter confidential message, coordinates, or directive...")
        self.secret_text_input.setMaximumHeight(80)
        e_layout.addWidget(self.secret_text_input)

        # Optional Pre-encryption
        e_layout.addWidget(QLabel("Optional AES-256 Pre-Encryption Passphrase:"))
        self.emb_passphrase_input = PasswordLineEdit(placeholder="Leave blank for plain LSB, or enter passphrase for Crypto-Stego...")
        e_layout.addWidget(self.emb_passphrase_input)

        self.btn_embed = QPushButton("🛰️ Embed Secret Payload (LSB)")
        self.btn_embed.clicked.connect(self._handle_embed)
        e_layout.addWidget(self.btn_embed)

        self.emb_status_label = QLabel("Ready to embed.")
        self.emb_status_label.setStyleSheet("color: #475569; font-weight: 600;")
        e_layout.addWidget(self.emb_status_label)

        main_layout.addWidget(emb_group)

        # ==========================================
        # RIGHT PANEL: EXTRACTION
        # ==========================================
        ext_group = QGroupBox("2. Steganography Extraction (Read Secret from Image)")
        x_layout = QVBoxLayout(ext_group)
        x_layout.setSpacing(8)

        # Stego Image Picker
        stego_layout = QHBoxLayout()
        self.stego_input = QLineEdit()
        self.stego_input.setPlaceholderText("Select stego satellite image containing hidden payload...")
        stego_layout.addWidget(self.stego_input)

        self.btn_browse_stego = QPushButton("📁 Browse...")
        self.btn_browse_stego.clicked.connect(self._browse_stego)
        stego_layout.addWidget(self.btn_browse_stego)
        x_layout.addLayout(stego_layout)

        # Stego Preview
        self.stego_preview = QLabel("Stego Image Preview")
        self.stego_preview.setFixedSize(220, 140)
        self.stego_preview.setStyleSheet("background-color: #F1F5F9; border: 1px solid #CBD5E1; border-radius: 6px;")
        self.stego_preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        x_layout.addWidget(self.stego_preview, alignment=Qt.AlignmentFlag.AlignCenter)

        # Passphrase for Decryption
        x_layout.addWidget(QLabel("Passphrase (if payload was pre-encrypted):"))
        self.ext_passphrase_input = PasswordLineEdit(placeholder="Enter passphrase if image is protected...")
        x_layout.addWidget(self.ext_passphrase_input)

        self.btn_extract = QPushButton("🔍 Extract Secret Payload")
        self.btn_extract.clicked.connect(self._handle_extract)
        x_layout.addWidget(self.btn_extract)

        x_layout.addWidget(QLabel("Extracted Secret Payload:"))
        self.extracted_text_output = QTextEdit()
        self.extracted_text_output.setReadOnly(True)
        self.extracted_text_output.setPlaceholderText("Extracted secret will appear here...")
        x_layout.addWidget(self.extracted_text_output)

        self.ext_status_label = QLabel("Ready to extract.")
        self.ext_status_label.setStyleSheet("color: #475569; font-weight: 600;")
        x_layout.addWidget(self.ext_status_label)

        main_layout.addWidget(ext_group)

        # Load initial thumbnail
        if self.default_sample_path.exists():
            self._update_cover_thumbnail(self.default_sample_path)

    def _update_cover_thumbnail(self, path: Path):
        pix = QPixmap(str(path))
        if not pix.isNull():
            self.cover_preview.setPixmap(
                pix.scaled(
                    self.cover_preview.width(),
                    self.cover_preview.height(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            )
            cap = calculate_image_capacity(pix.width(), pix.height())
            self.capacity_label.setText(
                f"Image: {pix.width()}x{pix.height()} px | Safe Capacity: {cap} Bytes (~{cap/1024:.1f} KB)"
            )

    def _browse_cover(self):
        f, _ = QFileDialog.getOpenFileName(self, "Select Cover Image", "", "PNG/BMP Images (*.png *.bmp)")
        if f:
            p = Path(f)
            self.cover_input.setText(str(p))
            self._update_cover_thumbnail(p)

    def _browse_stego(self):
        f, _ = QFileDialog.getOpenFileName(self, "Select Stego Image", "", "PNG/BMP Images (*.png *.bmp)")
        if f:
            p = Path(f)
            self.stego_input.setText(str(p))
            pix = QPixmap(str(p))
            if not pix.isNull():
                self.stego_preview.setPixmap(
                    pix.scaled(
                        self.stego_preview.width(),
                        self.stego_preview.height(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                )

    def _handle_embed(self):
        cov_str = self.cover_input.text().strip()
        secret = self.secret_text_input.toPlainText().strip()
        passphrase = self.emb_passphrase_input.text().strip() or None

        if not cov_str or not Path(cov_str).exists():
            QMessageBox.warning(self, "Warning", "Please select a valid cover image.")
            return
        if not secret:
            QMessageBox.warning(self, "Warning", "Please enter a secret message to embed.")
            return

        cov_p = Path(cov_str)
        out_p = cov_p.parent / f"stego_{cov_p.stem}.png"

        ok, msg, meta = embed_payload_into_image(
            cov_p,
            out_p,
            secret,
            passphrase=passphrase
        )

        if ok:
            self.emb_status_label.setText(f"Embedded! PSNR: {meta.get('psnr_db')} dB (Lossless)")
            self.emb_status_label.setStyleSheet("color: #059669; font-weight: 600;")

            # Auto-load into right panel for instant extraction testing
            self.stego_input.setText(str(out_p))
            self._browse_stego_direct(out_p)
            if passphrase:
                self.ext_passphrase_input.setText(passphrase)

            # Record in DB
            try:
                db = get_vault_db()
                db.add_stego_record(str(out_p), secret[:30] + "...", len(secret), meta.get("psnr_db", 0.0))
            except Exception:
                pass

            QMessageBox.information(
                self,
                "Embedding Successful",
                f"Stego image generated successfully!\n\nLocation: {out_p}\nPSNR: {meta.get('psnr_db')} dB (Visually identical)"
            )
        else:
            self.emb_status_label.setText(f"Failed: {msg}")
            self.emb_status_label.setStyleSheet("color: #DC2626; font-weight: 600;")
            QMessageBox.critical(self, "Error", msg)

    def _browse_stego_direct(self, path: Path):
        pix = QPixmap(str(path))
        if not pix.isNull():
            self.stego_preview.setPixmap(
                pix.scaled(
                    self.stego_preview.width(),
                    self.stego_preview.height(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )
            )

    def _handle_extract(self):
        stego_str = self.stego_input.text().strip()
        passphrase = self.ext_passphrase_input.text().strip() or None

        if not stego_str or not Path(stego_str).exists():
            QMessageBox.warning(self, "Warning", "Please select a valid stego image.")
            return

        ok, msg, data, meta = extract_payload_from_image(stego_str, passphrase=passphrase)

        if ok:
            self.extracted_text_output.setPlainText(str(data))
            self.ext_status_label.setText(f"Secret payload extracted successfully ({meta.get('payload_length_bytes')} B)")
            self.ext_status_label.setStyleSheet("color: #059669; font-weight: 600;")
        else:
            self.extracted_text_output.clear()
            self.ext_status_label.setText(f"Extraction failed: {msg}")
            self.ext_status_label.setStyleSheet("color: #DC2626; font-weight: 600;")
            QMessageBox.critical(self, "Extraction Error", msg)
