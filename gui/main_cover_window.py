"""
Sadap GroundStation - Main Public Cover Window (The Chameleon Story)
A dashboard-style satellite earth observation console. All NASA modules are
selectable from the sidebar. The 3-factor vault remains completely hidden and
can ONLY be triggered via Ctrl + Shift + S.
"""
import datetime

from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)

from gui.auth_dialog import AuthDialog
from gui.components.cover_sidebar import CoverSidebar
from gui.pages.cover_earth_imagery_page import CoverEarthImageryPage
from gui.pages.cover_map_page import CoverMapPage
from gui.pages.cover_neows_page import CoverNeowsPage
from gui.pages.cover_natural_events_page import CoverNaturalEventsPage
from gui.pages.cover_overview_page import CoverOverviewPage
from gui.pages.cover_space_weather_page import CoverSpaceWeatherPage
from gui.pages.cover_telemetry_page import CoverTelemetryPage
from gui.secret_dashboard import SecretDashboardWindow
from core.utils.logger import get_logger

logger = get_logger("MainCoverWindow")


PAGE_DEFS: list[tuple[str, str]] = [
    ("overview", "🏠 Overview"),
    ("map", "🗺️ Earth Observation"),
    ("events", "🌋 Natural Events"),
    ("weather", "☀️ Space Weather"),
    ("neows", "☄️ Near-Earth Objects"),
    ("imagery", "🌍 Earth Imagery"),
    ("telemetry", "🛰️ Satellite Telemetry"),
]


class MainCoverWindow(QMainWindow):
    """Public cover dashboard shell."""

    sign_out_requested = pyqtSignal()

    def __init__(self, operator_data: dict | None = None):
        super().__init__()
        self.operator_data = operator_data or {
            "username": "operator",
            "full_name": "Ground Station Specialist",
            "role": "Observation Specialist",
        }

        self.setWindowTitle("Sadap GroundStation — Earth Observation & Orbit Telemetry Command v2.4")
        self.resize(1280, 820)
        self.setMinimumSize(1080, 720)

        self.secret_dashboard: SecretDashboardWindow | None = None
        self._pages: dict[str, QWidget] = {}

        self._init_ui()
        self._setup_secret_shortcut()

        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._update_clock)
        self.clock_timer.start(1000)

        self.telemetry_stream_timer = QTimer(self)
        self.telemetry_stream_timer.timeout.connect(self._generate_live_telemetry_event)
        self.telemetry_stream_timer.start(3000)

        self._update_clock()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------
    def _init_ui(self) -> None:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(14, 10, 14, 8)
        main_layout.setSpacing(8)

        # Top header & operator session bar (fullscreen button intentionally removed)
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

        op_box = QHBoxLayout()
        op_lbl = QLabel(
            f"👤 Operator: <b>{self.operator_data.get('full_name')}</b> "
            f"({self.operator_data.get('role')})"
        )
        op_lbl.setStyleSheet(
            "background-color: #F1F5F9; border: 1px solid #CBD5E1; border-radius: 4px; "
            "padding: 4px 8px; font-size: 11px;"
        )
        op_box.addWidget(op_lbl)

        self.btn_sign_out = QPushButton("🚪 Sign Out")
        self.btn_sign_out.setObjectName("secondaryBtn")
        self.btn_sign_out.setStyleSheet("padding: 4px 10px; font-size: 11px;")
        self.btn_sign_out.clicked.connect(self._handle_sign_out)
        op_box.addWidget(self.btn_sign_out)
        top_bar.addLayout(op_box)

        self.clock_label = QLabel("UTC TIME: --:--:--")
        self.clock_label.setStyleSheet(
            "font-family: monospace; font-size: 12px; font-weight: bold; color: #334155; "
            "padding: 4px 8px; background-color: #E2E8F0; border-radius: 4px;"
        )
        top_bar.addWidget(self.clock_label)
        main_layout.addLayout(top_bar)

        # Dashboard body: sidebar + stacked pages
        body = QHBoxLayout()
        body.setSpacing(10)

        self.sidebar = CoverSidebar(PAGE_DEFS)
        body.addWidget(self.sidebar)

        self.stacked = QStackedWidget()
        self.stacked.setStyleSheet("QStackedWidget { background: #F8FAFC; border-radius: 8px; }")
        body.addWidget(self.stacked, stretch=1)

        self.overview_page = CoverOverviewPage()
        self.map_page = CoverMapPage()
        self.events_page = CoverNaturalEventsPage()
        self.weather_page = CoverSpaceWeatherPage()
        self.neows_page = CoverNeowsPage()
        self.imagery_page = CoverEarthImageryPage()
        self.telemetry_page = CoverTelemetryPage()

        self._pages = {
            "overview": self.overview_page,
            "map": self.map_page,
            "events": self.events_page,
            "weather": self.weather_page,
            "neows": self.neows_page,
            "imagery": self.imagery_page,
            "telemetry": self.telemetry_page,
        }
        for page in self._pages.values():
            self.stacked.addWidget(page)

        self.sidebar.page_selected.connect(self.show_page)
        self.overview_page.quick_jump.connect(self.show_page)
        self.events_page.locate_requested.connect(self._locate_on_map)
        self.events_page.metrics_ready.connect(self._update_overview_metrics)
        self.weather_page.metrics_ready.connect(self._update_overview_metrics)
        self.neows_page.metrics_ready.connect(self._update_overview_metrics)

        main_layout.addLayout(body, stretch=1)

        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("color: #475569; font-size: 11px; background-color: #F1F5F9;")
        self.setStatusBar(self.status_bar)
        self.show_page("overview")

    # ------------------------------------------------------------------
    # Navigation
    # ------------------------------------------------------------------
    def show_page(self, key: str) -> None:
        page = self._pages.get(key)
        if page is None:
            return
        self.stacked.setCurrentWidget(page)
        self.sidebar.select(key)

        labels = dict(PAGE_DEFS)
        self.status_bar.showMessage(
            "Station Status: OPERATIONAL (ONLINE)  |  "
            f"Active View: {labels.get(key, key)}  |  "
            "Receivers: Primary X-Band (150 Mbps) + S-Band Uplink Locked  |  "
            "Data Stream: NOMINAL (CRC32 Verified)"
        )

    def _locate_on_map(self, lat: float, lon: float, zoom: int) -> None:
        self.show_page("map")
        self.map_page.fly_to_coordinates(lat, lon, zoom)
        self.status_bar.showMessage(
            f"Map target updated from NASA event: {lat:.4f}, {lon:.4f} (zoom {zoom}x)"
        )

    def _update_overview_metrics(self, metrics: dict) -> None:
        self.overview_page.set_metrics(
            neo_count=metrics.get("neo_count"),
            hazard_count=metrics.get("hazard_count"),
            event_count=metrics.get("event_count"),
            alert_count=metrics.get("alert_count"),
            source="NASA Open APIs (NeoWs / DONKI / EONET)",
            updated=metrics.get("updated", "—"),
        )

    # ------------------------------------------------------------------
    # Hidden access & window controls
    # ------------------------------------------------------------------
    def _setup_secret_shortcut(self) -> None:
        """Secret hotkey trigger: Ctrl+Shift+S directly invokes the 3-Factor Gatekeeper."""
        self.secret_shortcut = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        self.secret_shortcut.activated.connect(self._trigger_secret_auth)

        # F11 remains active even though the visible button was removed.
        self.f11_shortcut = QShortcut(QKeySequence("F11"), self)
        self.f11_shortcut.activated.connect(self._toggle_fullscreen)

    def _toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showMaximized()
        else:
            self.showFullScreen()

    def _update_clock(self) -> None:
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        self.clock_label.setText(f"UTC TIME: {now_utc.strftime('%H:%M:%S')}")

    def _generate_live_telemetry_event(self) -> None:
        self.telemetry_page.append_telemetry_event()

    def _handle_sign_out(self) -> None:
        reply = QMessageBox.question(
            self,
            "Sign Out",
            "Are you sure you want to sign out and return to the Operator Login portal?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.close()
            self.sign_out_requested.emit()

    def _trigger_secret_auth(self) -> None:
        """Invoke the Zero-Trust 3-Factor Gatekeeper Dialog (triggered ONLY by Ctrl+Shift+S)."""
        auth_dlg = AuthDialog(self)
        if auth_dlg.exec() == AuthDialog.DialogCode.Accepted:
            callsign = auth_dlg.operator_callsign
            self.hide()
            self.secret_dashboard = SecretDashboardWindow(operator_callsign=callsign, parent=self)
            self.secret_dashboard.showMaximized()
