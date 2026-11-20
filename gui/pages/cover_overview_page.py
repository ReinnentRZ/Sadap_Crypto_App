"""Default landing page of the public cover dashboard."""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class MetricCard(QFrame):
    """KPI card with accent strip and clear value hierarchy."""

    def __init__(self, title: str, accent: str, parent=None):
        super().__init__(parent)
        self.setObjectName("metricCard")
        self.setMinimumHeight(132)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        accent_bar = QWidget()
        accent_bar.setFixedHeight(4)
        accent_bar.setStyleSheet(
            f"background-color: {accent}; border-top-left-radius: 12px; border-top-right-radius: 12px;"
        )
        outer.addWidget(accent_bar)

        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(6)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(
            "color: #64748B; font-size: 11px; font-weight: 700; letter-spacing: 0.5px;"
        )

        self.value_label = QLabel("—")
        self.value_label.setStyleSheet(f"color: {accent}; font-size: 30px; font-weight: 700;")

        self.note_label = QLabel("Menunggu sinkronisasi data")
        self.note_label.setWordWrap(True)
        self.note_label.setStyleSheet("color: #94A3B8; font-size: 12px;")

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addSpacing(2)
        layout.addWidget(self.note_label)
        layout.addStretch(1)
        outer.addWidget(body, stretch=1)

    def set_value(self, value: str, note: str) -> None:
        self.value_label.setText(value)
        self.note_label.setText(note)


class CoverOverviewPage(QWidget):
    """Mission summary with quick jumps to each dashboard module."""

    quick_jump = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()

    def _init_ui(self) -> None:
        main = QVBoxLayout(self)
        main.setContentsMargins(4, 4, 4, 4)
        main.setSpacing(16)

        intro = QFrame()
        intro.setObjectName("statusCard")
        intro_layout = QVBoxLayout(intro)
        intro_layout.setContentsMargins(20, 18, 20, 18)
        intro_layout.setSpacing(4)
        intro_title = QLabel("Mission Overview")
        intro_title.setStyleSheet("font-size: 20px; font-weight: 700; color: #1E293B;")
        intro_sub = QLabel(
            "Ringkasan data NASA Open APIs, prakiraan Open-Meteo, dan status stasiun. "
            "Pilih modul di sidebar untuk analisis detail."
        )
        intro_sub.setWordWrap(True)
        intro_sub.setStyleSheet("color: #64748B; font-size: 13px;")
        intro_layout.addWidget(intro_title)
        intro_layout.addWidget(intro_sub)
        main.addWidget(intro)

        self.card_neos = MetricCard("NEAR-EARTH OBJECTS", "#2563EB")
        self.card_hazard = MetricCard("POTENTIALLY HAZARDOUS", "#DC2626")
        self.card_events = MetricCard("ACTIVE NATURAL EVENTS", "#16A34A")
        self.card_alerts = MetricCard("SPACE WEATHER NOTICES", "#D97706")

        cards = QGridLayout()
        cards.setSpacing(12)
        cards.addWidget(self.card_neos, 0, 0)
        cards.addWidget(self.card_hazard, 0, 1)
        cards.addWidget(self.card_events, 1, 0)
        cards.addWidget(self.card_alerts, 1, 1)
        main.addLayout(cards)

        status_frame = QFrame()
        status_frame.setObjectName("statusCard")
        status_layout = QVBoxLayout(status_frame)
        status_layout.setContentsMargins(20, 16, 20, 16)
        status_layout.setSpacing(6)

        status_title = QLabel("Data Link Status")
        status_title.setStyleSheet("color: #1E293B; font-size: 16px; font-weight: 600;")
        self.status_label = QLabel("NASA API: siap digunakan. Buka modul untuk memuat data.")
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("color: #475569; font-size: 13px;")
        self.updated_label = QLabel("Terakhir disinkronisasi: —")
        self.updated_label.setStyleSheet("color: #94A3B8; font-size: 12px;")
        status_layout.addWidget(status_title)
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.updated_label)
        main.addWidget(status_frame)

        quick_frame = QFrame()
        quick_frame.setObjectName("statusCard")
        quick_layout_outer = QVBoxLayout(quick_frame)
        quick_layout_outer.setContentsMargins(20, 16, 20, 16)
        quick_layout_outer.setSpacing(10)
        quick_title = QLabel("Quick Access")
        quick_title.setStyleSheet("color: #1E293B; font-size: 16px; font-weight: 600;")
        quick_layout_outer.addWidget(quick_title)

        quick_grid = QGridLayout()
        quick_grid.setHorizontalSpacing(10)
        quick_grid.setVerticalSpacing(10)
        self._quick_buttons = [
            ("🗺️  Earth Observation", "map"),
            ("🌤️  Weather Forecast", "forecast"),
            ("🌍  Natural Events", "events"),
            ("☀️  Space Weather", "weather"),
            ("☄️  NEO Feed", "neows"),
            ("🛰️  Earth Imagery", "imagery"),
        ]
        for i, (label, key) in enumerate(self._quick_buttons):
            button = QPushButton(label)
            button.setObjectName("secondaryBtn")
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            button.setMinimumHeight(40)
            button.clicked.connect(lambda _checked=False, k=key: self.quick_jump.emit(k))
            quick_grid.addWidget(button, i // 3, i % 3)
        quick_layout_outer.addLayout(quick_grid)
        main.addWidget(quick_frame)
        main.addStretch(1)

    def set_metrics(
        self,
        *,
        neo_count: int | None,
        hazard_count: int | None,
        event_count: int | None,
        alert_count: int | None,
        source: str = "NASA Open APIs",
        updated: str = "—",
    ) -> None:
        if neo_count is not None:
            self.card_neos.set_value(str(neo_count), "objek dalam rentang tanggal")
        if hazard_count is not None:
            self.card_hazard.set_value(
                str(hazard_count),
                "berpotensi berbahaya" if hazard_count else "tidak ada ancaman terdeteksi",
            )
        if event_count is not None:
            self.card_events.set_value(str(event_count), "kejadian alam aktif (EONET)")
        if alert_count is not None:
            self.card_alerts.set_value(str(alert_count), "notifikasi cuaca antariksa (DONKI)")
        self.status_label.setText(f"Sumber data aktif: {source}")
        self.updated_label.setText(f"Terakhir disinkronisasi: {updated}")
