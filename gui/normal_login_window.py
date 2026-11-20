"""
Sadap GroundStation - Operator Login & Registration Portal (Modern Light UI)
"""
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QMessageBox,
    QFrame,
    QSizePolicy,
    QGraphicsDropShadowEffect,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut, QPainter, QColor, QLinearGradient

from core.database.db_manager import get_vault_db
from gui.components.password_line_edit import PasswordLineEdit
from core.utils.logger import get_logger

logger = get_logger("NormalLogin")


class LoginBackgroundWidget(QWidget):
    """Subtle light background for the login screen."""

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        grad = QLinearGradient(0, 0, 0, h)
        grad.setColorAt(0.0, QColor("#F8FAFC"))
        grad.setColorAt(1.0, QColor("#EEF2F7"))
        painter.fillRect(0, 0, w, h, grad)

        # Soft accent glow
        painter.setBrush(QColor(37, 99, 235, 18))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(int(w * 0.5 - 220), int(h * 0.5 - 260), 440, 440)
        painter.end()


class NormalLoginWindow(QMainWindow):
    """Fullscreen login workstation for ground station operators."""

    login_successful = pyqtSignal(dict)  # emits operator_data dict

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sadap GroundStation - Operator Access Portal")
        self.resize(1280, 800)
        self.setMinimumSize(960, 640)

        self.db = get_vault_db()
        self.authenticated_operator: dict | None = None

        self._init_ui()
        self._setup_shortcuts()

    def _setup_shortcuts(self):
        self.f11_shortcut = QShortcut(QKeySequence("F11"), self)
        self.f11_shortcut.activated.connect(self._toggle_fullscreen)

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showMaximized()
        else:
            self.showFullScreen()

    def _create_form_group(self, label_text: str, widget: QWidget, helper: str = "") -> QWidget:
        group = QWidget()
        group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        lbl = QLabel(label_text)
        lbl.setObjectName("fieldLabel")
        layout.addWidget(lbl)

        widget.setMinimumHeight(44)
        widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout.addWidget(widget)

        if helper:
            help_lbl = QLabel(helper)
            help_lbl.setObjectName("helperText")
            layout.addWidget(help_lbl)
        return group

    def _style_input(self, widget: QLineEdit, placeholder: str = ""):
        if placeholder:
            widget.setPlaceholderText(placeholder)
        widget.setStyleSheet(
            """
            QLineEdit {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 10px 12px;
                font-size: 13px;
                color: #1E293B;
            }
            QLineEdit:hover { border-color: #94A3B8; }
            QLineEdit:focus { border: 1px solid #2563EB; background-color: #FFFFFF; }
            """
        )

    def _init_ui(self):
        bg_canvas = LoginBackgroundWidget(self)
        self.setCentralWidget(bg_canvas)

        main_layout = QVBoxLayout(bg_canvas)
        main_layout.setContentsMargins(24, 24, 24, 24)

        main_layout.addStretch(1)

        center_row = QHBoxLayout()
        center_row.addStretch(1)

        self.card = QFrame()
        self.card.setObjectName("loginCard")
        self.card.setFixedWidth(420)
        self.card.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Maximum)

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(28)
        shadow.setColor(QColor(15, 23, 42, 35))
        shadow.setOffset(0, 8)
        self.card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(32, 32, 32, 28)
        card_layout.setSpacing(16)

        # Branding
        brand_box = QVBoxLayout()
        brand_box.setSpacing(8)
        brand_box.setAlignment(Qt.AlignmentFlag.AlignCenter)

        logo = QLabel("SG")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo.setFixedSize(56, 56)
        logo.setStyleSheet(
            """
            QLabel {
                background-color: #EFF6FF;
                color: #2563EB;
                border: 1px solid #BFDBFE;
                border-radius: 28px;
                font-size: 18px;
                font-weight: 700;
            }
            """
        )
        brand_box.addWidget(logo, alignment=Qt.AlignmentFlag.AlignCenter)

        app_name = QLabel("Sadap GroundStation")
        app_name.setObjectName("loginTitle")
        app_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_box.addWidget(app_name)

        app_desc = QLabel("Earth Observation & Geospatial Command Console")
        app_desc.setObjectName("loginSubtitle")
        app_desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_box.addWidget(app_desc)
        card_layout.addLayout(brand_box)

        # Divider
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFixedHeight(1)
        sep.setStyleSheet("background-color: #E2E8F0; border: none;")
        card_layout.addWidget(sep)

        # Heading
        heading_box = QVBoxLayout()
        heading_box.setSpacing(4)
        heading_title = QLabel("Operator Access")
        heading_title.setObjectName("loginSectionTitle")
        heading_sub = QLabel("Sign in to continue, or register a new operator account.")
        heading_sub.setObjectName("helperText")
        heading_sub.setWordWrap(True)
        heading_box.addWidget(heading_title)
        heading_box.addWidget(heading_sub)
        card_layout.addLayout(heading_box)

        # Tabs
        self.tab_widget = QTabWidget()
        self.tab_widget.tabBar().setExpanding(True)
        self.tab_widget.setStyleSheet(
            """
            QTabWidget::pane {
                border: 1px solid #E2E8F0;
                border-radius: 10px;
                background-color: #FFFFFF;
                top: -1px;
            }
            QTabBar::tab {
                background: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-bottom: none;
                padding: 10px 12px;
                font-weight: 600;
                color: #64748B;
                font-size: 13px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
                margin-right: 2px;
            }
            QTabBar::tab:selected {
                background: #FFFFFF;
                color: #2563EB;
                border-bottom: 2px solid #2563EB;
            }
            QTabBar::tab:hover:!selected {
                background: #F1F5F9;
                color: #334155;
            }
            """
        )

        # --- Login tab ---
        login_tab = QWidget()
        l_layout = QVBoxLayout(login_tab)
        l_layout.setContentsMargins(20, 20, 20, 20)
        l_layout.setSpacing(14)

        self.login_user_input = QLineEdit()
        self._style_input(self.login_user_input, "Enter callsign (e.g. operator)")
        self.login_user_input.returnPressed.connect(lambda: self.login_pwd_input.setFocus())
        l_layout.addWidget(self._create_form_group("Operator Callsign / Username", self.login_user_input))

        self.login_pwd_input = PasswordLineEdit(self, placeholder="Enter station password")
        self.login_pwd_input.setStyleSheet(self.login_user_input.styleSheet())
        self.login_pwd_input.returnPressed.connect(self._handle_login)
        l_layout.addWidget(self._create_form_group("Station Access Password", self.login_pwd_input))

        l_layout.addSpacing(4)

        self.btn_login = QPushButton("Sign In to Ground Station")
        self.btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_login.setMinimumHeight(44)
        self.btn_login.setStyleSheet(
            """
            QPushButton {
                background-color: #2563EB;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #1D4ED8; }
            QPushButton:pressed { background-color: #1E40AF; }
            """
        )
        self.btn_login.clicked.connect(self._handle_login)
        l_layout.addWidget(self.btn_login)
        l_layout.addStretch(1)

        self.tab_widget.addTab(login_tab, "Sign In")

        # --- Register tab ---
        reg_tab = QWidget()
        r_layout = QVBoxLayout(reg_tab)
        r_layout.setContentsMargins(20, 18, 20, 18)
        r_layout.setSpacing(12)

        self.reg_fullname_input = QLineEdit()
        self._style_input(self.reg_fullname_input, "e.g. Alex Pratama, S.T.")
        self.reg_fullname_input.returnPressed.connect(lambda: self.reg_user_input.setFocus())
        r_layout.addWidget(self._create_form_group("Full Name", self.reg_fullname_input))

        self.reg_user_input = QLineEdit()
        self._style_input(self.reg_user_input, "e.g. apratama")
        self.reg_user_input.returnPressed.connect(lambda: self.reg_pwd_input.setFocus())
        r_layout.addWidget(self._create_form_group("Operator Callsign / Username", self.reg_user_input))

        self.reg_role_combo = QComboBox()
        self.reg_role_combo.addItems([
            "Observation Specialist",
            "Geospatial Telemetry Analyst",
            "Orbital Flight Controller",
            "Ground Station Supervisor",
        ])
        self.reg_role_combo.setMinimumHeight(44)
        self.reg_role_combo.setStyleSheet(
            """
            QComboBox {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 13px;
                color: #1E293B;
            }
            QComboBox:hover { border-color: #94A3B8; }
            QComboBox:focus { border: 1px solid #2563EB; }
            QComboBox::drop-down { border: none; width: 24px; }
            QComboBox QAbstractItemView {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                selection-background-color: #EFF6FF;
                selection-color: #2563EB;
            }
            """
        )
        r_layout.addWidget(self._create_form_group("Assigned Mission Role", self.reg_role_combo))

        self.reg_pwd_input = PasswordLineEdit(self, placeholder="Minimum 4 characters")
        self.reg_pwd_input.setStyleSheet(self.login_user_input.styleSheet())
        self.reg_pwd_input.returnPressed.connect(self._handle_register)
        r_layout.addWidget(self._create_form_group("Access Password", self.reg_pwd_input, "Use at least 4 characters."))

        r_layout.addSpacing(2)

        self.btn_register = QPushButton("Register Operator Account")
        self.btn_register.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_register.setMinimumHeight(44)
        self.btn_register.setStyleSheet(
            """
            QPushButton {
                background-color: #0F172A;
                color: #FFFFFF;
                border: none;
                border-radius: 8px;
                font-weight: 600;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #1E293B; }
            QPushButton:pressed { background-color: #334155; }
            """
        )
        self.btn_register.clicked.connect(self._handle_register)
        r_layout.addWidget(self.btn_register)
        r_layout.addStretch(1)

        self.tab_widget.addTab(reg_tab, "Register")

        card_layout.addWidget(self.tab_widget)

        footer = QLabel("Sadap Aerospace Telemetry Network · Authorized Operators Only")
        footer.setObjectName("helperText")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(footer)

        center_row.addWidget(self.card)
        center_row.addStretch(1)

        main_layout.addLayout(center_row)
        main_layout.addStretch(1)

    def _handle_login(self):
        username = self.login_user_input.text().strip()
        password = self.login_pwd_input.text().strip()

        if not username or not password:
            QMessageBox.warning(self, "Peringatan", "Username dan password tidak boleh kosong.")
            return

        ok, user_data, msg = self.db.authenticate_operator(username, password)
        if ok and user_data:
            self.authenticated_operator = user_data
            logger.info(f"Operator '{username}' logged in successfully.")
            self.login_successful.emit(user_data)
            self.close()
        else:
            QMessageBox.critical(self, "Login Failed", msg)

    def _handle_register(self):
        fullname = self.reg_fullname_input.text().strip()
        username = self.reg_user_input.text().strip()
        role = self.reg_role_combo.currentText()
        password = self.reg_pwd_input.text().strip()

        if not fullname:
            QMessageBox.warning(self, "Peringatan", "Silakan masukkan nama lengkap.")
            return

        if not username or not password:
            QMessageBox.warning(self, "Peringatan", "Username dan password tidak boleh kosong.")
            return

        ok, msg = self.db.register_operator(username, password, full_name=fullname, role=role)
        if ok:
            QMessageBox.information(self, "Pendaftaran Berhasil", f"{msg}\nSilakan login menggunakan akun baru Anda.")
            self.login_user_input.setText(username.lower())
            self.login_pwd_input.setText(password)
            self.tab_widget.setCurrentIndex(0)
        else:
            QMessageBox.warning(self, "Pendaftaran Gagal", msg)
