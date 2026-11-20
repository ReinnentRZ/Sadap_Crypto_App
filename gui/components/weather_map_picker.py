"""Dialog with a mini map for picking a weather forecast location by center pin."""
from __future__ import annotations

from PyQt6.QtCore import QTimer, Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QVBoxLayout,
)

from gui.components.google_satellite_map_widget import GoogleSatelliteMapWidget


class WeatherLocationPickerDialog(QDialog):
    """Lets the user choose coordinates by panning/zooming so the pin stays at map center."""

    def __init__(self, latitude: float, longitude: float, label: str = "", parent=None):
        super().__init__(parent)
        self._latitude = float(latitude)
        self._longitude = float(longitude)
        self._label = label or "Lokasi Pilihan"
        self.selected: tuple[float, float, str] | None = None

        self.setWindowTitle("Pilih Lokasi Prakiraan Cuaca")
        self.resize(720, 520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        hint = QLabel(
            "Geser dan zoom peta sehingga pin berada di titik yang ingin diprakirakan. "
            "Pin selalu berada di tengah peta."
        )
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #334155; font-size: 12px;")
        layout.addWidget(hint)

        self.map_widget = GoogleSatelliteMapWidget(self)
        self.map_widget.setMinimumHeight(360)
        layout.addWidget(self.map_widget, stretch=1)

        self.coord_label = QLabel("Koordinat: —")
        self.coord_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.coord_label.setStyleSheet(
            "font-family: Consolas, monospace; font-size: 12px; font-weight: 600; color: #0284C7;"
        )
        layout.addWidget(self.coord_label)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Gunakan Lokasi Ini")
        self.buttons.accepted.connect(self._accept_location)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)

        # Initialize view/pin after the WebEngine view has had time to load.
        QTimer.singleShot(0, self._init_map)
        QTimer.singleShot(700, self._init_map)

        # Keep the displayed coordinates in sync while the user pans/zooms.
        self._poll_timer = QTimer(self)
        self._poll_timer.timeout.connect(self._refresh_coords)
        self._poll_timer.start(500)

    def _init_map(self) -> None:
        self.map_widget.enable_center_pin(True)
        self.map_widget.set_center_coordinates(self._latitude, self._longitude, 8)
        self._refresh_coords()

    def _refresh_coords(self) -> None:
        def _apply(point):
            if not point:
                return
            try:
                lat = float(point.get("lat", self._latitude))
                lng = float(point.get("lng", self._longitude))
            except (TypeError, ValueError):
                return
            self._latitude = lat
            self._longitude = lng
            self.coord_label.setText(f"Koordinat terpilih: {lat:.5f}, {lng:.5f}")

        self.map_widget.get_center(_apply)

    def _accept_location(self) -> None:
        def _apply(point):
            if point:
                try:
                    self._latitude = float(point.get("lat", self._latitude))
                    self._longitude = float(point.get("lng", self._longitude))
                except (TypeError, ValueError):
                    pass
            label = f"Pin Peta ({self._latitude:.4f}, {self._longitude:.4f})"
            self.selected = (self._latitude, self._longitude, label)
            self.accept()

        self.map_widget.get_center(_apply)

    def closeEvent(self, event):  # noqa: N802 - Qt API
        try:
            if hasattr(self, "_poll_timer"):
                self._poll_timer.stop()
            self.map_widget.enable_center_pin(False)
        except Exception:
            pass
        super().closeEvent(event)
