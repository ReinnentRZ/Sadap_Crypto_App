"""
Sadap GroundStation - Main Public Cover Window (The Chameleon Story)
A dense, authentic satellite earth observation and orbital telemetry workstation.
Integrates interactive Google Maps / Satellite imagery in the Observation Target panel.
Eliminates all visible covert buttons: The 3-factor vault can ONLY be triggered via
the secret hotkey (Ctrl + Shift + S).
"""
import datetime
import random
from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QGroupBox,
    QLabel,
    QPushButton,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QProgressBar,
    QHeaderView,
    QStatusBar,
    QMessageBox,
    QSizePolicy,
)
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtCore import QTimer, Qt, pyqtSignal

from gui.components.satellite_map_widget import SatelliteMapWidget
from gui.components.google_satellite_map_widget import GoogleSatelliteMapWidget
from gui.auth_dialog import AuthDialog
from gui.secret_dashboard import SecretDashboardWindow
from core.utils.logger import get_logger

logger = get_logger("MainCoverWindow")

# Real Satellite Observation Location Presets (with GPS Coordinates for Google Maps)
SATELLITE_PRESETS = {
    "Jakarta Metropolitan & Port Zone (Indonesia)": {
        "lat": -6.2088,
        "lon": 106.8456,
        "zoom": 13,
        "coords": "-06° 12' 31\" S, 106° 50' 44\" E",
        "sensor": "Google Satellite Hybrid / High-Res Optical",
        "elevation": "8.0 m ASL",
        "cloud_cover": "12.4%"
    },
    "IKN Nusantara Capital Zone (East Kalimantan)": {
        "lat": -0.9730,
        "lon": 116.7040,
        "zoom": 14,
        "coords": "-00° 58' 22\" S, 116° 42' 15\" E",
        "sensor": "Google Satellite Hybrid / High-Res Optical",
        "elevation": "45.2 m ASL",
        "cloud_cover": "18.1%"
    },
    "Mount Krakatau & Sunda Strait (Indonesia)": {
        "lat": -6.1021,
        "lon": 105.4230,
        "zoom": 13,
        "coords": "-06° 06' 07\" S, 105° 25' 23\" E",
        "sensor": "Google Satellite Hybrid / High-Res Optical",
        "elevation": "813.0 m ASL",
        "cloud_cover": "5.6%"
    },
    "Tokyo Bay & Shinjuku District (Japan)": {
        "lat": 35.6895,
        "lon": 139.6917,
        "zoom": 14,
        "coords": "35° 41' 22\" N, 139° 41' 30\" E",
        "sensor": "Google Satellite Hybrid / High-Res Optical",
        "elevation": "40.0 m ASL",
        "cloud_cover": "2.1%"
    },
    "Mount Fuji Crater Elevation (Japan)": {
        "lat": 35.3606,
        "lon": 138.7274,
        "zoom": 14,
        "coords": "35° 21' 38\" N, 138° 43' 39\" E",
        "sensor": "Google Satellite Hybrid / High-Res Optical",
        "elevation": "3,776.0 m ASL",
        "cloud_cover": "8.9%"
    },
    "New York Harbor & Manhattan (USA)": {
        "lat": 40.7128,
        "lon": -74.0060,
        "zoom": 14,
        "coords": "40° 42' 46\" N, 74° 00' 22\" W",
        "sensor": "Google Satellite Hybrid / High-Res Optical",
        "elevation": "10.0 m ASL",
        "cloud_cover": "3.5%"
    },
    "Mecca Holy City (Saudi Arabia)": {
        "lat": 21.4225,
        "lon": 39.8262,
        "zoom": 15,
        "coords": "21° 25' 21\" N, 39° 49' 34\" E",
        "sensor": "Google Satellite Hybrid / High-Res Optical",
        "elevation": "277.0 m ASL",
        "cloud_cover": "0.0%"
    }
}

# Satellites for Tracking
SATELLITES_DATA = {
    "SADAP-SV09 (National Remote Sensing)": {"callsign": "SADAP-SV09", "alt": "542.4 km", "spd": "7.61 km/s", "freq": "2.245 GHz (S-Band)", "inc": "97.4°"},
    "ISS (ZARYA) - Space Station": {"callsign": "ISS-ALPHA", "alt": "418.2 km", "spd": "7.66 km/s", "freq": "145.80 MHz (VHF)", "inc": "51.6°"},
    "LANDSAT-9 (USGS/NASA)": {"callsign": "LANDSAT-9", "alt": "705.0 km", "spd": "7.50 km/s", "freq": "8.212 GHz (X-Band)", "inc": "98.2°"},
    "SENTINEL-2A (Copernicus ESA)": {"callsign": "SENTINEL-2A", "alt": "786.1 km", "spd": "7.45 km/s", "freq": "8.045 GHz (X-Band)", "inc": "98.5°"},
    "NOAA-20 (JPSS-1 Polar Weather)": {"callsign": "NOAA-20", "alt": "824.0 km", "spd": "7.42 km/s", "freq": "1.707 GHz (L-Band)", "inc": "98.7°"},
}


class MainCoverWindow(QMainWindow):
    """The public cover station interface."""

    sign_out_requested = pyqtSignal()

    def __init__(self, operator_data: dict | None = None):
        super().__init__()
        self.operator_data = operator_data or {
            "username": "operator",
            "full_name": "Ground Station Specialist",
            "role": "Observation Specialist"
        }

        self.setWindowTitle("Sadap GroundStation — Earth Observation & Orbit Telemetry Command v2.4")
        self.resize(1280, 820)
        self.setMinimumSize(1080, 720)

        self.secret_dashboard: SecretDashboardWindow | None = None

        self._init_ui()
        self._setup_secret_shortcut()

        # Timers
        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(1000)

        self.telemetry_stream_timer = QTimer(self)
        self.telemetry_stream_timer.timeout.connect(self._generate_live_telemetry_event)
        self.telemetry_stream_timer.start(3000)

        self._on_satellite_changed(0)

    def _init_ui(self):
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(14, 10, 14, 8)
        main_layout.setSpacing(8)

        # -----------------------------------------------------------------
        # 1. TOP HEADER & OPERATOR SESSION BAR
        # -----------------------------------------------------------------
        top_bar = QHBoxLayout()

        station_info = QVBoxLayout()
        title_lbl = QLabel("🛰️ SADAP GROUNDSTATION — EARTH OBSERVATION COMMAND CONSOLE")
        title_lbl.setStyleSheet("font-size: 15px; font-weight: bold; color: #0284C7;")
        station_info.addWidget(title_lbl)

        sub_title = QLabel("National Geospatial Research & Multi-Mission Orbit Telemetry System")
        sub_title.setStyleSheet("color: #64748B; font-size: 11px;")
        station_info.addWidget(sub_title)
        top_bar.addLayout(station_info)

        top_bar.addStretch()

        # Operator Info Badge
        op_box = QHBoxLayout()
        op_lbl = QLabel(f"👤 Operator: <b>{self.operator_data.get('full_name')}</b> ({self.operator_data.get('role')})")
        op_lbl.setStyleSheet("background-color: #F1F5F9; border: 1px solid #CBD5E1; border-radius: 4px; padding: 4px 8px; font-size: 11px;")
        op_box.addWidget(op_lbl)

        self.btn_sign_out = QPushButton("🚪 Sign Out")
        self.btn_sign_out.setObjectName("secondaryBtn")
        self.btn_sign_out.setStyleSheet("padding: 4px 10px; font-size: 11px;")
        self.btn_sign_out.clicked.connect(self._handle_sign_out)
        op_box.addWidget(self.btn_sign_out)
        top_bar.addLayout(op_box)

        self.clock_label = QLabel("UTC TIME: --:--:--")
        self.clock_label.setStyleSheet("font-family: monospace; font-size: 12px; font-weight: bold; color: #334155; padding: 4px 8px; background-color: #E2E8F0; border-radius: 4px;")
        top_bar.addWidget(self.clock_label)

        main_layout.addLayout(top_bar)

        # -----------------------------------------------------------------
        # 2. MAIN WORKSTATION BODY (LEFT: TELEMETRY 38% | RIGHT: GOOGLE MAPS 62%)
        # -----------------------------------------------------------------
        body_layout = QHBoxLayout()
        body_layout.setSpacing(10)

        # =================================================================
        # LEFT COLUMN (MAP ORBIT + SENSORS + PASS SCHEDULE)
        # =================================================================
        left_col = QVBoxLayout()
        left_col.setSpacing(8)

        # Satellite Selection Bar
        sat_select_bar = QHBoxLayout()
        sat_select_bar.addWidget(QLabel("<b>Tracked Satellite:</b>"))
        self.satellite_combo = QComboBox()
        self.satellite_combo.addItems(list(SATELLITES_DATA.keys()))
        self.satellite_combo.currentIndexChanged.connect(self._on_satellite_changed)
        sat_select_bar.addWidget(self.satellite_combo)
        left_col.addLayout(sat_select_bar)

        # Orbital Ground Track Map
        map_group = QGroupBox("Real-time Orbital Ground Track (GIS Radar)")
        map_layout = QVBoxLayout(map_group)
        map_layout.setContentsMargins(6, 8, 6, 6)
        self.map_widget = SatelliteMapWidget(self)
        self.map_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        map_layout.addWidget(self.map_widget)
        left_col.addWidget(map_group, stretch=4)

        # Telemetry & Sensor Gauges Grid
        telem_group = QGroupBox("Sub-Satellite Sensor & Power Telemetry")
        telem_layout = QGridLayout(telem_group)
        telem_layout.setContentsMargins(10, 8, 10, 8)
        telem_layout.setSpacing(6)

        self.val_altitude = QLabel("542.4 km")
        self.val_speed = QLabel("7.61 km/s")
        self.val_freq = QLabel("2.245 GHz (Locked)")
        self.val_azimuth = QLabel("142.8° (Antenna A)")
        self.val_snr = QLabel("+24.8 dB (Excellent)")
        self.val_solar = QLabel("1,420 W (100% Sun)")

        telem_layout.addWidget(QLabel("Orbit Altitude:"), 0, 0)
        telem_layout.addWidget(self.val_altitude, 0, 1)
        telem_layout.addWidget(QLabel("Ground Speed:"), 0, 2)
        telem_layout.addWidget(self.val_speed, 0, 3)

        telem_layout.addWidget(QLabel("Downlink Freq:"), 1, 0)
        telem_layout.addWidget(self.val_freq, 1, 1)
        telem_layout.addWidget(QLabel("Azimuth / Elev:"), 1, 2)
        telem_layout.addWidget(self.val_azimuth, 1, 3)

        telem_layout.addWidget(QLabel("Signal SNR:"), 2, 0)
        telem_layout.addWidget(self.val_snr, 2, 1)
        telem_layout.addWidget(QLabel("Solar Array Power:"), 2, 2)
        telem_layout.addWidget(self.val_solar, 2, 3)

        # Battery Bar
        telem_layout.addWidget(QLabel("Bus Battery Reserve:"), 3, 0)
        self.battery_bar = QProgressBar()
        self.battery_bar.setValue(94)
        self.battery_bar.setTextVisible(True)
        self.battery_bar.setFixedHeight(16)
        self.battery_bar.setStyleSheet("QProgressBar::chunk { background-color: #059669; border-radius: 3px; }")
        telem_layout.addWidget(self.battery_bar, 3, 1, 1, 3)

        left_col.addWidget(telem_group, stretch=3)

        # Pass Prediction Schedule Table
        pass_group = QGroupBox("Ground Station Pass Prediction Schedule (Next 12 Hours)")
        pass_layout = QVBoxLayout(pass_group)
        pass_layout.setContentsMargins(6, 6, 6, 6)

        self.pass_table = QTableWidget()
        self.pass_table.setColumnCount(5)
        self.pass_table.setHorizontalHeaderLabels(["Pass #", "Satellite Target", "AOS (Acquire)", "Max Elev", "Duration"])
        self.pass_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.pass_table.setMaximumHeight(180)
        self._populate_pass_schedule()
        pass_layout.addWidget(self.pass_table)
        left_col.addWidget(pass_group, stretch=3)

        body_layout.addLayout(left_col, stretch=4)

        # =================================================================
        # RIGHT COLUMN (ENLARGED GOOGLE SATELLITE MAP + COMPACT TELEMETRY)
        # =================================================================
        right_col = QVBoxLayout()
        right_col.setSpacing(8)

        # ENLARGED Interactive Google Maps & Satellite View
        map_obs_group = QGroupBox("Interactive Satellite Observation Map (Google Maps / Earth Satellite)")
        obs_layout = QVBoxLayout(map_obs_group)
        obs_layout.setContentsMargins(8, 8, 8, 6)
        obs_layout.setSpacing(6)

        # Interactive Google Maps Satellite Widget (Dominant Focus, fully interactive)
        self.google_map_widget = GoogleSatelliteMapWidget(self)
        self.google_map_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        obs_layout.addWidget(self.google_map_widget, stretch=1)

        # Operational telemetry note
        self.meta_card = QLabel(
            "<b>Controls:</b> Drag to Pan | Scroll to Zoom | Top-Right Menu to Switch Layers (Google Hybrid / Sat / ESRI / OSM)"
        )
        self.meta_card.setStyleSheet(
            "background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 4px; padding: 5px 8px; font-size: 11px; color: #475569;"
        )
        obs_layout.addWidget(self.meta_card)

        # Enlarge Google Maps panel proportion (stretch=8)
        right_col.addWidget(map_obs_group, stretch=8)

        # COMPACT Live Decoded Telemetry Event Stream (secukupnya saja)
        terminal_group = QGroupBox("Decoded Telemetry Event Stream (Live RX)")
        term_layout = QVBoxLayout(terminal_group)
        term_layout.setContentsMargins(6, 4, 6, 6)

        self.terminal_view = QTextEdit()
        self.terminal_view.setReadOnly(True)
        self.terminal_view.setStyleSheet(
            "background-color: #0F172A; color: #38BDF8; font-family: 'Consolas', 'Courier New', monospace; font-size: 11px; border-radius: 4px; padding: 4px;"
        )
        self.terminal_view.setMaximumHeight(150)  # Compact height as requested
        self._init_terminal_stream()
        term_layout.addWidget(self.terminal_view)

        right_col.addWidget(terminal_group, stretch=2)

        body_layout.addLayout(right_col, stretch=6)

        main_layout.addLayout(body_layout)

        # -----------------------------------------------------------------
        # 3. BOTTOM PURE OPERATIONAL STATUS BAR (NO VISIBLE SECRET BUTTON!)
        # -----------------------------------------------------------------
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("color: #475569; font-size: 11px; background-color: #F1F5F9;")
        self.status_bar.showMessage(
            "Station Status: OPERATIONAL (ONLINE)  |  Receivers: Primary X-Band (150 Mbps) + S-Band Uplink Locked  |  Data Stream: NOMINAL (CRC32 Verified)"
        )
        self.setStatusBar(self.status_bar)

    def _setup_secret_shortcut(self):
        """Secret hotkey trigger: Ctrl+Shift+S directly invokes the 3-Factor Gatekeeper."""
        self.secret_shortcut = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        self.secret_shortcut.activated.connect(self._trigger_secret_auth)

        # F11 Shortcut for True Fullscreen Toggle
        self.f11_shortcut = QShortcut(QKeySequence("F11"), self)
        self.f11_shortcut.activated.connect(self._toggle_fullscreen)

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showMaximized()
        else:
            self.showFullScreen()

    def _update_clock(self):
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        self.clock_label.setText(f"UTC TIME: {now_utc.strftime('%H:%M:%S')}")

    def _on_satellite_changed(self, index: int):
        sat_name = self.satellite_combo.currentText()
        data = SATELLITES_DATA.get(sat_name, {})
        if data:
            self.map_widget.set_satellite(data["callsign"], initial_angle=random.uniform(20.0, 180.0))
            self.val_altitude.setText(data["alt"])
            self.val_speed.setText(data["spd"])
            self.val_freq.setText(data["freq"])
            self.val_azimuth.setText(f"{random.randint(40, 280)}.4° (Antenna A)")
            self.val_snr.setText(f"+{random.uniform(22.0, 27.5):.1f} dB")
            self.val_solar.setText(f"{random.randint(1350, 1490)} W (Sunlit)")

    def _populate_pass_schedule(self):
        passes = [
            ("P-1042", "SADAP-SV09", "22:48:12 UTC", "72° NE", "09m 45s"),
            ("P-1043", "ISS (ZARYA)", "23:14:05 UTC", "58° WSW", "06m 12s"),
            ("P-1044", "LANDSAT-9", "00:22:40 UTC", "84° N", "11m 30s"),
            ("P-1045", "SENTINEL-2A", "01:05:18 UTC", "65° S", "10m 05s"),
        ]
        self.pass_table.setRowCount(len(passes))
        for row, p in enumerate(passes):
            for col, val in enumerate(p):
                self.pass_table.setItem(row, col, QTableWidgetItem(val))

    def _init_terminal_stream(self):
        init_lines = [
            "[SYSTEM] Ground Station Core v2.4 initialized. S-Band / X-Band phased array online.",
            "[EPHEMERIS] TLE orbit models synchronized with NORAD orbital catalog.",
            "[DOWNLINK] 2.245 GHz stream synced at 150.2 Mbps. Signal lock confirmed.",
        ]
        self.terminal_view.setPlainText("\n".join(init_lines))

    def _generate_live_telemetry_event(self):
        sat = self.satellite_combo.currentText().split()[0]
        frame_id = random.randint(10000, 99999)
        now_time = datetime.datetime.now().strftime("%H:%M:%S")

        events = [
            f"[{now_time}] [{sat}] RX-FRAME #{frame_id}: Doppler shift compensated. Telemetry CRC32 OK.",
            f"[{now_time}] [{sat}] SENSOR-TELEMETRY: Bus voltage 28.4V | Solar array 5.12A | Thermal nominal.",
            f"[{now_time}] [{sat}] DOWNLINK-STREAM: Demodulated 64-APSK packet block #{frame_id}. Signal quality 99.8%.",
            f"[{now_time}] [{sat}] ATTITUDE-CONTROL: Reaction wheels RPM nominal | Star tracker locked.",
        ]

        new_event = random.choice(events)
        self.terminal_view.append(new_event)
        lines = self.terminal_view.toPlainText().splitlines()
        if len(lines) > 40:
            self.terminal_view.setPlainText("\n".join(lines[-25:]))

    def _handle_sign_out(self):
        reply = QMessageBox.question(
            self,
            "Sign Out",
            "Are you sure you want to sign out and return to the Operator Login portal?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.close()
            self.sign_out_requested.emit()

    def _trigger_secret_auth(self):
        """Invoke the Zero-Trust 3-Factor Gatekeeper Dialog (triggered ONLY by Ctrl+Shift+S)."""
        auth_dlg = AuthDialog(self)
        if auth_dlg.exec() == AuthDialog.DialogCode.Accepted:
            callsign = auth_dlg.operator_callsign
            self.hide()
            self.secret_dashboard = SecretDashboardWindow(operator_callsign=callsign, parent=self)
            self.secret_dashboard.showMaximized()
