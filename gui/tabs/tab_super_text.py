"""
AeroSat GroundStation - Tab 1: Super-Cipher Memo (Vigenère + RSA)
Combines classical Extended Vigenère and modern RSA-OAEP asymmetric encryption.
"""
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QMessageBox,
    QApplication,
)
from PyQt6.QtCore import Qt

from core.crypto.rsa_engine import get_or_create_default_keypair, export_public_key_pem
from core.crypto.super_text_cipher import super_encrypt, super_decrypt
from core.database.db_manager import get_vault_db
from gui.components.password_line_edit import PasswordLineEdit
from core.utils.logger import get_logger

logger = get_logger("TabSuperText")


class TabSuperText(QWidget):
    """GUI tab for 2-layer Super-Encryption and Decryption."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.priv_key, self.pub_key = get_or_create_default_keypair()
        self._init_ui()

    def _init_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(16, 16, 16, 16)

        # ==========================================
        # LEFT PANEL: SUPER-ENCRYPTION
        # ==========================================
        enc_group = QGroupBox("1. Super-Encryption (Plaintext → Vigenère → RSA)")
        enc_layout = QVBoxLayout(enc_group)
        enc_layout.setSpacing(10)

        enc_layout.addWidget(QLabel("Plaintext Message / Directive:"))
        self.plain_input = QTextEdit()
        self.plain_input.setPlaceholderText("Enter classified message or satellite directive here...")
        self.plain_input.setMinimumHeight(100)
        enc_layout.addWidget(self.plain_input)

        enc_layout.addWidget(QLabel("Classical Vigenère Key (Passphrase):"))
        self.enc_vigenere_key = PasswordLineEdit(placeholder="Enter Vigenère key...")
        enc_layout.addWidget(self.enc_vigenere_key)

        key_info_label = QLabel(f"RSA Asymmetric Target: System 2048-bit Public Key (OAEP-SHA256)")
        key_info_label.setStyleSheet("color: #0284C7; font-size: 11px;")
        enc_layout.addWidget(key_info_label)

        self.btn_encrypt = QPushButton("🔒 Execute Super-Encryption")
        self.btn_encrypt.clicked.connect(self._handle_encrypt)
        enc_layout.addWidget(self.btn_encrypt)

        enc_layout.addWidget(QLabel("Super-Ciphertext Token (Base64 Output):"))
        self.cipher_output = QTextEdit()
        self.cipher_output.setReadOnly(True)
        self.cipher_output.setPlaceholderText("Encrypted token will appear here...")
        enc_layout.addWidget(self.cipher_output)

        btn_bar = QHBoxLayout()
        self.btn_copy_token = QPushButton("📋 Copy Token")
        self.btn_copy_token.setObjectName("secondaryBtn")
        self.btn_copy_token.clicked.connect(self._copy_token_to_clipboard)
        btn_bar.addWidget(self.btn_copy_token)

        self.btn_save_db = QPushButton("💾 Save to Vault DB")
        self.btn_save_db.setObjectName("secondaryBtn")
        self.btn_save_db.clicked.connect(self._save_to_db)
        btn_bar.addWidget(self.btn_save_db)
        enc_layout.addLayout(btn_bar)

        main_layout.addWidget(enc_group)

        # ==========================================
        # RIGHT PANEL: SUPER-DECRYPTION
        # ==========================================
        dec_group = QGroupBox("2. Super-Decryption (Token → RSA Decrypt → Vigenère Decrypt)")
        dec_layout = QVBoxLayout(dec_group)
        dec_layout.setSpacing(10)

        dec_layout.addWidget(QLabel("Ciphertext Token to Decrypt:"))
        self.cipher_input = QTextEdit()
        self.cipher_input.setPlaceholderText("Paste encrypted Super-Cipher token here...")
        self.cipher_input.setMinimumHeight(100)
        dec_layout.addWidget(self.cipher_input)

        dec_layout.addWidget(QLabel("Classical Vigenère Key:"))
        self.dec_vigenere_key = PasswordLineEdit(placeholder="Enter matching Vigenère key...")
        dec_layout.addWidget(self.dec_vigenere_key)

        dec_key_label = QLabel("RSA Decryption Key: Hardware-bound Private Key loaded")
        dec_key_label.setStyleSheet("color: #0284C7; font-size: 11px;")
        dec_layout.addWidget(dec_key_label)

        self.btn_decrypt = QPushButton("🔓 Execute Super-Decryption")
        self.btn_decrypt.clicked.connect(self._handle_decrypt)
        dec_layout.addWidget(self.btn_decrypt)

        dec_layout.addWidget(QLabel("Recovered Plaintext:"))
        self.recovered_output = QTextEdit()
        self.recovered_output.setReadOnly(True)
        self.recovered_output.setPlaceholderText("Decrypted message will appear here...")
        dec_layout.addWidget(self.recovered_output)

        self.status_banner = QLabel("Ready")
        self.status_banner.setStyleSheet("color: #64748B; font-weight: 600; padding: 4px;")
        dec_layout.addWidget(self.status_banner)

        main_layout.addWidget(dec_group)

    def _handle_encrypt(self):
        plain = self.plain_input.toPlainText().strip()
        v_key = self.enc_vigenere_key.text().strip()

        if not plain:
            QMessageBox.warning(self, "Warning", "Please enter a plaintext message to encrypt.")
            return
        if not v_key:
            QMessageBox.warning(self, "Warning", "Please enter a Vigenère key.")
            return

        try:
            token = super_encrypt(plain, v_key, self.pub_key)
            self.cipher_output.setPlainText(token)
            self.status_banner.setText("Status: Message successfully super-encrypted! Copy token to decrypt.")
            self.status_banner.setStyleSheet("color: #059669; font-weight: 600;")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Super-encryption failed: {str(e)}")

    def _handle_decrypt(self):
        token = self.cipher_input.toPlainText().strip()
        v_key = self.dec_vigenere_key.text().strip()

        if not token:
            QMessageBox.warning(self, "Warning", "Please paste a ciphertext token to decrypt.")
            return
        if not v_key:
            QMessageBox.warning(self, "Warning", "Please provide the Vigenère passphrase key.")
            return

        success, plain, msg = super_decrypt(token, v_key, self.priv_key)
        if success:
            self.recovered_output.setPlainText(plain)
            self.status_banner.setText("Status: " + msg)
            self.status_banner.setStyleSheet("color: #059669; font-weight: 600;")
        else:
            self.recovered_output.clear()
            self.status_banner.setText("Status: " + msg)
            self.status_banner.setStyleSheet("color: #DC2626; font-weight: 600;")
            QMessageBox.critical(self, "Decryption Failed", msg)

    def _copy_token_to_clipboard(self):
        token = self.cipher_output.toPlainText()
        if token:
            QApplication.clipboard().setText(token)
            QMessageBox.information(self, "Copied", "Ciphertext token copied to clipboard.")

    def _save_to_db(self):
        plain = self.plain_input.toPlainText().strip()
        token = self.cipher_output.toPlainText().strip()
        hint = self.enc_vigenere_key.text().strip()

        if not plain or not token:
            QMessageBox.warning(self, "Warning", "Encrypt a message first before saving to DB.")
            return

        try:
            db = get_vault_db()
            title = f"Classified Memo - {plain[:20]}..."
            memo_id = db.add_memo(title, plain, author="OPERATOR-ALPHA", vigenere_hint=hint)
            QMessageBox.information(self, "Saved", f"Classified memo saved to Encrypted Vault DB (ID: {memo_id}).")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save to database: {e}")
