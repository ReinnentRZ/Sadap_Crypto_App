"""Near-Earth Object feed page (NASA NeoWs)."""
from datetime import datetime, timedelta, timezone

from PyQt6.QtCore import Qt, QThreadPool, pyqtSignal
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
from core.api.nasa_endpoints import NEOWS_FEED_URL
from gui.components.nasa_worker import NasaFetchWorker


class CoverNeowsPage(QWidget):
    """Displays close-approach asteroids and hazard flags."""

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
        title = QLabel("NEAR-EARTH OBJECT FEED")
        title.setStyleSheet("font-size: 18px; font-weight: 800; color: #0F172A;")
        subtitle = QLabel("NASA NeoWs — objek dengan pendekatan terdekat ke Bumi.")
        subtitle.setStyleSheet("color: #64748B; font-size: 12px;")
        box.addWidget(title)
        box.addWidget(subtitle)
        header.addLayout(box)
        header.addStretch()

        refresh = QPushButton("⟳ Refresh NeoWs")
        refresh.setObjectName("primaryBtn")
        refresh.setStyleSheet("padding: 7px 14px; font-weight: 700;")
        refresh.clicked.connect(self.refresh)
        header.addWidget(refresh)
        main.addLayout(header)

        self.summary_label = QLabel("Memuat data NeoWs...")
        self.summary_label.setStyleSheet("color: #64748B; font-size: 11px;")
        main.addWidget(self.summary_label)

        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(
            ["Objek", "Tanggal", "Diameter (m)", "Jarak (km)", "Kecepatan (km/s)", "Status"]
        )
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        main.addWidget(self.table, stretch=1)

    def refresh(self) -> None:
        today = datetime.now(timezone.utc).date()
        start = today - timedelta(days=1)
        end = today + timedelta(days=2)
        self.summary_label.setText("Memuat data NeoWs...")
        self._worker = NasaFetchWorker(
            NEOWS_FEED_URL,
            {"start_date": start.isoformat(), "end_date": end.isoformat()},
            cache_name="neows_feed",
        )
        self._worker.signals.finished.connect(self._on_data)
        self._worker.signals.failed.connect(self._on_error)
        QThreadPool.globalInstance().start(self._worker)

    def _on_data(self, response: NasaResponse) -> None:
        feed = response.data.get("near_earth_objects", {}) if isinstance(response.data, dict) else {}
        objects: list[dict] = []
        for daily in feed.values():
            objects.extend(daily)

        def distance(item: dict) -> float:
            approaches = item.get("close_approach_data") or []
            if not approaches:
                return float("inf")
            try:
                return float(approaches[0].get("miss_distance", {}).get("kilometers", float("inf")))
            except (TypeError, ValueError):
                return float("inf")

        objects.sort(key=distance)
        hazardous = sum(1 for item in objects if item.get("is_potentially_hazardous_asteroid"))
        self.table.setRowCount(len(objects))

        for row, item in enumerate(objects):
            approach = (item.get("close_approach_data") or [{}])[0]
            diameter_m = item.get("estimated_diameter", {}).get("meters", {})
            d_min = float(diameter_m.get("estimated_diameter_min", 0) or 0)
            d_max = float(diameter_m.get("estimated_diameter_max", 0) or 0)
            diameter_text = f"{d_min:.1f} – {d_max:.1f}" if d_max else "—"
            miss_km = approach.get("miss_distance", {}).get("kilometers", "—")
            velocity = approach.get("relative_velocity", {}).get("kilometers_per_second", "—")
            is_hazard = bool(item.get("is_potentially_hazardous_asteroid"))

            values = [
                item.get("name", "—"),
                approach.get("close_approach_date", "—"),
                diameter_text,
                f"{float(miss_km):,.0f}" if isinstance(miss_km, (int, float, str)) and str(miss_km).replace(".", "", 1).isdigit() else str(miss_km),
                f"{float(velocity):.2f}" if isinstance(velocity, (int, float, str)) and str(velocity).replace(".", "", 1).isdigit() else str(velocity),
                "⚠ HAZARDOUS" if is_hazard else "AMAN",
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(str(value))
                if col == 5 and is_hazard:
                    cell.setForeground(Qt.GlobalColor.red)
                self.table.setItem(row, col, cell)

        mode = "CACHE" if response.from_cache else "LIVE"
        self.summary_label.setText(
            f"NeoWs · {len(objects)} objek · {hazardous} potensial berbahaya · {mode} · {response.fetched_at}"
        )
        self.summary_label.setProperty("neo_count", len(objects))
        self.summary_label.setProperty("hazard_count", hazardous)
        self.summary_label.setProperty("updated", response.fetched_at)
        self.summary_label.setObjectName("neowsStatus")
        self.metrics_ready.emit(
            {
                "neo_count": len(objects),
                "hazard_count": hazardous,
                "updated": response.fetched_at,
            }
        )

    def _on_error(self, message: str) -> None:
        self.summary_label.setText(f"Gagal memuat NeoWs: {message}")
