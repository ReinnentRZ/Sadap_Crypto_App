"""Satellite tracking and live telemetry page (moved from the original cover)."""
import random

from PyQt6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from config.settings import SATELLITES_DATA


class CoverTelemetryPage(QWidget):
    """Preserves the original orbital radar, telemetry gauges, pass table, and RX stream."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._init_ui()
        self.on_satellite_changed(0)

    def _init_ui(self) -> None:
        main = QHBoxLayout(self)
        main.setContentsMargins(18, 16, 18, 16)
        main.setSpacing(10)

        left = QVBoxLayout()
        left.setSpacing(8)

        sat_bar = QHBoxLayout()
        sat_bar.addWidget(QLabel("<b>Tracked Satellite:</b>"))
        self.satellite_combo = QComboBox()
        self.satellite_combo.addItems(SATELLITES_DATA.keys())
        self.satellite_combo.currentIndexChanged.connect(self.on_satellite_changed)
        sat_bar.addWidget(self.satellite_combo, stretch=1)
        left.addLayout(sat_bar)

        radar_group = QGroupBox("Real-time Orbital Ground Track (GIS Radar)")
        radar_layout = QVBoxLayout(radar_group)
        radar_layout.setContentsMargins(6, 8, 6, 6)
        from gui.components.satellite_map_widget import SatelliteMapWidget

        self.map_widget = SatelliteMapWidget(self)
        radar_layout.addWidget(self.map_widget)
        left.addWidget(radar_group, stretch=4)

        telem_group = QGroupBox("Sub-Satellite Sensor & Power Telemetry")
        telem_layout = QGridLayout(telem_group)
        telem_layout.setContentsMargins(10, 8, 10, 8)
        telem_layout.setSpacing(6)

        self.val_altitude = QLabel("542.4 km")
        self.val_speed = QLabel("7.61 km/s")
        self.val_freq = QLabel("2.245 GHz (Locked)")
        self.val_azimuth = QLabel("142.8° (Antenna A)")
        self.val_snr = QLabel("+24.8 dB (Excellent)")
        self.val_solar = QLabel("1,420 W (Sunlit)")

        rows = [
            ("Orbit Altitude:", self.val_altitude, "Ground Speed:", self.val_speed),
            ("Downlink Freq:", self.val_freq, "Azimuth / Elev:", self.val_azimuth),
            ("Signal SNR:", self.val_snr, "Solar Array Power:", self.val_solar),
        ]
        for row, (l1, v1, l2, v2) in enumerate(rows):
            telem_layout.addWidget(QLabel(l1), row, 0)
            telem_layout.addWidget(v1, row, 1)
            telem_layout.addWidget(QLabel(l2), row, 2)
            telem_layout.addWidget(v2, row, 3)

        telem_layout.addWidget(QLabel("Bus Battery Reserve:"), 3, 0)
        self.battery_bar = QProgressBar()
        self.battery_bar.setValue(94)
        self.battery_bar.setTextVisible(True)
        self.battery_bar.setFixedHeight(16)
        self.battery_bar.setStyleSheet("QProgressBar::chunk { background-color: #059669; border-radius: 3px; }")
        telem_layout.addWidget(self.battery_bar, 3, 1, 1, 3)
        left.addWidget(telem_group, stretch=3)

        pass_group = QGroupBox("Pass Prediction Schedule (Next 12 Hours)")
        pass_layout = QVBoxLayout(pass_group)
        pass_layout.setContentsMargins(6, 6, 6, 6)
        self.pass_table = QTableWidget()
        self.pass_table.setColumnCount(5)
        self.pass_table.setHorizontalHeaderLabels(["Pass #", "Satellite Target", "AOS (Acquire)", "Max Elev", "Duration"])
        self.pass_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.pass_table.setMaximumHeight(170)
        self._populate_pass_schedule()
        pass_layout.addWidget(self.pass_table)
        left.addWidget(pass_group, stretch=3)
        main.addLayout(left, stretch=4)

        right = QVBoxLayout()
        right.setSpacing(8)
        terminal_group = QGroupBox("Decoded Telemetry Event Stream (Live RX)")
        term_layout = QVBoxLayout(terminal_group)
        term_layout.setContentsMargins(6, 4, 6, 6)
        self.terminal_view = QTextEdit()
        self.terminal_view.setReadOnly(True)
        self.terminal_view.setStyleSheet(
            "background-color: #0F172A; color: #38BDF8; font-family: 'Consolas', 'Courier New', monospace; "
            "font-size: 11px; border-radius: 4px; padding: 4px;"
        )
        self._init_terminal_stream()
        term_layout.addWidget(self.terminal_view)
        right.addWidget(terminal_group, stretch=1)
        main.addLayout(right, stretch=2)

    def on_satellite_changed(self, index: int) -> None:
        sat_name = self.satellite_combo.currentText()
        data = SATELLITES_DATA.get(sat_name, {})
        if not data:
            return
        self.map_widget.set_satellite(data["callsign"], initial_angle=random.uniform(20.0, 180.0))
        self.val_altitude.setText(data["alt"])
        self.val_speed.setText(data["spd"])
        self.val_freq.setText(data["freq"])
        self.val_azimuth.setText(f"{random.randint(40, 280)}.4° (Antenna A)")
        self.val_snr.setText(f"+{random.uniform(22.0, 27.5):.1f} dB")
        self.val_solar.setText(f"{random.randint(1350, 1490)} W (Sunlit)")

    def select_default(self) -> None:
        self.on_satellite_changed(0)

    def _populate_pass_schedule(self) -> None:
        passes = [
            ("P-1042", "SADAP-SV09", "22:48:12 UTC", "72° NE", "09m 45s"),
            ("P-1043", "ISS (ZARYA)", "23:14:05 UTC", "58° WSW", "06m 12s"),
            ("P-1044", "LANDSAT-9", "00:22:40 UTC", "84° N", "11m 30s"),
            ("P-1045", "SENTINEL-2A", "01:05:18 UTC", "65° S", "10m 05s"),
        ]
        self.pass_table.setRowCount(len(passes))
        for row, values in enumerate(passes):
            for col, value in enumerate(values):
                self.pass_table.setItem(row, col, QTableWidgetItem(value))

    def _init_terminal_stream(self) -> None:
        self.terminal_view.setPlainText(
            "\n".join(
                [
                    "[SYSTEM] Ground Station Core v2.4 initialized. S-Band / X-Band phased array online.",
                    "[EPHEMERIS] TLE orbit models synchronized with NORAD orbital catalog.",
                    "[DOWNLINK] 2.245 GHz stream synced at 150.2 Mbps. Signal lock confirmed.",
                ]
            )
        )

    def append_telemetry_event(self) -> None:
        sat = self.satellite_combo.currentText().split()[0]
        frame_id = random.randint(10000, 99999)
        from datetime import datetime

        now_time = datetime.now().strftime("%H:%M:%S")
        events = [
            f"[{now_time}] [{sat}] RX-FRAME #{frame_id}: Doppler shift compensated. Telemetry CRC32 OK.",
            f"[{now_time}] [{sat}] SENSOR-TELEMETRY: Bus voltage 28.4V | Solar array 5.12A | Thermal nominal.",
            f"[{now_time}] [{sat}] DOWNLINK-STREAM: Demodulated 64-APSK packet block #{frame_id}. Signal quality 99.8%.",
            f"[{now_time}] [{sat}] ATTITUDE-CONTROL: Reaction wheels RPM nominal | Star tracker locked.",
        ]
        self.terminal_view.append(random.choice(events))
        lines = self.terminal_view.toPlainText().splitlines()
        if len(lines) > 40:
            self.terminal_view.setPlainText("\n".join(lines[-25:]))
