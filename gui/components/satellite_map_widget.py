"""
Sadap GroundStation - Satellite Orbital Tracking Canvas Widget
Draws an animated geospatial orbital track, Earth coordinate grid, and telemetry
for the public Cover Mode interface.
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
        self.orbit_angle = 45.0  # degrees
        self.satellite_callsign = "SADAP-SV09"

        # Telemetry timer
        self.anim_timer = QTimer(self)
        self.anim_timer.timeout.connect(self._step_simulation)
        self.anim_timer.start(100)  # 10 Hz refresh

    def set_satellite(self, callsign: str, initial_angle: float = 45.0):
        """Update tracked satellite callsign and position."""
        self.satellite_callsign = callsign
        self.orbit_angle = initial_angle
        self.update()

    def _step_simulation(self):
        """Advance satellite along simulated orbital path."""
        self.orbit_angle = (self.orbit_angle + 0.4) % 360.0
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # 1. Background (Clean slate-white aerospace look)
        painter.fillRect(0, 0, w, h, QColor("#FFFFFF"))

        # 2. Draw Geospatial Grid Lines (Latitude & Longitude)
        grid_pen = QPen(QColor("#E2E8F0"), 1, Qt.PenStyle.DashLine)
        painter.setPen(grid_pen)

        # Vertical longitudes
        for x in range(40, w - 20, 50):
            painter.drawLine(x, 20, x, h - 20)

        # Horizontal latitudes
        for y in range(30, h - 20, 40):
            painter.drawLine(20, y, w - 20, y)

        # Equator line (Darker solid line)
        equator_pen = QPen(QColor("#CBD5E1"), 1.5, Qt.PenStyle.SolidLine)
        painter.setPen(equator_pen)
        painter.drawLine(20, h // 2, w - 20, h // 2)

        # 3. Draw Continents Outline (Geometric representation)
        continent_pen = QPen(QColor("#94A3B8"), 1)
        continent_brush = QBrush(QColor("#F1F5F9"))
        painter.setPen(continent_pen)
        painter.setBrush(continent_brush)

        # Simulated landmasses
        painter.drawRoundedRect(int(w * 0.15), int(h * 0.2), int(w * 0.22), int(h * 0.45), 10, 10)
        painter.drawRoundedRect(int(w * 0.48), int(h * 0.18), int(w * 0.35), int(h * 0.5), 12, 12)
        painter.drawRoundedRect(int(w * 0.65), int(h * 0.55), int(w * 0.18), int(h * 0.3), 8, 8)

        # 4. Draw Orbital Ground Track (Sine wave path)
        orbit_pen = QPen(QColor("#38BDF8"), 2, Qt.PenStyle.SolidLine)
        painter.setPen(orbit_pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)

        points = []
        for x_pos in range(20, w - 20, 4):
            # Sinusoidal ground track
            rad = math.radians((x_pos / w) * 360 * 1.5)
            y_pos = (h // 2) + int(math.sin(rad) * (h * 0.35))
            points.append(QPointF(x_pos, y_pos))

        for i in range(len(points) - 1):
            painter.drawLine(points[i], points[i + 1])

        # 5. Draw Active Satellite Marker
        sat_x = int(20 + ((self.orbit_angle / 360.0) * (w - 40)))
        sat_rad = math.radians((sat_x / w) * 360 * 1.5)
        sat_y = int((h // 2) + (math.sin(sat_rad) * (h * 0.35)))

        # Outer radar pulse ring
        pulse_pen = QPen(QColor(2, 132, 199, 120), 1.5)
        painter.setPen(pulse_pen)
        painter.setBrush(QColor(2, 132, 199, 30))
        painter.drawEllipse(QPointF(sat_x, sat_y), 14, 14)

        # Satellite center point
        painter.setPen(QPen(QColor("#FFFFFF"), 2))
        painter.setBrush(QBrush(QColor("#0284C7")))
        painter.drawEllipse(QPointF(sat_x, sat_y), 5, 5)

        # 6. Satellite Label & Telemetry Badge
        font = QFont("Segoe UI", 9, QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QPen(QColor("#0F172A")))
        painter.drawText(sat_x + 12, sat_y - 8, f"{self.satellite_callsign}")

        subfont = QFont("Segoe UI", 8)
        painter.setFont(subfont)
        painter.setPen(QPen(QColor("#64748B")))

        lat = (h // 2 - sat_y) / (h // 2) * 90.0
        lon = (sat_x - w // 2) / (w // 2) * 180.0
        painter.drawText(sat_x + 12, sat_y + 8, f"{abs(lat):.1f}°{'N' if lat>=0 else 'S'}, {abs(lon):.1f}°{'E' if lon>=0 else 'W'}")
