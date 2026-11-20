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
    """KPI card with a single accent strip and no nested card borders."""

    def __init__(self, title: str, accent: str, parent=None):
        super().__init__(parent)
        # Target only this card. A bare ``QFrame {}`` selector also styles any
        # nested QFrame and stacks another border/header on top of this one.
        self.setObjectName("metricCard")
        self.setStyleSheet(
            """
            QFrame#metricCard {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
            """
        )

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        accent_bar = QWidget()
        accent_bar.setFixedHeight(4)
        accent_bar.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        accent_bar.setStyleSheet(
            f"background-color: {accent}; border-top-left-radius: 8px; border-top-right-radius: 8px;"
        )
        outer.addWidget(accent_bar)

        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(4)

        self.title_label = QLabel(title)
        self.title_label.setStyleSheet(
            "color: #64748B; font-size: 11px; font-weight: 700; letter-spacing: 0.4px;"
        )

        self.value_label = QLabel("—")
        self.value_label.setStyleSheet(f"color: {accent}; font-size: 26px; font-weight: 800;")

        self.note_label = QLabel("Menunggu sinkronisasi data")
        self.note_label.setStyleSheet("color: #94A3B8; font-size: 10px;")

        layout.addWidget(self.title_label)
        layout.addWidget(self.value_label)
        layout.addWidget(self.note_label)
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
        main.setContentsMargins(20, 18, 20, 18)
        main.setSpacing(14)

        title = QLabel("MISSION OVERVIEW")
        title.setStyleSheet("font-size: 20px; font-weight: 800; color: #0F172A;")
        subtitle = QLabel(
            "Ringkasan data NASA Open APIs, prakiraan Open-Meteo, dan status stasiun. Pilih modul di sidebar untuk analisis detail."
        )
        subtitle.setStyleSheet("color: #64748B; font-size: 12px;")
        main.addWidget(title)
        main.addWidget(subtitle)

        self.card_neos = MetricCard("NEAR-EARTH OBJECTS", "#0284C7")
        self.card_hazard = MetricCard("POTENTIALLY HAZARDOUS", "#DC2626")
        self.card_events = MetricCard("ACTIVE NATURAL EVENTS", "#059669")
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
        status_frame.setStyleSheet(
            """
            QFrame#statusCard {
                background-color: #F8FAFC;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
            """
        )
        status_layout = QVBoxLayout(status_frame)
        status_layout.setContentsMargins(14, 12, 14, 12)
        status_layout.setSpacing(4)

        status_title = QLabel("DATA LINK STATUS")
        status_title.setStyleSheet("color: #334155; font-size: 12px; font-weight: 800;")
        self.status_label = QLabel("NASA API: siap digunakan. Buka modul untuk memuat data.")
        self.status_label.setStyleSheet("color: #475569; font-size: 12px;")
        self.updated_label = QLabel("Terakhir disinkronisasi: —")
        self.updated_label.setStyleSheet("color: #94A3B8; font-size: 10px;")
        status_layout.addWidget(status_title)
        status_layout.addWidget(self.status_label)
        status_layout.addWidget(self.updated_label)
        main.addWidget(status_frame)

        quick_title = QLabel("QUICK ACCESS")
        quick_title.setStyleSheet("color: #334155; font-size: 12px; font-weight: 800; margin-top: 4px;")
        main.addWidget(quick_title)

        quick_layout = QHBoxLayout()
        quick_layout.setSpacing(8)
        self._quick_buttons = [
            ("🗺️ Earth Observation", "map"),
            ("🌤️ Weather Forecast", "forecast"),
            ("🌋 Natural Events", "events"),
            ("☀️ Space Weather", "weather"),
            ("☄️ NEO Feed", "neows"),
            ("🌍 Earth Imagery", "imagery"),
        ]
        for label, key in self._quick_buttons:
            button = QPushButton(label)
            button.setObjectName("secondaryBtn")
            button.setStyleSheet("padding: 9px 12px; font-weight: 600;")
            button.clicked.connect(lambda _checked=False, k=key: self.quick_jump.emit(k))
            quick_layout.addWidget(button)
        main.addLayout(quick_layout)
        main.addStretch()

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
        """Update KPI cards as each NASA module finishes loading."""
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
