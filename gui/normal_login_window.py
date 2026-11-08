"""
Sadap GroundStation - Normal Operator Login & Registration Portal (Clean Fullscreen)
A minimalist, high-end aerospace login workstation in fullscreen.
Features a clean tech background, central satellite emblem, and sleek form tabs
without distracting telemetry widgets.
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
from PyQt6.QtCore import Qt, pyqtSignal, QPointF
from PyQt6.QtGui import (
    QKeySequence,
    QShortcut,
    QPainter,
    QColor,
    QPen,
    QLinearGradient,
    QRadialGradient,
)

from core.database.db_manager import get_vault_db
from gui.components.password_line_edit import PasswordLineEdit
from core.utils.logger import get_logger

logger = get_logger("NormalLogin")


class AerospaceBackgroundWidget(QWidget):
    """Clean aerospace canvas with subtle tech dot-grid and ambient center glow."""

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()

        # 1. Base Slate Gradient
        grad = QLinearGradient(0, 0, w, h)
        grad.setColorAt(0.0, QColor("#F8FAFC"))
        grad.setColorAt(0.5, QColor("#F1F5F9"))
        grad.setColorAt(1.0, QColor("#E2E8F0"))
        painter.fillRect(0, 0, w, h, grad)

        # 2. Subtle Tech Dot Grid Pattern
        dot_pen = QPen(QColor(148, 163, 184, 45))
        dot_pen.setWidth(2)
        painter.setPen(dot_pen)
        grid_step = 36
        for x in range(0, w, grid_step):
            for y in range(0, h, grid_step):
                painter.drawPoint(x, y)

        # 3. Soft Ambient Orbital Radial Glow behind center
        center_x, center_y = w / 2.0, h / 2.0
        glow_radius = min(w, h) * 0.55
        glow = QRadialGradient(center_x, center_y, glow_radius)
        glow.setColorAt(0.0, QColor(2, 132, 199, 28))   # Cyan/Sky blue tint
        glow.setColorAt(0.7, QColor(2, 132, 199, 8))
        glow.setColorAt(1.0, QColor(2, 132, 199, 0))
        painter.fillRect(0, 0, w, h, glow)

        painter.end()


class NormalLoginWindow(QMainWindow):
    """Clean, minimalist fullscreen login workstation for ground station operators."""

    login_successful = pyqtSignal(dict)  # emits operator_data dict

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Sadap GroundStation — Operator Access Portal")
        self.resize(1280, 800)
        self.setMinimumSize(960, 640)

        self.db = get_vault_db()
        self.authenticated_operator: dict | None = None

        self._init_ui()
        self._setup_shortcuts()

    def _setup_shortcuts(self):
        """F11 shortcut for fullscreen toggle."""
        self.f11_shortcut = QShortcut(QKeySequence("F11"), self)
        self.f11_shortcut.activated.connect(self._toggle_fullscreen)

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showMaximized()
            if hasattr(self, "btn_fullscreen"):
                self.btn_fullscreen.setText("⛶ Fullscreen (F11)")
        else:
            self.showFullScreen()
            if hasattr(self, "btn_fullscreen"):
                self.btn_fullscreen.setText("🗗 Windowed (F11)")

    def _create_form_group(self, label_text: str, widget: QWidget) -> QWidget:
        """Create a neatly aligned form field block with tight label and input."""
        group = QWidget()
        group.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(group)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)  # Jarak rapat antara label dan input

        lbl = QLabel(label_text)
        lbl.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        lbl.setStyleSheet("font-size: 12px; font-weight: 600; color: #334155; margin-left: 1px;")
        layout.addWidget(lbl)

        widget.setFixedHeight(38)  # Tinggi rapi dan konsisten
        layout.addWidget(widget)

        return group

    def _init_ui(self):
        # Fullscreen atmospheric background canvas
        bg_canvas = AerospaceBackgroundWidget(self)
        self.setCentralWidget(bg_canvas)

        # Main layout centering the login card
        main_layout = QVBoxLayout(bg_canvas)
        main_layout.setContentsMargins(20, 16, 20, 20)

        # Top utility bar (Fullscreen toggle)
        top_bar = QHBoxLayout()
        top_bar.addStretch()
        self.btn_fullscreen = QPushButton("⛶ Fullscreen (F11)")
        self.btn_fullscreen.setObjectName("secondaryBtn")
        self.btn_fullscreen.setStyleSheet(
            "padding: 5px 12px; font-size: 11px; background-color: rgba(255, 255, 255, 0.85); "
            "border: 1px solid #CBD5E1; border-radius: 6px; font-weight: 600; color: #475569;"
        )
        self.btn_fullscreen.clicked.connect(self._toggle_fullscreen)
        top_bar.addWidget(self.btn_fullscreen)
        main_layout.addLayout(top_bar)

        main_layout.addStretch()

        # Center Container (Horizontally Centered)
        center_row = QHBoxLayout()
        center_row.addStretch()

        # -------------------------------------------------------------
        # ELEVATED CLEAN LOGIN CARD
        # -------------------------------------------------------------
        self.card = QFrame()
        self.card.setObjectName("loginCard")
        self.card.setFixedWidth(460)
        self.card.setStyleSheet("""
            #loginCard {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 14px;
            }
            #loginCard QLineEdit, #loginCard QComboBox {
                background-color: #F8FAFC;
                border: 1.5px solid #CBD5E1;
                border-radius: 7px;
                padding: 6px 12px;
                font-size: 13px;
                color: #0F172A;
            }
            #loginCard QLineEdit:hover, #loginCard QComboBox:hover {
                border-color: #94A3B8;
            }
            #loginCard QLineEdit:focus, #loginCard QComboBox:focus {
                background-color: #FFFFFF;
                border: 1.5px solid #0284C7;
            }
            #loginCard QComboBox::drop-down {
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 28px;
                border-left: 1px solid #CBD5E1;
                border-top-right-radius: 7px;
                border-bottom-right-radius: 7px;
            }
            #loginCard QComboBox QAbstractItemView {
                background-color: #FFFFFF;
                border: 1px solid #CBD5E1;
                selection-background-color: #E0F2FE;
                selection-color: #0284C7;
                padding: 4px;
            }
        """)

        # Drop shadow effect for modern elevated look
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(32)
        shadow.setColor(QColor(15, 23, 42, 38))
        shadow.setOffset(0, 10)
        self.card.setGraphicsEffect(shadow)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(30, 30, 30, 26)
        card_layout.setSpacing(16)

        # 1. Station Emblem & Header
        header_box = QVBoxLayout()
        header_box.setSpacing(6)
        header_box.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Circular Logo Emblem
        logo_label = QLabel("🛰️")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setFixedSize(68, 68)
        logo_label.setStyleSheet("""
            background-color: #F0F9FF;
            border: 2px solid #38BDF8;
            border-radius: 34px;
            font-size: 30px;
        """)
        header_box.addWidget(logo_label, alignment=Qt.AlignmentFlag.AlignCenter)

        title_lbl = QLabel("SADAP GROUNDSTATION")
        title_lbl.setStyleSheet(
            "font-size: 19px; font-weight: bold; color: #0284C7; letter-spacing: 0.8px; margin-top: 4px;"
        )
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_box.addWidget(title_lbl)

        sub_lbl = QLabel("Earth Observation & Geospatial Command Console")
        sub_lbl.setStyleSheet("color: #64748B; font-size: 11px;")
        sub_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_box.addWidget(sub_lbl)

        card_layout.addLayout(header_box)

        # Separator line
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("background-color: #E2E8F0; max-height: 1px;")
        card_layout.addWidget(sep)

        # 2. Tabs: Sign In / Register
        self.tab_widget = QTabWidget()
        self.tab_widget.tabBar().setExpanding(True)
        self.tab_widget.tabBar().setDocumentMode(True)
        self.tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #E2E8F0;
                border-radius: 8px;
                background-color: #FFFFFF;
                top: -1px;
            }
            QTabBar::tab {
                background: #F8FAFC;
                border: 1px solid #CBD5E1;
                border-bottom: 1px solid #E2E8F0;
                padding: 10px 16px;
                font-weight: 600;
                color: #64748B;
                font-size: 12px;
                border-top-left-radius: 8px;
                border-top-right-radius: 8px;
            }
            QTabBar::tab:selected {
                background: #FFFFFF;
                border-bottom: 2px solid #0284C7;
                color: #0284C7;
                font-weight: bold;
            }
            QTabBar::tab:hover:!selected {
                background: #F1F5F9;
                color: #1E293B;
            }
        """)

        # -------------------------------------------------------------
        # TAB 1: OPERATOR SIGN IN
        # -------------------------------------------------------------
        login_tab = QWidget()
        l_layout = QVBoxLayout(login_tab)
        l_layout.setSpacing(14)
        l_layout.setContentsMargins(18, 20, 18, 18)

        # Field 1: Callsign / Username
        self.login_user_input = QLineEdit()
        self.login_user_input.setPlaceholderText("Enter callsign (e.g. operator)")
        self.login_user_input.returnPressed.connect(lambda: self.login_pwd_input.setFocus())
        l_layout.addWidget(self._create_form_group("Operator Callsign / Username", self.login_user_input))

        # Field 2: Password
        self.login_pwd_input = PasswordLineEdit(self, placeholder="Enter station password")
        self.login_pwd_input.returnPressed.connect(self._handle_login)
        l_layout.addWidget(self._create_form_group("Station Access Password", self.login_pwd_input))

        # Box transparan fleksibel untuk memberi jarak ke tombol login
        login_spacer = QWidget()
        login_spacer.setStyleSheet("background: transparent;")
        login_spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        login_spacer.setMinimumHeight(24)
        l_layout.addWidget(login_spacer)

        self.btn_login = QPushButton("🔑 Sign In to Ground Station")
        self.btn_login.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_login.setFixedHeight(42)
        self.btn_login.setStyleSheet("""
            QPushButton {
                background-color: #0284C7;
                color: #FFFFFF;
                border: none;
                border-radius: 7px;
                font-weight: bold;
                font-size: 13px;
                letter-spacing: 0.3px;
            }
            QPushButton:hover {
                background-color: #0369A1;
            }
            QPushButton:pressed {
                background-color: #075985;
            }
        """)
        self.btn_login.clicked.connect(self._handle_login)
        l_layout.addWidget(self.btn_login)

        self.tab_widget.addTab(login_tab, "Operator Sign In")

        # -------------------------------------------------------------
        # TAB 2: REGISTER NEW OPERATOR
        # -------------------------------------------------------------
        reg_tab = QWidget()
        r_layout = QVBoxLayout(reg_tab)
        r_layout.setSpacing(10)
        r_layout.setContentsMargins(18, 16, 18, 16)

        # Field 1: Full Name
        self.reg_fullname_input = QLineEdit()
        self.reg_fullname_input.setPlaceholderText("e.g. Alex Pratama, S.T.")
        self.reg_fullname_input.returnPressed.connect(lambda: self.reg_user_input.setFocus())
        r_layout.addWidget(self._create_form_group("Full Name", self.reg_fullname_input))

        # Field 2: Username
        self.reg_user_input = QLineEdit()
        self.reg_user_input.setPlaceholderText("e.g. apratama")
        self.reg_user_input.returnPressed.connect(lambda: self.reg_pwd_input.setFocus())
        r_layout.addWidget(self._create_form_group("Operator Callsign / Username", self.reg_user_input))

        # Field 3: Mission Role
        self.reg_role_combo = QComboBox()
        self.reg_role_combo.addItems([
            "Observation Specialist",
            "Geospatial Telemetry Analyst",
            "Orbital Flight Controller",
            "Ground Station Supervisor",
        ])
        r_layout.addWidget(self._create_form_group("Assigned Mission Role", self.reg_role_combo))

        # Field 4: Password
        self.reg_pwd_input = PasswordLineEdit(self, placeholder="Minimum 4 characters")
        self.reg_pwd_input.returnPressed.connect(self._handle_register)
        r_layout.addWidget(self._create_form_group("Access Password", self.reg_pwd_input))

        # Box transparan fleksibel untuk memberi jarak ke tombol registrasi
        reg_spacer = QWidget()
        reg_spacer.setStyleSheet("background: transparent;")
        reg_spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        reg_spacer.setMinimumHeight(14)
        r_layout.addWidget(reg_spacer)

        self.btn_register = QPushButton("📝 Register Operator Account")
        self.btn_register.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_register.setFixedHeight(40)
        self.btn_register.setStyleSheet("""
            QPushButton {
                background-color: #0F172A;
                color: #FFFFFF;
                border: none;
                border-radius: 7px;
                font-weight: bold;
                font-size: 13px;
                letter-spacing: 0.3px;
            }
            QPushButton:hover {
                background-color: #1E293B;
            }
            QPushButton:pressed {
                background-color: #334155;
            }
        """)
        self.btn_register.clicked.connect(self._handle_register)
        r_layout.addWidget(self.btn_register)

        self.tab_widget.addTab(reg_tab, "Register New Operator")

        card_layout.addWidget(self.tab_widget)

        # 3. Footer Note inside Card
        footer_note = QLabel("Sadap Aerospace Telemetry Network • Authorized Operators Only")
        footer_note.setStyleSheet("color: #94A3B8; font-size: 11px; margin-top: 4px;")
        footer_note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        card_layout.addWidget(footer_note)

        center_row.addWidget(self.card)
        center_row.addStretch()

        main_layout.addLayout(center_row)
        main_layout.addStretch()

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
            # Switch back to login tab and prefill
            self.login_user_input.setText(username.lower())
            self.login_pwd_input.setText(password)
            self.tab_widget.setCurrentIndex(0)
        else:
            QMessageBox.warning(self, "Pendaftaran Gagal", msg)
