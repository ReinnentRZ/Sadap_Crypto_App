"""Interactive Earth observation map page."""
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import (
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from config.settings import SATELLITE_PRESETS
from gui.components.google_satellite_map_widget import GoogleSatelliteMapWidget


class CoverMapPage(QWidget):
    """Hosts the single WebEngine map instance used by the cover dashboard."""

    def __init__(self, parent=None):
        super().__init__(parent)
        default_name = next(iter(SATELLITE_PRESETS))
        default_preset = SATELLITE_PRESETS[default_name]
        self._current_target = (default_preset["lat"], default_preset["lon"], default_name)
        self._init_ui()
        QTimer.singleShot(900, lambda: self.fly_to_city("Jakarta Metropolitan & Port Zone"))

    def _init_ui(self) -> None:
        main = QVBoxLayout(self)
        main.setContentsMargins(18, 16, 18, 16)
        main.setSpacing(10)

        title = QLabel("EARTH OBSERVATION")
        title.setStyleSheet("font-size: 18px; font-weight: 800; color: #0F172A;")
        subtitle = QLabel("Peta satelit interaktif dengan target observasi di seluruh Indonesia.")
        subtitle.setStyleSheet("color: #64748B; font-size: 12px;")
        main.addWidget(title)
        main.addWidget(subtitle)

        controls = QHBoxLayout()
        controls.addWidget(QLabel("<b>Observation Target:</b>"))
        self.city_combo = QComboBox()
        self.city_combo.addItems(SATELLITE_PRESETS.keys())
        controls.addWidget(self.city_combo, stretch=1)

        self.btn_fly = QPushButton("🎯 Fly to Target")
        self.btn_fly.setObjectName("primaryBtn")
        self.btn_fly.setStyleSheet("padding: 7px 14px; font-weight: 700;")
        self.btn_fly.clicked.connect(self._on_fly_clicked)
        controls.addWidget(self.btn_fly)

        self.btn_refresh = QPushButton("⟳ Refresh Canvas")
        self.btn_refresh.setObjectName("secondaryBtn")
        self.btn_refresh.setStyleSheet("padding: 7px 12px;")
        self.btn_refresh.clicked.connect(self.refresh_map)
        controls.addWidget(self.btn_refresh)
        main.addLayout(controls)

        map_group = QGroupBox("Interactive Satellite Observation Map")
        map_layout = QVBoxLayout(map_group)
        map_layout.setContentsMargins(6, 8, 6, 6)
        map_layout.setSpacing(6)

        self.map_widget = GoogleSatelliteMapWidget(self)
        self.map_widget.setSizePolicy(
            self.map_widget.sizePolicy().horizontalPolicy(),
            self.map_widget.sizePolicy().verticalPolicy(),
        )
        map_layout.addWidget(self.map_widget, stretch=1)

        self.target_card = QLabel(
            "Kontrol: Drag untuk pan, scroll untuk zoom, gunakan menu kanan atas untuk mengganti layer peta."
        )
        self.target_card.setStyleSheet(
            "background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 4px; "
            "padding: 6px 8px; font-size: 11px; color: #475569;"
        )
        map_layout.addWidget(self.target_card)
        main.addWidget(map_group, stretch=1)

    def _on_fly_clicked(self) -> None:
        self.fly_to_city(self.city_combo.currentText())

    def fly_to_city(self, city_name: str) -> None:
        preset = SATELLITE_PRESETS.get(city_name)
        if not preset:
            return
        if self.city_combo.currentText() != city_name:
            self.city_combo.setCurrentText(city_name)
        self.fly_to_coordinates(preset["lat"], preset["lon"], preset["zoom"], city_name)
        self.target_card.setText(
            f"<b>Target:</b> {city_name} &nbsp;|&nbsp; <b>Koordinat:</b> {preset['coords']} "
            f"&nbsp;|&nbsp; <b>Elevasi:</b> {preset['elevation']} &nbsp;|&nbsp; <b>Cloud:</b> {preset['cloud_cover']}"
        )

    def fly_to_coordinates(
        self, lat: float, lon: float, zoom: int = 13, label: str = "Koordinat NASA"
    ) -> None:
        self._current_target = (lat, lon, label)
        self.map_widget.fly_to_coordinates(lat, lon, zoom)
        self.target_card.setText(
            f"<b>Target:</b> {label} &nbsp;|&nbsp; <b>Lat/Lon:</b> {lat:.4f}, {lon:.4f} "
            f"&nbsp;|&nbsp; <b>Zoom:</b> {zoom}x"
        )

    def current_target(self) -> tuple[float, float, str]:
        """Return the latitude, longitude, and label of the active map target."""
        return self._current_target

    def refresh_map(self) -> None:
        self.map_widget.invalidate_map_size()
