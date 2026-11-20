"""DONKI space-weather notification page."""
from datetime import datetime, timedelta, timezone

from PyQt6.QtCore import QThreadPool, pyqtSignal
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

from core.api.nasa_client import NasaResponse
from core.api.nasa_endpoints import DONKI_NOTIFICATIONS_URL
from gui.components.nasa_worker import NasaFetchWorker


class CoverSpaceWeatherPage(QWidget):
    """Shows recent DONKI alerts relevant to satellite uplink operations."""

    metrics_ready = pyqtSignal(dict)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker: NasaFetchWorker | None = None
        self._init_ui()
        self.refresh()

    def _init_ui(self) -> None:
        main = QVBoxLayout(self)
        main.setContentsMargins(18, 16, 18, 16)
        main.setSpacing(10)

        header = QHBoxLayout()
        box = QVBoxLayout()
        title = QLabel("SPACE WEATHER ADVISORY")
        title.setStyleSheet("font-size: 18px; font-weight: 800; color: #0F172A;")
        subtitle = QLabel("NASA DONKI notifikasi cuaca antariksa 7 hari terakhir.")
        subtitle.setStyleSheet("color: #64748B; font-size: 12px;")
        box.addWidget(title)
        box.addWidget(subtitle)
        header.addLayout(box)
        header.addStretch()

        refresh = QPushButton("⟳ Refresh DONKI")
        refresh.setObjectName("primaryBtn")
        refresh.setStyleSheet("padding: 7px 14px; font-weight: 700;")
        refresh.clicked.connect(self.refresh)
        header.addWidget(refresh)
        main.addLayout(header)

        self.summary_label = QLabel("Memuat data DONKI...")
        self.summary_label.setStyleSheet("color: #64748B; font-size: 11px;")
        main.addWidget(self.summary_label)

        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Waktu", "Tipe", "Notifikasi"])
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        main.addWidget(self.table, stretch=1)

    def refresh(self) -> None:
        today = datetime.now(timezone.utc).date()
        start = today - timedelta(days=7)
        self.summary_label.setText("Memuat data DONKI...")
        self._worker = NasaFetchWorker(
            DONKI_NOTIFICATIONS_URL,
            {
                "startDate": start.isoformat(),
                "endDate": today.isoformat(),
                "type": "all",
            },
            cache_name="donki_notifications",
        )
        self._worker.signals.finished.connect(self._on_data)
        self._worker.signals.failed.connect(self._on_error)
        QThreadPool.globalInstance().start(self._worker)

    def _on_data(self, response: NasaResponse) -> None:
        items = response.data if isinstance(response.data, list) else []
        self.table.setRowCount(len(items))

        type_counts: dict[str, int] = {}
        for row, item in enumerate(items):
            kind = str(item.get("messageType") or item.get("type") or "—")
            type_counts[kind] = type_counts.get(kind, 0) + 1
            issued = (
                item.get("messageIssued")
                or item.get("messageDate")
                or item.get("activityID")
                or "—"
            )
            note = item.get("note") or item.get("message") or item.get("messageURL") or "—"
            for col, value in enumerate([str(issued).replace("T", " "), kind, str(note)]):
                self.table.setItem(row, col, QTableWidgetItem(value))

        breakdown = ", ".join(f"{k}: {v}" for k, v in sorted(type_counts.items())) or "tidak ada notifikasi"
        mode = "CACHE" if response.from_cache else "LIVE"
        self.summary_label.setText(
            f"DONKI · {len(items)} notifikasi · {breakdown} · {mode} · {response.fetched_at}"
        )
        self.summary_label.setProperty("alert_count", len(items))
        self.summary_label.setProperty("updated", response.fetched_at)
        self.summary_label.setObjectName("donkiStatus")
        self.metrics_ready.emit({"alert_count": len(items), "updated": response.fetched_at})

    def _on_error(self, message: str) -> None:
        self.summary_label.setText(f"Gagal memuat DONKI: {message}")
