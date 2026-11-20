"""
Sadap GroundStation - Main Public Cover Window (Dashboard Shell)
"""
import datetime

from PyQt6.QtCore import QTimer, pyqtSignal, Qt
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QFrame,
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
from gui.pages.cover_weather_forecast_page import CoverWeatherForecastPage
from gui.secret_dashboard import SecretDashboardWindow
from core.utils.logger import get_logger

logger = get_logger("MainCoverWindow")


PAGE_DEFS: list[tuple[str, str]] = [
    ("overview", "📊  Overview"),
    ("map", "🗺️  Earth Observation"),
    ("forecast", "🌤️  Weather Forecast"),
    ("events", "🌍  Natural Events"),
    ("weather", "☀️  Space Weather"),
    ("neows", "☄️  Near-Earth Objects"),
    ("imagery", "🛰️  Earth Imagery"),
    ("telemetry", "📡  Satellite Telemetry"),
]


class MainCoverWindow(QMainWindow):
    """Public cover dashboard shell with modern light layout."""

    sign_out_requested = pyqtSignal()

    def __init__(self, operator_data: dict | None = None):
        super().__init__()
        self.operator_data = operator_data or {
            "username": "operator",
            "full_name": "Ground Station Specialist",
            "role": "Observation Specialist",
        }

        self.setWindowTitle("Sadap GroundStation - Earth Observation Command Console v2.4")
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

    def _init_ui(self) -> None:
        central_widget = QWidget(self)
        central_widget.setStyleSheet("background-color: #F8FAFC;")
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(16, 16, 16, 12)
        main_layout.setSpacing(12)

        # Top header
        header_frame = QFrame()
        header_frame.setObjectName("statusCard")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(20, 16, 20, 16)
        header_layout.setSpacing(12)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        self.page_title_label = QLabel("Overview")
        self.page_title_label.setObjectName("pageTitle")
        self.page_subtitle_label = QLabel("Mission summary and quick access to observation modules.")
        self.page_subtitle_label.setObjectName("pageSubtitle")
        self.page_subtitle_label.setWordWrap(True)
        title_box.addWidget(self.page_title_label)
        title_box.addWidget(self.page_subtitle_label)
        header_layout.addLayout(title_box, stretch=1)

        right_box = QHBoxLayout()
        right_box.setSpacing(8)
        right_box.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        user_text = (
            f"<b>{self.operator_data.get('full_name', 'Operator')}</b><br>"
            f"<span style='color:#64748B; font-size:11px;'>{self.operator_data.get('role', 'Operator')}</span>"
        )
        self.user_chip = QLabel(user_text)
        self.user_chip.setObjectName("userChip")
        self.user_chip.setTextFormat(Qt.TextFormat.RichText)
        right_box.addWidget(self.user_chip)

        self.clock_label = QLabel("UTC --:--:--")
        self.clock_label.setStyleSheet(
            "font-family: 'Consolas', 'Segoe UI', monospace; font-size: 12px; font-weight: 600; "
            "color: #334155; padding: 8px 10px; background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 8px;"
        )
        right_box.addWidget(self.clock_label)

        self.btn_sign_out = QPushButton("Sign Out")
        self.btn_sign_out.setObjectName("secondaryBtn")
        self.btn_sign_out.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_sign_out.setMinimumHeight(36)
        self.btn_sign_out.clicked.connect(self._handle_sign_out)
        right_box.addWidget(self.btn_sign_out)

        header_layout.addLayout(right_box)
        main_layout.addWidget(header_frame)

        # Body
        body = QHBoxLayout()
        body.setSpacing(12)

        self.sidebar = CoverSidebar(PAGE_DEFS)
        body.addWidget(self.sidebar)

        content_frame = QFrame()
        content_frame.setStyleSheet("QFrame { background: transparent; border: none; }")
        content_layout = QVBoxLayout(content_frame)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)

        self.stacked = QStackedWidget()
        self.stacked.setStyleSheet("QStackedWidget { background: transparent; }")
        content_layout.addWidget(self.stacked)
        body.addWidget(content_frame, stretch=1)

        self.overview_page = CoverOverviewPage()
        self.map_page = CoverMapPage()
        self.forecast_page = CoverWeatherForecastPage()
        self.events_page = CoverNaturalEventsPage()
        self.weather_page = CoverSpaceWeatherPage()
        self.neows_page = CoverNeowsPage()
        self.imagery_page = CoverEarthImageryPage()
        self.telemetry_page = CoverTelemetryPage()

        self._pages = {
            "overview": self.overview_page,
            "map": self.map_page,
            "forecast": self.forecast_page,
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
        self.forecast_page.use_map_target_requested.connect(self._apply_map_target_to_forecast)
        self.events_page.locate_requested.connect(self._locate_on_map)
        self.events_page.metrics_ready.connect(self._update_overview_metrics)
        self.weather_page.metrics_ready.connect(self._update_overview_metrics)
        self.neows_page.metrics_ready.connect(self._update_overview_metrics)

        main_layout.addLayout(body, stretch=1)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.show_page("overview")

    def show_page(self, key: str) -> None:
        page = self._pages.get(key)
        if page is None:
            return
        self.stacked.setCurrentWidget(page)
        self.sidebar.select(key)

        labels = dict(PAGE_DEFS)
        subtitles = {
            "overview": "Mission summary and quick access to observation modules.",
            "map": "Interactive satellite map and target observation controls.",
            "forecast": "Global weather forecast powered by Open-Meteo.",
            "events": "Active natural events tracked by NASA EONET.",
            "weather": "Space weather notifications from NASA DONKI.",
            "neows": "Near-Earth object feed and hazard overview.",
            "imagery": "EPIC Earth imagery and Astronomy Picture of the Day.",
            "telemetry": "Orbital tracking, pass schedule, and live RX telemetry.",
        }
        label = labels.get(key, key)
        self.page_title_label.setText(label.split("  ", 1)[-1] if "  " in label else label)
        self.page_subtitle_label.setText(subtitles.get(key, ""))
        self.status_bar.showMessage(
            f"Station: Operational  •  Active View: {self.page_title_label.text()}  •  Data links nominal"
        )

    def _locate_on_map(self, lat: float, lon: float, zoom: int) -> None:
        self.show_page("map")
        self.map_page.fly_to_coordinates(lat, lon, zoom)
        self.status_bar.showMessage(f"Map target updated from NASA event: {lat:.4f}, {lon:.4f} (zoom {zoom}x)")

    def _apply_map_target_to_forecast(self) -> None:
        def _apply(target):
            if not target:
                return
            lat, lon, label = target
            self.forecast_page.apply_map_target(lat, lon, label)
            self.status_bar.showMessage(f"Forecast location synced from map: {label} ({lat:.4f}, {lon:.4f})")

        self.map_page.get_current_target(_apply)

    def _update_overview_metrics(self, metrics: dict) -> None:
        self.overview_page.set_metrics(
            neo_count=metrics.get("neo_count"),
            hazard_count=metrics.get("hazard_count"),
            event_count=metrics.get("event_count"),
            alert_count=metrics.get("alert_count"),
            source="NASA Open APIs (NeoWs / DONKI / EONET)",
            updated=metrics.get("updated", "—"),
        )

    def _setup_secret_shortcut(self) -> None:
        self.secret_shortcut = QShortcut(QKeySequence("Ctrl+Shift+S"), self)
        self.secret_shortcut.activated.connect(self._trigger_secret_auth)

        self.f11_shortcut = QShortcut(QKeySequence("F11"), self)
        self.f11_shortcut.activated.connect(self._toggle_fullscreen)

    def _toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showMaximized()
        else:
            self.showFullScreen()

    def _update_clock(self) -> None:
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        self.clock_label.setText(f"UTC {now_utc.strftime('%H:%M:%S')}")

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
        auth_dlg = AuthDialog(self)
        if auth_dlg.exec() == AuthDialog.DialogCode.Accepted:
            callsign = auth_dlg.operator_callsign
            self.hide()
            self.secret_dashboard = SecretDashboardWindow(
                operator_callsign=callsign,
                dongle_payload=auth_dlg.dongle_payload,
                parent=self,
            )
            self.secret_dashboard.showMaximized()
