"""
AeroSat GroundStation - Classified Covert Intelligence Dashboard Window
Hosts the full cryptography suite: Super-Cipher, AES Files, Stego Lab, DB Vault, and Blockchain.
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
)
from PyQt6.QtCore import Qt

from gui.tabs.tab_super_text import TabSuperText
from gui.tabs.tab_file_crypto import TabFileCrypto
from gui.tabs.tab_stego_lab import TabStegoLab
from gui.tabs.tab_database_vault import TabDatabaseVault
from gui.tabs.tab_blockchain_view import TabBlockchainView
from core.database.db_manager import get_vault_db
from core.utils.logger import get_logger

logger = get_logger("SecretDashboard")


class SecretDashboardWindow(QMainWindow):
    """The covert classified intelligence suite."""

    def __init__(self, operator_callsign: str = "COMMANDER-ALPHA-01", parent=None):
        super().__init__(parent)
        self.operator_callsign = operator_callsign
        self.setWindowTitle("AeroSat GroundStation — Classified Covert Crypto Suite [BLACKOPS]")
        self.resize(1080, 720)
        self.setMinimumSize(960, 640)

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
        title_lbl = QLabel("🛰️ AEROSAT CLASSIFIED INTELLIGENCE VAULT")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #0284C7;")
        badge_layout.addWidget(title_lbl)

        sec_badge = QLabel(f"SECURITY CLEARANCE: TOP SECRET / SCI  |  OPERATOR: {self.operator_callsign}")
        sec_badge.setStyleSheet("color: #059669; font-weight: bold; font-size: 11px;")
        badge_layout.addWidget(sec_badge)
        header_bar.addLayout(badge_layout)

        header_bar.addStretch()

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

    def _log_access_event(self):
        """Log authentication event to encrypted database."""
        try:
            db = get_vault_db()
            db.add_audit_log(
                event_type="AUTH_VAULT_ACCESSED",
                details=f"Classified vault unlocked by {self.operator_callsign}. All modules active.",
                operator=self.operator_callsign
            )
        except Exception:
            pass

    def _lock_and_return(self):
        """Lock the vault and return to normal public ground station cover."""
        reply = QMessageBox.question(
            self,
            "Lock Classified Vault",
            "Are you sure you want to lock the classified vault and return to Cover Mode?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                db = get_vault_db()
                db.add_audit_log(
                    event_type="AUTH_VAULT_LOCKED",
                    details=f"Vault session closed by {self.operator_callsign}.",
                    operator=self.operator_callsign
                )
            except Exception:
                pass
            self.close()
            if self.parent():
                self.parent().show()
