"""EONET natural events page with map jump support."""
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import QThreadPool

from core.api.nasa_client import NasaResponse
from core.api.nasa_endpoints import EONET_EVENTS_URL
from gui.components.nasa_worker import NasaFetchWorker


class CoverNaturalEventsPage(QWidget):
    """Displays active NASA EONET events and lets the user fly the map to them."""

    locate_requested = pyqtSignal(float, float, int)
    metrics_ready = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._event_coords: list[tuple[float, float]] = []
        self._worker: NasaFetchWorker | None = None
        self._init_ui()
        self.refresh()

    def _init_ui(self) -> None:
        main = QVBoxLayout(self)
        main.setContentsMargins(18, 16, 18, 16)
        main.setSpacing(10)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("NATURAL EVENT WATCH")
        title.setStyleSheet("font-size: 18px; font-weight: 800; color: #0F172A;")
        subtitle = QLabel("NASA Earth Observatory Natural Event Tracker — kejadian alam aktif dunia.")
        subtitle.setStyleSheet("color: #64748B; font-size: 12px;")
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box)
        header.addStretch()

        refresh = QPushButton("⟳ Refresh EONET")
        refresh.setObjectName("primaryBtn")
        refresh.setStyleSheet("padding: 7px 14px; font-weight: 700;")
        refresh.clicked.connect(self.refresh)
        header.addWidget(refresh)

        locate = QPushButton("🎯 Locate on Map")
        locate.setObjectName("secondaryBtn")
        locate.setStyleSheet("padding: 7px 12px;")
        locate.clicked.connect(self._locate_selected)
        header.addWidget(locate)
        main.addLayout(header)

        self.status_label = QLabel("Memuat data EONET...")
        self.status_label.setStyleSheet("color: #64748B; font-size: 11px;")
        main.addWidget(self.status_label)

        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Event", "Kategori", "Waktu", "Magnitude", "Sumber"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        main.addWidget(self.table, stretch=1)

    def refresh(self) -> None:
        self.status_label.setText("Memuat data EONET...")
        self._worker = NasaFetchWorker(
            EONET_EVENTS_URL,
            {"status": "open", "limit": 30},
            use_key=False,
            cache_name="eonet_events",
        )
        self._worker.signals.finished.connect(self._on_data)
        self._worker.signals.failed.connect(self._on_error)
        QThreadPool.globalInstance().start(self._worker)

    def _on_data(self, response: NasaResponse) -> None:
        events = response.data.get("events", []) if isinstance(response.data, dict) else []
        self._event_coords.clear()
        self.table.setRowCount(len(events))

        for row, event in enumerate(events):
            geometry = event.get("geometry") or []
            latest = geometry[-1] if geometry else {}
            coordinates = latest.get("coordinates") or [0.0, 0.0]
            lon, lat = float(coordinates[0]), float(coordinates[1])
            self._event_coords.append((lat, lon))

            categories = ", ".join(cat.get("title", "") for cat in event.get("categories", []))
            sources = ", ".join(src.get("id", "") for src in event.get("sources", []))
            magnitude = latest.get("magnitudeValue")
            magnitude_text = (
                f"{magnitude} {latest.get('magnitudeUnit', '')}".strip() if magnitude is not None else "—"
            )

            values = [
                event.get("title", "—"),
                categories or "—",
                (latest.get("date") or "—").replace("T", " "),
                magnitude_text,
                sources or "—",
            ]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(str(value)))

        mode = "CACHE" if response.from_cache else "LIVE"
        self.status_label.setText(
            f"EONET · {len(events)} event aktif · Sumber: {mode} · Diperbarui {response.fetched_at}"
        )
        self.status_label.setProperty("updated", response.fetched_at)
        self.status_label.setProperty("event_count", len(events))
        self.status_label.setObjectName("eonetStatus")
        self.metrics_ready.emit({"event_count": len(events), "updated": response.fetched_at})

    def _on_error(self, message: str) -> None:
        self.status_label.setText(f"Gagal memuat EONET: {message}")

    def _locate_selected(self) -> None:
        row = self.table.currentRow()
        if 0 <= row < len(self._event_coords):
            lat, lon = self._event_coords[row]
            self.locate_requested.emit(lat, lon, 9)
