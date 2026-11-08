"""
Sadap GroundStation - Classified Covert Intelligence Dashboard Window
Hosts the full cryptography suite: Super-Cipher, AES Files, Stego Lab, DB Vault, and Blockchain.
Includes live Master Clearance Passcode management from inside the classified vault.
"""
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QLabel,
    QPushButton,
    QStatusBar,
    QMessageBox,
    QDialog,
    QFormLayout,
    QLineEdit,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QKeySequence, QShortcut

from config.settings import DATA_DIR
from core.auth.hasher import hash_password, verify_password
from gui.tabs.tab_super_text import TabSuperText
from gui.tabs.tab_file_crypto import TabFileCrypto
from gui.tabs.tab_stego_lab import TabStegoLab
from gui.tabs.tab_database_vault import TabDatabaseVault
from gui.tabs.tab_blockchain_view import TabBlockchainView
from core.database.db_manager import get_vault_db
from gui.components.password_line_edit import PasswordLineEdit
from core.utils.logger import get_logger

logger = get_logger("SecretDashboard")


class ChangeMasterCodeDialog(QDialog):
    """Modal dialog allowing authorized operator to update Master Clearance Passcode."""

    def __init__(self, parent=None, operator_callsign: str = "OPERATOR"):
        super().__init__(parent)
        self.operator_callsign = operator_callsign
        self.setWindowTitle("Change Master Clearance Passcode")
        self.setFixedSize(420, 260)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(18, 16, 18, 16)

        title = QLabel("<b>Update Master Clearance Passcode (Factor 3)</b>")
        title.setStyleSheet("color: #0284C7; font-size: 13px;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(8)

        self.old_pass_input = PasswordLineEdit(self, placeholder="Current passcode...")
        form.addRow("Current Passcode:", self.old_pass_input)

        self.new_pass_input = PasswordLineEdit(self, placeholder="New passcode (min 8 chars)...")
        form.addRow("New Passcode:", self.new_pass_input)

        self.confirm_pass_input = PasswordLineEdit(self, placeholder="Confirm new passcode...")
        form.addRow("Confirm Passcode:", self.confirm_pass_input)

        layout.addLayout(form)

        btn_box = QHBoxLayout()
        btn_box.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("secondaryBtn")
        cancel_btn.clicked.connect(self.reject)
        btn_box.addWidget(cancel_btn)

        save_btn = QPushButton("💾 Save New Passcode")
        save_btn.setStyleSheet("background-color: #0284C7; color: #FFFFFF; font-weight: bold; padding: 6px 14px;")
        save_btn.clicked.connect(self._save_passcode)
        btn_box.addWidget(save_btn)

        layout.addLayout(btn_box)

    def _save_passcode(self):
        old_pass = self.old_pass_input.text().strip()
        new_pass = self.new_pass_input.text().strip()
        confirm_pass = self.confirm_pass_input.text().strip()

        if not old_pass or not new_pass or not confirm_pass:
            QMessageBox.warning(self, "Peringatan", "Semua kolom passcode wajib diisi.")
            return

        cred_file = DATA_DIR / "keys" / "master_credential.hash"
        stored_hash = ""
        if cred_file.exists():
            stored_hash = cred_file.read_text(encoding="utf-8").strip()

        if not verify_password(old_pass, stored_hash):
            QMessageBox.critical(self, "Akses Ditolak", "Passcode lama yang Anda masukkan tidak cocok!")
            return

        if len(new_pass) < 8:
            QMessageBox.warning(self, "Peringatan", "Passcode baru minimal 8 karakter demi keamanan.")
            return

        if new_pass != confirm_pass:
            QMessageBox.warning(self, "Peringatan", "Konfirmasi passcode baru tidak cocok!")
            return

        # Compute new PBKDF2 hash with fresh cryptographic salt
        new_hash = hash_password(new_pass)
        cred_file.parent.mkdir(parents=True, exist_ok=True)
        cred_file.write_text(new_hash, encoding="utf-8")

        # Log security audit event
        try:
            db = get_vault_db()
            db.add_audit_log(
                event_type="MASTER_PASSCODE_CHANGED",
                details=f"Master clearance passcode updated by {self.operator_callsign}.",
                operator=self.operator_callsign,
            )
        except Exception:
            pass

        QMessageBox.information(
            self,
            "Berhasil",
            "Master Clearance Passcode berhasil diubah!\n\n"
            "Gunakan passcode baru ini untuk autentikasi gerbang rahasia berikutnya.",
        )
        self.accept()


class SecretDashboardWindow(QMainWindow):
    """The covert classified intelligence suite."""

    def __init__(self, parent=None, operator_callsign: str = "OPERATOR-ALPHA"):
        super().__init__(parent)
        self.operator_callsign = operator_callsign
        self.setWindowTitle("Sadap Classified Intelligence Vault — BlackOps Directive v2.4")
        self.resize(1300, 840)
        self.setMinimumSize(1080, 720)

        self._init_ui()
        self._log_access_event()

    def _init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

        # Top Header Bar
        header_bar = QHBoxLayout()

        badge_layout = QVBoxLayout()
        title_lbl = QLabel("🛰️ SADAP CLASSIFIED INTELLIGENCE VAULT")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #0284C7;")
        badge_layout.addWidget(title_lbl)

        sec_badge = QLabel(f"SECURITY CLEARANCE: TOP SECRET / SCI  |  OPERATOR: {self.operator_callsign}")
        sec_badge.setStyleSheet("color: #059669; font-weight: bold; font-size: 11px;")
        badge_layout.addWidget(sec_badge)
        header_bar.addLayout(badge_layout)

        header_bar.addStretch()

        # Fullscreen Toggle Button & Shortcut
        self.btn_fullscreen = QPushButton("⛶ Fullscreen (F11)")
        self.btn_fullscreen.setObjectName("secondaryBtn")
        self.btn_fullscreen.setStyleSheet("padding: 8px 12px; font-size: 11px;")
        self.btn_fullscreen.clicked.connect(self._toggle_fullscreen)
        header_bar.addWidget(self.btn_fullscreen)

        # F11 Shortcut for True Fullscreen Toggle
        self.f11_shortcut = QShortcut(QKeySequence("F11"), self)
        self.f11_shortcut.activated.connect(self._toggle_fullscreen)

        # Change Master Code Button
        self.btn_change_code = QPushButton("🔑 Change Master Code")
        self.btn_change_code.setObjectName("secondaryBtn")
        self.btn_change_code.setStyleSheet("padding: 8px 12px; font-size: 11px;")
        self.btn_change_code.clicked.connect(self._open_change_code_dialog)
        header_bar.addWidget(self.btn_change_code)

        # Lock and Return Button
        self.btn_lock = QPushButton("🔒 Lock & Return to Cover Mode")
        self.btn_lock.setStyleSheet("background-color: #DC2626; color: #FFFFFF; font-weight: bold; padding: 8px 16px;")
        self.btn_lock.clicked.connect(self._lock_and_return)
        header_bar.addWidget(self.btn_lock)

        main_layout.addLayout(header_bar)

        # Tab Widget
        self.tabs = QTabWidget()
        self.tab_super_text = TabSuperText(self)
        self.tab_file_crypto = TabFileCrypto(self)
        self.tab_stego_lab = TabStegoLab(self)
        self.tab_db_vault = TabDatabaseVault(self)
        self.tab_blockchain = TabBlockchainView(self)

        self.tabs.addTab(self.tab_super_text, "📜 Super-Cipher (Vigenère+RSA)")
        self.tabs.addTab(self.tab_file_crypto, "📁 File AES-256 Vault")
        self.tabs.addTab(self.tab_stego_lab, "🛰️ Satellite Stego Lab")
        self.tabs.addTab(self.tab_db_vault, "🗄️ Encrypted DB Vault")
        self.tabs.addTab(self.tab_blockchain, "⛓️ Blockchain Ledger")

        main_layout.addWidget(self.tabs)

        # Status Bar
        status = QStatusBar()
        status.showMessage("All cryptographic modules initialized. Zero-trust session active.")
        self.setStatusBar(status)

    def _open_change_code_dialog(self):
        """Open the modal dialog to update master passcode."""
        dlg = ChangeMasterCodeDialog(self, operator_callsign=self.operator_callsign)
        dlg.exec()

    def _log_access_event(self):
        """Log authentication event to encrypted database."""
        try:
            db = get_vault_db()
            db.add_audit_log(
                event_type="AUTH_VAULT_ACCESSED",
                details=f"Classified vault unlocked by {self.operator_callsign}. All modules active.",
                operator=self.operator_callsign,
            )
        except Exception:
            pass

    def _lock_and_return(self):
        """Lock the vault and return to normal public ground station cover."""
        reply = QMessageBox.question(
            self,
            "Lock Classified Vault",
            "Are you sure you want to lock the classified vault and return to Cover Mode?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                db = get_vault_db()
                db.add_audit_log(
                    event_type="AUTH_VAULT_LOCKED",
                    details=f"Vault session closed by {self.operator_callsign}.",
                    operator=self.operator_callsign,
                )
            except Exception:
                pass
            self.close()
            if self.parent():
                self.parent().showMaximized()

    def _toggle_fullscreen(self):
        """Toggle between Fullscreen and Maximized mode."""
        if self.isFullScreen():
            self.showMaximized()
            if hasattr(self, "btn_fullscreen"):
                self.btn_fullscreen.setText("⛶ Fullscreen (F11)")
        else:
            self.showFullScreen()
            if hasattr(self, "btn_fullscreen"):
                self.btn_fullscreen.setText("🗗 Windowed (F11)")
