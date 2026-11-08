"""
AeroSat GroundStation - Main Public Cover Window (The Chameleon Story)
Acts as a legitimate, functional satellite observation and orbital telemetry console.
Hides the covert crypto suite behind a plausible deniability gatekeeper.
"""
import datetime
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QStatusBar,
    QMessageBox,
)
from PyQt6.QtGui import QPixmap, QKeySequence, QShortcut
from PyQt6.QtCore import QTimer, Qt

from config.settings import SAMPLE_IMAGES_DIR
from gui.components.satellite_map_widget import SatelliteMapWidget
from gui.auth_dialog import AuthDialog
from gui.secret_dashboard import SecretDashboardWindow
from core.utils.logger import get_logger

logger = get_logger("MainCoverWindow")


class MainCoverWindow(QMainWindow):
    """The public cover station interface."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("AeroSat GroundStation — Earth Observation & Orbit Telemetry Console v2.4")
        self.resize(1080, 720)
        self.setMinimumSize(960, 640)

        self.sample_img_path = SAMPLE_IMAGES_DIR / "satellite_base.png"
        self.secret_dashboard: SecretDashboardWindow | None = None

        self._init_ui()
        self._setup_secret_shortcut()

        # Telemetry clock timer
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_clock_and_telemetry)
        self.clock_timer.start(1000)

    def _init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(14)

        # 1. Top Station Banner
        top_bar = QHBoxLayout()

        station_info = QVBoxLayout()
        title_lbl = QLabel("🛰️ AEROSAT GROUND STATION — CONSOLE SV-09")
        title_lbl.setStyleSheet("font-size: 16px; font-weight: bold; color: #0284C7;")
        station_info.addWidget(title_lbl)

        sub_title = QLabel("Global Earth Observation System | Copernicus & NOAA Telemetry Feed")
        sub_title.setStyleSheet("color: #64748B; font-size: 11px;")
        station_info.addWidget(sub_title)
        top_bar.addLayout(station_info)

        top_bar.addStretch()

        self.clock_label = QLabel("UTC TIME: --:--:--")
        self.clock_label.setStyleSheet("font-family: monospace; font-size: 13px; font-weight: bold; color: #334155; padding: 6px; background-color: #E2E8F0; border-radius: 4px;")
        top_bar.addWidget(self.clock_label)

        main_layout.addLayout(top_bar)

        # 2. Main Workstation Body (Split Layout)
        body_layout = QHBoxLayout()
        body_layout.setSpacing(14)

        # LEFT COLUMN: ORBITAL MAP & SATELLITE TELEMETRY
        left_col = QVBoxLayout()
        left_col.setSpacing(10)

        map_group = QGroupBox("Orbital Ground Track (Real-time GIS Radar)")
        map_layout = QVBoxLayout(map_group)
        self.map_widget = SatelliteMapWidget(self)
        map_layout.addWidget(self.map_widget)
        left_col.addWidget(map_group)

        # Telemetry Metrics Grid
        telem_group = QGroupBox("Sub-Satellite Sensor Telemetry")
        telem_layout = QVBoxLayout(telem_group)

        row1 = QHBoxLayout()
        row1.addWidget(QLabel("<b>Orbit Altitude:</b> 542.4 km"))
        row1.addWidget(QLabel("<b>Ground Velocity:</b> 7.61 km/s"))
        telem_layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("<b>Antenna Azimuth:</b> 142.8°"))
        row2.addWidget(QLabel("<b>Downlink Signal:</b> 98.4% SNR"))
        telem_layout.addLayout(row2)

        row3 = QHBoxLayout()
        row3.addWidget(QLabel("<b>S-Band Transponder:</b> 2.24 GHz (Locked)"))
        row3.addWidget(QLabel("<b>Station Pass:</b> 11m 42s Remaining"))
        telem_layout.addLayout(row3)

        left_col.addWidget(telem_group)
        body_layout.addLayout(left_col, stretch=1)

        # RIGHT COLUMN: SATELLITE IMAGERY VIEWER
        right_col = QVBoxLayout()
        right_col.setSpacing(10)

        img_group = QGroupBox("Earth Surface Imagery (Multi-Spectral Raster)")
        img_layout = QVBoxLayout(img_group)

        # Imagery View Label
        self.sat_image_display = QLabel("Loading satellite raster...")
        self.sat_image_display.setFixedSize(480, 320)
        self.sat_image_display.setStyleSheet("background-color: #0F172A; border: 1px solid #CBD5E1; border-radius: 6px;")
        self.sat_image_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img_layout.addWidget(self.sat_image_display, alignment=Qt.AlignmentFlag.AlignCenter)

        # Band Filters
        bands_layout = QHBoxLayout()
        btn_true_color = QPushButton("RGB Natural")
        btn_true_color.clicked.connect(lambda: self._set_channel_badge("RGB Natural Color"))
        bands_layout.addWidget(btn_true_color)

        btn_infrared = QPushButton("Thermal IR")
        btn_infrared.setObjectName("secondaryBtn")
        btn_infrared.clicked.connect(lambda: self._set_channel_badge("Thermal Infrared (Band 8)"))
        bands_layout.addWidget(btn_infrared)

        btn_ndvi = QPushButton("NDVI Index")
        btn_ndvi.setObjectName("secondaryBtn")
        btn_ndvi.clicked.connect(lambda: self._set_channel_badge("Normalized Difference Vegetation Index"))
        bands_layout.addWidget(btn_ndvi)
        img_layout.addLayout(bands_layout)

        self.channel_badge = QLabel("Active Channel: RGB Natural Color | Sensor: OLI-2 Multispectral")
        self.channel_badge.setStyleSheet("color: #64748B; font-size: 11px;")
        img_layout.addWidget(self.channel_badge)

        right_col.addWidget(img_group)
        body_layout.addLayout(right_col, stretch=1)

        main_layout.addLayout(body_layout)

        # 3. Bottom Status Bar with Subtle Secret Trigger
        bottom_bar = QHBoxLayout()
        status_info = QLabel("Station Status: ONLINE | Uplink Channel: STANDBY | Data Integrity: NOMINAL")
        status_info.setStyleSheet("color: #475569; font-size: 12px;")
        bottom_bar.addWidget(status_info)

        bottom_bar.addStretch()

        # The Secret Trigger Button
        self.btn_secure_uplink = QPushButton("📡 Secure Uplink (Restricted)")
        self.btn_secure_uplink.setToolTip("Restricted Operator Channel (Requires Hardware USB Key & Biometric Auth)")
        self.btn_secure_uplink.setStyleSheet(
            "background-color: #F8FAFC; color: #64748B; border: 1px solid #CBD5E1; font-weight: 600; padding: 6px 12px;"
        )
        self.btn_secure_uplink.clicked.connect(self._trigger_secret_auth)
        bottom_bar.addWidget(self.btn_secure_uplink)

        main_layout.addLayout(bottom_bar)

        # Load initial satellite picture
        self._load_sample_sat_image()
        self._update_clock_and_telemetry()

    def _setup_secret_shortcut(self):
        """Hidden hotkey trigger: Ctrl+Shift+S directly invokes the gatekeeper."""
        self.secret_shortcut = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        self.secret_shortcut.activated.connect(self._trigger_secret_auth)

    def _load_sample_sat_image(self):
        if self.sample_img_path.exists():
            pix = QPixmap(str(self.sample_img_path))
            if not pix.isNull():
                self.sat_image_display.setPixmap(
                    pix.scaled(
                        self.sat_image_display.width(),
                        self.sat_image_display.height(),
                        Qt.AspectRatioMode.KeepAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                )

    def _set_channel_badge(self, name: str):
        self.channel_badge.setText(f"Active Channel: {name} | Sensor: OLI-2 Multispectral")

    def _update_clock_and_telemetry(self):
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        self.clock_label.setText(f"UTC TIME: {now_utc.strftime('%H:%M:%S')}")

    def _trigger_secret_auth(self):
        """Invoke the Zero-Trust 3-Factor Gatekeeper Dialog."""
        auth_dlg = AuthDialog(self)
        if auth_dlg.exec() == AuthDialog.DialogCode.Accepted:
            # Authorization succeeded! Open the Secret Intelligence Vault
            callsign = auth_dlg.operator_callsign
            self.hide()
            self.secret_dashboard = SecretDashboardWindow(operator_callsign=callsign, parent=self)
            self.secret_dashboard.show()
