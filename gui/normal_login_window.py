"""
Sadap GroundStation - Normal Operator Login & Registration Portal
The initial access gate for the public cover mode.
Provides legitimate authentication with PBKDF2 hashed credentials in SQLite.
"""
from PyQt6.QtWidgets import (
    QDialog,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QGroupBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QMessageBox,
)
from PyQt6.QtCore import Qt, pyqtSignal

from core.database.db_manager import get_vault_db
from core.utils.logger import get_logger

logger = get_logger("NormalLogin")


class NormalLoginWindow(QDialog):
    """Initial public portal for ground station operators."""

    login_successful = pyqtSignal(dict)  # emits operator_data dict

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sadap GroundStation — Operator Access Portal")
        self.setFixedSize(460, 480)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)

        self.db = get_vault_db()
        self.authenticated_operator: dict | None = None

        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(14)
        layout.setContentsMargins(24, 20, 24, 20)

        # Header Title
        title_box = QVBoxLayout()
        header_title = QLabel("🛰️ SADAP GROUNDSTATION")
        header_title.setStyleSheet("font-size: 18px; font-weight: bold; color: #0284C7;")
        header_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_box.addWidget(header_title)

        header_sub = QLabel("Earth Observation & Geospatial Command System")
        header_sub.setStyleSheet("color: #64748B; font-size: 11px;")
        header_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_box.addWidget(header_sub)
        layout.addLayout(title_box)

        # Tabs: Sign In / Register
        self.tab_widget = QTabWidget()

        # -----------------------------------------------
        # TAB 1: OPERATOR LOGIN
        # -----------------------------------------------
        login_tab = QWidget()
        l_layout = QVBoxLayout(login_tab)
        l_layout.setSpacing(12)
        l_layout.setContentsMargins(12, 16, 12, 12)

        l_layout.addWidget(QLabel("Operator Callsign / Username:"))
        self.login_user_input = QLineEdit()
        self.login_user_input.setPlaceholderText("Enter operator username...")
        l_layout.addWidget(self.login_user_input)

        l_layout.addWidget(QLabel("Station Password:"))
        self.login_pwd_input = QLineEdit()
        self.login_pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.login_pwd_input.setPlaceholderText("Enter station access password...")
        self.login_pwd_input.returnPressed.connect(self._handle_login)
        l_layout.addWidget(self.login_pwd_input)

        l_layout.addStretch()

        self.btn_login = QPushButton("🔑 Sign In to Ground Station")
        self.btn_login.setStyleSheet("background-color: #0284C7; padding: 10px; font-weight: bold;")
        self.btn_login.clicked.connect(self._handle_login)
        l_layout.addWidget(self.btn_login)

        self.tab_widget.addTab(login_tab, "Operator Sign In")

        # -----------------------------------------------
        # TAB 2: REGISTER NEW OPERATOR
        # -----------------------------------------------
        reg_tab = QWidget()
        r_layout = QVBoxLayout(reg_tab)
        r_layout.setSpacing(10)
        r_layout.setContentsMargins(12, 14, 12, 12)

        r_layout.addWidget(QLabel("Full Name:"))
        self.reg_fullname_input = QLineEdit()
        self.reg_fullname_input.setPlaceholderText("e.g. Alex Pratama, S.T.")
        r_layout.addWidget(self.reg_fullname_input)

        r_layout.addWidget(QLabel("Operator Username:"))
        self.reg_user_input = QLineEdit()
        self.reg_user_input.setPlaceholderText("e.g. apratama")
        r_layout.addWidget(self.reg_user_input)

        r_layout.addWidget(QLabel("Assigned Mission Role:"))
        self.reg_role_combo = QComboBox()
        self.reg_role_combo.addItems([
            "Observation Specialist",
            "Geospatial Telemetry Analyst",
            "Orbital Flight Controller",
            "Ground Station Supervisor",
        ])
        r_layout.addWidget(self.reg_role_combo)

        r_layout.addWidget(QLabel("Password:"))
        self.reg_pwd_input = QLineEdit()
        self.reg_pwd_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.reg_pwd_input.setPlaceholderText("Minimum 4 characters...")
        r_layout.addWidget(self.reg_pwd_input)

        r_layout.addStretch()

        self.btn_register = QPushButton("📝 Register Operator Account")
        self.btn_register.setObjectName("secondaryBtn")
        self.btn_register.clicked.connect(self._handle_register)
        r_layout.addWidget(self.btn_register)

        self.tab_widget.addTab(reg_tab, "Register New Operator")

        layout.addWidget(self.tab_widget)

    def _handle_login(self):
        username = self.login_user_input.text().strip()
        password = self.login_pwd_input.text().strip()

        ok, user_data, msg = self.db.authenticate_operator(username, password)
        if ok and user_data:
            self.authenticated_operator = user_data
            logger.info(f"Operator '{username}' logged in successfully.")
            self.login_successful.emit(user_data)
            self.accept()
        else:
            QMessageBox.critical(self, "Login Failed", msg)

    def _handle_register(self):
        fullname = self.reg_fullname_input.text().strip()
        username = self.reg_user_input.text().strip()
        role = self.reg_role_combo.currentText()
        password = self.reg_pwd_input.text().strip()

        if not fullname:
            QMessageBox.warning(self, "Warning", "Please enter your full name.")
            return

        ok, msg = self.db.register_operator(username, password, full_name=fullname, role=role)
        if ok:
            QMessageBox.information(self, "Registered", f"{msg}\nYou can now sign in using your new credentials.")
            # Switch back to login tab and prefill
            self.login_user_input.setText(username.lower())
            self.login_pwd_input.setText(password)
            self.tab_widget.setCurrentIndex(0)
        else:
            QMessageBox.warning(self, "Registration Error", msg)
