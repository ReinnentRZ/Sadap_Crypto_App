"""
Sadap GroundStation - Satellite Orbital Tracking Canvas Widget
Draws an animated geospatial orbital track, Earth coordinate grid, and telemetry
for the public Cover Mode interface. Supports simulated tracks and real
TLE-propagated positions/ground tracks.
"""
import math
import random

from PyQt6.QtCore import QTimer, Qt, QPointF
from PyQt6.QtGui import QPainter, QColor, QPen, QBrush, QFont
from PyQt6.QtWidgets import QWidget


class SatelliteMapWidget(QWidget):
    """Custom canvas showing orbital ground track and satellite position."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(420, 240)
        self.orbit_angle = 45.0  # degrees (simulated mode)
        self.satellite_callsign = "SADAP-SV09"

        # Modes: "simulated" (sine track, animated angle) or "real" (lat/lon data)
        self.mode = "simulated"
        self._track_points: list[tuple[float, float]] = []  # (lat, lon)
        self._current_latlon: tuple[float, float] | None = None
        self._info_text: str = ""

        # Telemetry timer
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._step_simulation)
        self.anim_timer.start(100)  # 10 Hz refresh

    def set_satellite(self, callsign: str, initial_angle: float = 45.0):
        """Backward-compatible: set simulated satellite and position."""
        self.set_simulated(callsign, initial_angle)

    def set_simulated(self, callsign: str, initial_angle: float = 45.0):
        """Use simulated sine-wave ground track and animated position."""
        self.mode = "simulated"
        self.satellite_callsign = callsign
        self.orbit_angle = initial_angle
        self._track_points = []
        self._current_latlon = None
        self._info_text = ""
        self.update()

    def set_real_data(
        self,
        callsign: str,
        track_points: list[tuple[float, float]],
        current_latlon: tuple[float, float] | None,
        info_text: str = "",
    ):
        """Use real lat/lon ground track and current sub-satellite point."""
        self.mode = "real"
        self.satellite_callsign = callsign
        self._track_points = track_points or []
        self._current_latlon = current_latlon
        self._info_text = info_text or ""
        self.update()

    def set_real_position(self, current_latlon: tuple[float, float] | None, info_text: str | None = None):
        """Update only current position (and optional info) in real mode."""
        if self.mode != "real":
            return
        self._current_latlon = current_latlon
        if info_text is not None:
            self._info_text = info_text
        self.update()

    def _step_simulation(self):
        """Advance satellite along simulated orbital path."""
        if self.mode != "simulated":
            return
        self.orbit_angle = (self.orbit_angle + 0.4) % 360.0
        self.update()

    # --- coordinate helpers ---
    def _geo_to_xy(self, lat: float, lon: float, w: int, h: int):
        x0, y0, x1, y1 = 20, 20, w - 20, h - 20
        # clamp
        lat = max(-90.0, min(90.0, lat))
        lon = ((lon + 180.0) % 360.0) - 180.0
        x = x0 + (lon + 180.0) / 360.0 * (x1 - x0)
        y = y0 + (90.0 - lat) / 180.0 * (y1 - y0)
        return x, y

    def _draw_base(self, painter: QPainter, w: int, h: int):
        # 1. Background
        painter.fillRect(0, 0, w, h, QColor("#FFFFFF"))

        # 2. Geospatial Grid Lines (Latitude & Longitude)
        grid_pen = QPen(QColor("#E2E8F0"), 1, Qt.PenStyle.DashLine)
        painter.setPen(grid_pen)
        for x in range(40, w - 20, 50):
            painter.drawLine(x, 20, x, h - 20)
        for y in range(30, h - 20, 40):
            painter.drawLine(20, y, w - 20, y)

        # Equator
        equator_pen = QPen(QColor("#CBD5E1"), 1.5, Qt.PenStyle.SolidLine)
        painter.setPen(equator_pen)
        painter.drawLine(20, h // 2, w - 20, h // 2)

        # 3. Continents Outline (decorative)
        continent_pen = QPen(QColor("#94A3B8"), 1)
        continent_brush = QBrush(QColor("#F1F5F9"))
        painter.setPen(continent_pen)
        painter.setBrush(continent_brush)
        painter.drawRoundedRect(int(w * 0.15), int(h * 0.2), int(w * 0.22), int(h * 0.45), 10, 10)
        painter.drawRoundedRect(int(w * 0.48), int(h * 0.18), int(w * 0.35), int(h * 0.5), 12, 12)
        painter.drawRoundedRect(int(w * 0.65), int(h * 0.55), int(w * 0.18), int(h * 0.3), 8, 8)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        self._draw_base(painter, w, h)

        if self.mode == "real":
            self._paint_real(painter, w, h)
        else:
            self._paint_simulated(painter, w, h)

    def _paint_simulated(self, painter: QPainter, w: int, h: int):
        # Orbital Ground Track (Sine wave path)
        orbit_pen = QPen(QColor("#38BDF8"), 2, Qt.PenStyle.SolidLine)
        painter.setPen(orbit_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        points = []
        for x_pos in range(20, w - 20, 4):
            rad = math.radians((x_pos / w) * 360 * 1.5)
            y_pos = (h // 2) + int(math.sin(rad) * (h * 0.35))
            points.append(QPointF(x_pos, y_pos))

        for i in range(len(points) - 1):
            painter.drawLine(points[i], points[i + 1])

        # Active Satellite Marker
        sat_x = int(20 + ((self.orbit_angle / 360.0) * (w - 40)))
        sat_rad = math.radians((sat_x / w) * 360 * 1.5)
        sat_y = int((h // 2) + (math.sin(sat_rad) * (h * 0.35)))

        pulse_pen = QPen(QColor(2, 132, 199, 120), 1.5)
        painter.setPen(pulse_pen)
        painter.setBrush(QColor(2, 132, 199, 30))
        painter.drawEllipse(QPointF(sat_x, sat_y), 14, 14)

        painter.setPen(QPen(QColor("#FFFFFF"), 2))
        painter.setBrush(QBrush(QColor("#0284C7")))
        painter.drawEllipse(QPointF(sat_x, sat_y), 5, 5)

        font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QPen(QColor("#0F172A")))
        painter.drawText(sat_x + 12, sat_y - 8, f"{self.satellite_callsign}")

        subfont = QFont("Segoe UI", 8)
        painter.setFont(subfont)
        painter.setPen(QPen(QColor("#64748B")))

        lat = (h // 2 - sat_y) / (h // 2) * 90.0
        lon = (sat_x - w // 2) / (w // 2) * 180.0
        painter.drawText(
            sat_x + 12,
            sat_y + 8,
            f"{abs(lat):.1f}°{'N' if lat>=0 else 'S'}, {abs(lon):.1f}°{'E' if lon>=0 else 'W'} (sim)",
        )

    def _paint_real(self, painter: QPainter, w: int, h: int):
        # Ground track
        track_pen = QPen(QColor("#2563EB"), 2, Qt.PenStyle.SolidLine)
        painter.setPen(track_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        if self._track_points:
            # draw segments, splitting on dateline jumps
            for i in range(len(self._track_points) - 1):
                lat1, lon1 = self._track_points[i]
                lat2, lon2 = self._track_points[i + 1]
                if abs(lon2 - lon1) > 180:
                    continue
                x1, y1 = self._geo_to_xy(lat1, lon1, w, h)
                x2, y2 = self._geo_to_xy(lat2, lon2, w, h)
                painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        # Current position
        if self._current_latlon is not None:
            lat, lon = self._current_latlon
            sat_x, sat_y = self._geo_to_xy(lat, lon, w, h)

            pulse_pen = QPen(QColor(37, 99, 235, 120), 1.5)
            painter.setPen(pulse_pen)
            painter.setBrush(QColor(37, 99, 235, 30))
            painter.drawEllipse(QPointF(sat_x, sat_y), 14, 14)

            painter.setPen(QPen(QColor("#FFFFFF"), 2))
            painter.setBrush(QBrush(QColor("#2563EB")))
            painter.drawEllipse(QPointF(sat_x, sat_y), 5, 5)

            font = QFont("Segoe UI", 9, QFont.Weight.Bold)
            painter.setFont(font)
            painter.setPen(QPen(QColor("#0F172A")))
            painter.drawText(int(sat_x) + 12, int(sat_y) - 8, f"{self.satellite_callsign}")

            subfont = QFont("Segoe UI", 8)
            painter.setFont(subfont)
            painter.setPen(QPen(QColor("#64748B")))
            coord_text = f"{abs(lat):.2f}°{'N' if lat>=0 else 'S'}, {abs(lon):.2f}°{'E' if lon>=0 else 'W'}"
            if self._info_text:
                coord_text = f"{coord_text}  {self._info_text}"
            painter.drawText(int(sat_x) + 12, int(sat_y) + 8, coord_text)
        else:
            # no fix yet
            font = QFont("Segoe UI", 9, QFont.Weight.Bold)
            painter.setFont(font)
            painter.setPen(QPen(QColor("#64748B")))
            msg = self._info_text or "Menunggu data TLE..."
            painter.drawText(28, h - 28, f"{self.satellite_callsign} — {msg}")
