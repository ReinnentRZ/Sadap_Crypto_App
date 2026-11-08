"""
AeroSat GroundStation - Tab 2: AES-256-GCM File Vault
Encrypts and decrypts large files in streaming authenticated chunks (AEAD).
"""
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QFileDialog,
    QProgressBar,
    QMessageBox,
    QApplication,
)
from PyQt6.QtCore import Qt

from core.crypto.file_aes import encrypt_file, decrypt_file
from core.blockchain.asset_tracker import AssetTracker
from core.database.db_manager import get_vault_db
from core.utils.crypto_helpers import sha256_hash_file
from core.utils.logger import get_logger

logger = get_logger("TabFileCrypto")


class TabFileCrypto(QWidget):
    """GUI tab for AES-256-GCM File Encryption and Decryption."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_file_path: Path | None = None
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(16, 16, 16, 16)

        # 1. File Selection Group
        file_group = QGroupBox("1. File Target Selection")
        f_layout = QVBoxLayout(file_group)

        browse_layout = QHBoxLayout()
        self.file_path_input = QLineEdit()
        self.file_path_input.setPlaceholderText("Select any file to encrypt (.pdf, .png, .zip, .docx, .bin) or encrypted (.enc) file to decrypt...")
        browse_layout.addWidget(self.file_path_input)

        self.btn_browse = QPushButton("📁 Browse File...")
        self.btn_browse.clicked.connect(self._browse_file)
        browse_layout.addWidget(self.btn_browse)
        f_layout.addLayout(browse_layout)

        self.file_info_label = QLabel("No file selected.")
        self.file_info_label.setStyleSheet("color: #64748B; font-size: 11px;")
        f_layout.addWidget(self.file_info_label)

        layout.addWidget(file_group)

        # 2. Cryptographic Passphrase Group
        pass_group = QGroupBox("2. AES-256 Symmetric Key Derivation (PBKDF2-HMAC-SHA256)")
        p_layout = QVBoxLayout(pass_group)

        p_layout.addWidget(QLabel("Passphrase / Cipher Key:"))
        self.passphrase_input = QLineEdit()
        self.passphrase_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.passphrase_input.setPlaceholderText("Enter high-entropy encryption passphrase...")
        self.passphrase_input.setText("AeroSat-Classified-Key-99")
        p_layout.addWidget(self.passphrase_input)

        layout.addWidget(pass_group)

        # 3. Action & Progress Group
        act_group = QGroupBox("3. Encryption & Decryption Execution")
        a_layout = QVBoxLayout(act_group)

        btn_layout = QHBoxLayout()
        self.btn_encrypt = QPushButton("🔒 Encrypt File (AES-256-GCM)")
        self.btn_encrypt.clicked.connect(self._handle_encrypt)
        btn_layout.addWidget(self.btn_encrypt)

        self.btn_decrypt = QPushButton("🔓 Decrypt File (.enc → Original)")
        self.btn_decrypt.setObjectName("secondaryBtn")
        self.btn_decrypt.clicked.connect(self._handle_decrypt)
        btn_layout.addWidget(self.btn_decrypt)
        a_layout.addLayout(btn_layout)

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        a_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("Ready for file operations.")
        self.status_label.setStyleSheet("font-weight: 600; color: #475569;")
        a_layout.addWidget(self.status_label)

        layout.addWidget(act_group)
        layout.addStretch()

    def _browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Target File",
            "",
            "All Files (*.*);;Encrypted Files (*.enc)"
        )
        if file_path:
            p = Path(file_path)
            self.selected_file_path = p
            self.file_path_input.setText(str(p))

            size_kb = p.stat().st_size / 1024.0
            h = sha256_hash_file(str(p))
            self.file_info_label.setText(
                f"File: {p.name} | Size: {size_kb:.2f} KB | SHA-256: {h[:16]}...{h[-8:]}"
            )
            self.progress_bar.setValue(0)
            self.status_label.setText("File selected. Ready to encrypt or decrypt.")

    def _handle_encrypt(self):
        path_str = self.file_path_input.text().strip()
        passphrase = self.passphrase_input.text().strip()

        if not path_str or not Path(path_str).exists():
            QMessageBox.warning(self, "Warning", "Please select a valid file to encrypt.")
            return
        if not passphrase:
            QMessageBox.warning(self, "Warning", "Passphrase is required for AES-256 key derivation.")
            return

        in_p = Path(path_str)
        out_p = in_p.with_name(in_p.name + ".enc")

        self.status_label.setText("Encrypting file in 64 KB streaming chunks...")
        QApplication.processEvents()

        def update_pct(val):
            self.progress_bar.setValue(int(val))
            QApplication.processEvents()

        success, msg, meta = encrypt_file(
            in_p,
            out_p,
            passphrase,
            progress_callback=update_pct
        )

        if success:
            self.progress_bar.setValue(100)
            self.status_label.setText(f"File encrypted: {out_p.name} (Tag Verified)")
            self.status_label.setStyleSheet("color: #059669; font-weight: 600;")

            # Record to DB and offer Blockchain Notarization
            try:
                db = get_vault_db()
                orig_hash = sha256_hash_file(str(in_p))
                db.add_file_record(in_p.name, str(out_p), in_p.stat().st_size, orig_hash)
            except Exception:
                pass

            reply = QMessageBox.question(
                self,
                "File Encrypted",
                f"File successfully encrypted to:\n{out_p}\n\nDo you want to anchor this file's fingerprint to the Blockchain now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                tracker = AssetTracker()
                tracker.register_file_asset(in_p, in_p.name, owner_callsign="OPERATOR-ALPHA")
                QMessageBox.information(self, "Anchored", "File fingerprint successfully anchored to Blockchain!")
        else:
            self.status_label.setText(f"Encryption failed: {msg}")
            self.status_label.setStyleSheet("color: #DC2626; font-weight: 600;")
            QMessageBox.critical(self, "Error", msg)

    def _handle_decrypt(self):
        path_str = self.file_path_input.text().strip()
        passphrase = self.passphrase_input.text().strip()

        if not path_str or not Path(path_str).exists():
            QMessageBox.warning(self, "Warning", "Please select an encrypted (.enc) file to decrypt.")
            return
        if not passphrase:
            QMessageBox.warning(self, "Warning", "Passphrase is required.")
            return

        in_p = Path(path_str)
        out_dir = in_p.parent / "decrypted_files"

        self.status_label.setText("Decrypting and authenticating file...")
        QApplication.processEvents()

        def update_pct(val):
            self.progress_bar.setValue(int(val))
            QApplication.processEvents()

        success, msg, recovered_path = decrypt_file(
            in_p,
            out_dir,
            passphrase,
            progress_callback=update_pct
        )

        if success and recovered_path:
            self.progress_bar.setValue(100)
            self.status_label.setText(f"Decrypted successfully: {recovered_path.name}")
            self.status_label.setStyleSheet("color: #059669; font-weight: 600;")
            QMessageBox.information(
                self,
                "Decryption Successful",
                f"File decrypted and authenticated successfully!\nSaved to: {recovered_path}"
            )
        else:
            self.status_label.setText(f"Decryption failed: {msg}")
            self.status_label.setStyleSheet("color: #DC2626; font-weight: 600;")
            QMessageBox.critical(self, "Decryption Failed", msg)
