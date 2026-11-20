"""Full-disk Earth (EPIC) and Astronomy Picture of the Day page."""
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)
from PyQt6.QtCore import Qt, QThreadPool

from config.settings import NASA_API_KEY
from core.api.nasa_client import NasaResponse
from core.api.nasa_endpoints import APOD_URL, EPIC_NATURAL_IMAGES_URL, epic_image_url
from gui.components.nasa_worker import NasaFetchWorker, NasaImageWorker


class CoverEarthImageryPage(QWidget):
    """Displays two NASA imagery feeds with graceful offline caching."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._epic_worker: NasaFetchWorker | None = None
        self._apod_worker: NasaFetchWorker | None = None
        self._epic_image_worker: NasaImageWorker | None = None
        self._apod_image_worker: NasaImageWorker | None = None
        self._init_ui()
        self.refresh()

    def _init_ui(self) -> None:
        main = QVBoxLayout(self)
        main.setContentsMargins(18, 16, 18, 16)
        main.setSpacing(10)

        header = QHBoxLayout()
        box = QVBoxLayout()
        title = QLabel("EARTH & ASTRONOMY IMAGERY")
        title.setStyleSheet("font-size: 18px; font-weight: 800; color: #0F172A;")
        subtitle = QLabel("NASA EPIC full-disk Earth dan Astronomy Picture of the Day.")
        subtitle.setStyleSheet("color: #64748B; font-size: 12px;")
        box.addWidget(title)
        box.addWidget(subtitle)
        header.addLayout(box)
        header.addStretch()

        refresh = QPushButton("⟳ Refresh Imagery")
        refresh.setObjectName("primaryBtn")
        refresh.setStyleSheet("padding: 7px 14px; font-weight: 700;")
        refresh.clicked.connect(self.refresh)
        header.addWidget(refresh)
        main.addLayout(header)

        panels = QHBoxLayout()
        panels.setSpacing(12)

        # EPIC panel
        epic_group = QGroupBox("EPIC — Full Disk Earth (DSCOVR)")
        epic_layout = QVBoxLayout(epic_group)
        epic_layout.setContentsMargins(8, 10, 8, 8)
        self.epic_image = self._make_image_label()
        self.epic_status = QLabel("Memuat EPIC...")
        self.epic_status.setStyleSheet("color: #64748B; font-size: 10px;")
        self.epic_text = self._make_text_view()
        epic_layout.addWidget(self.epic_image, stretch=3)
        epic_layout.addWidget(self.epic_status)
        epic_layout.addWidget(self.epic_text, stretch=2)
        panels.addWidget(epic_group, stretch=1)

        # APOD panel
        apod_group = QGroupBox("APOD — Astronomy Picture of the Day")
        apod_layout = QVBoxLayout(apod_group)
        apod_layout.setContentsMargins(8, 10, 8, 8)
        self.apod_image = self._make_image_label()
        self.apod_status = QLabel("Memuat APOD...")
        self.apod_status.setStyleSheet("color: #64748B; font-size: 10px;")
        self.apod_text = self._make_text_view()
        apod_layout.addWidget(self.apod_image, stretch=3)
        apod_layout.addWidget(self.apod_status)
        apod_layout.addWidget(self.apod_text, stretch=2)
        panels.addWidget(apod_group, stretch=1)

        main.addLayout(panels, stretch=1)

    @staticmethod
    def _make_image_label() -> QLabel:
        label = QLabel("Menunggu gambar...")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setMinimumHeight(220)
        label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        label.setStyleSheet(
            "background-color: #0F172A; color: #64748B; border-radius: 6px; font-size: 11px;"
        )
        return label

    @staticmethod
    def _make_text_view() -> QTextEdit:
        view = QTextEdit()
        view.setReadOnly(True)
        view.setStyleSheet(
            "background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; "
            "font-size: 11px; color: #334155; padding: 6px;"
        )
        return view

    def refresh(self) -> None:
        self.epic_status.setText("Memuat EPIC...")
        self.apod_status.setText("Memuat APOD...")

        self._epic_worker = NasaFetchWorker(
            EPIC_NATURAL_IMAGES_URL,
            {},
            use_key=False,
            cache_name="epic_natural",
        )
        self._epic_worker.signals.finished.connect(self._on_epic_data)
        self._epic_worker.signals.failed.connect(lambda msg: self.epic_status.setText(f"Gagal: {msg}"))
        QThreadPool.globalInstance().start(self._epic_worker)

        self._apod_worker = NasaFetchWorker(
            APOD_URL,
            {"count": 1},
            cache_name="apod_latest",
        )
        self._apod_worker.signals.finished.connect(self._on_apod_data)
        self._apod_worker.signals.failed.connect(lambda msg: self.apod_status.setText(f"Gagal: {msg}"))
        QThreadPool.globalInstance().start(self._apod_worker)

    def _on_epic_data(self, response: NasaResponse) -> None:
        records = response.data if isinstance(response.data, list) else []
        if not records:
            self.epic_status.setText("EPIC: tidak ada gambar terbaru.")
            return
        first = records[0]
        image_name = first.get("image", "")
        date = first.get("date", "")
        if not image_name or not date:
            self.epic_status.setText("EPIC: format data tidak dikenali.")
            return

        self.epic_text.setPlainText(
            f"Tanggal: {date}\nKeterangan: {first.get('caption', '—')}\n"
            f"Koordinat pusat: {first.get('centroid_coordinates', {})}"
        )
        url = epic_image_url(image_name, date, NASA_API_KEY)
        self._epic_image_worker = NasaImageWorker(url, "epic_image")
        self._epic_image_worker.signals.finished.connect(self._set_epic_image)
        self._epic_image_worker.signals.failed.connect(
            lambda msg: self.epic_status.setText(f"Gambar EPIC gagal: {msg}")
        )
        QThreadPool.globalInstance().start(self._epic_image_worker)
        mode = "CACHE" if response.from_cache else "LIVE"
        self.epic_status.setText(f"EPIC · {len(records)} gambar · {mode} · {response.fetched_at}")

    def _on_apod_data(self, response: NasaResponse) -> None:
        data = response.data
        if isinstance(data, list):
            data = data[0] if data else {}
        if not isinstance(data, dict):
            self.apod_status.setText("APOD: format data tidak dikenali.")
            return

        title = data.get("title", "Astronomy Picture of the Day")
        explanation = data.get("explanation", "")
        image_url = data.get("hdurl") or data.get("url") or ""
        permalink = data.get("permalink") or image_url or "—"
        mode = "CACHE" if response.from_cache else "LIVE"
        self.apod_text.setPlainText(f"{title}\n\n{explanation}\n\nTautan: {permalink}")

        # APOD occasionally publishes video instead of a still image.
        if str(data.get("media_type") or "image").lower() != "image":
            self.apod_image.setPixmap(QPixmap())
            self.apod_image.setText("APOD hari ini berupa video.\nBuka tautan di panel teks.")
            self.apod_status.setText(
                f"APOD · video · {data.get('date', '—')} · {mode} · {response.fetched_at}"
            )
            return

        if not image_url:
            self.apod_status.setText("APOD: URL gambar tidak tersedia.")
            return
        self._apod_image_worker = NasaImageWorker(image_url, "apod_image")
        self._apod_image_worker.signals.finished.connect(self._set_apod_image)
        self._apod_image_worker.signals.failed.connect(
            lambda msg: self.apod_status.setText(f"Gambar APOD gagal: {msg}")
        )
        QThreadPool.globalInstance().start(self._apod_image_worker)
        self.apod_status.setText(f"APOD · {data.get('date', '—')} · {mode} · {response.fetched_at}")

    def _set_epic_image(self, payload: tuple[bytes, bool]) -> None:
        self._apply_pixmap(self.epic_image, payload[0])

    def _set_apod_image(self, payload: tuple[bytes, bool]) -> None:
        self._apply_pixmap(self.apod_image, payload[0])

    def _apply_pixmap(self, label: QLabel, payload: bytes) -> None:
        pixmap = QPixmap()
        if not pixmap.loadFromData(payload):
            label.setText("Gambar tidak dapat dibaca.")
            return
        label.setPixmap(
            pixmap.scaled(
                label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
