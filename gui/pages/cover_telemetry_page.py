"""Satellite tracking and live telemetry page with CelesTrak TLE (plan A)."""
import random
from datetime import datetime, timezone

from PyQt6.QtCore import Qt, QThreadPool, QTimer
from PyQt6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from config.settings import SATELLITES_DATA, TELEMETRY_OBSERVER
from core.utils.orbit import (
    az_to_compass,
    build_satrec,
    compute_ground_track,
    compute_passes,
    propagate_position,
    sgp4_available,
)
from gui.components.tle_worker import TleFetchWorker


class CoverTelemetryPage(QWidget):
    """Orbital radar, telemetry gauges, pass schedule, and RX stream.

    For satellites with NORAD IDs, fetches TLE from CelesTrak (no API key),
    propagates real position/altitude/speed and ground track (SGP4), and
    computes pass predictions for the configured observer station. Bus/link
    telemetry (SNR, power, battery, azimuth readout) remains simulated.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._tle_worker: TleFetchWorker | None = None
        self._current_norad_id: int | None = None
        self._satrec = None
        self._tle_line2: str | None = None
        self._tle_epoch: str | None = None
        self._tle_source_mode: str = "SIMULATED"  # LIVE / CACHE / SIMULATED / ERROR

        self._real_update_timer = QTimer(self)
        self._real_update_timer.setInterval(10000)  # 10s position refresh
        self._real_update_timer.timeout.connect(self._update_real_position)

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

        self.btn_refresh_tle = QPushButton("⟳ Refresh TLE")
        self.btn_refresh_tle.setObjectName("secondaryBtn")
        self.btn_refresh_tle.setStyleSheet("padding: 6px 10px;")
        self.btn_refresh_tle.clicked.connect(self._refresh_current_tle)
        sat_bar.addWidget(self.btn_refresh_tle)
        left.addLayout(sat_bar)

        self.tle_status_label = QLabel("TLE: —")
        self.tle_status_label.setWordWrap(True)
        self.tle_status_label.setStyleSheet("color: #64748B; font-size: 11px;")
        left.addWidget(self.tle_status_label)

        radar_group = QGroupBox("Real-time Orbital Ground Track (GIS Radar)")
        radar_layout = QVBoxLayout(radar_group)
        radar_layout.setContentsMargins(6, 8, 6, 6)
        from gui.components.satellite_map_widget import SatelliteMapWidget

        self.map_widget = SatelliteMapWidget(self)
        radar_layout.addWidget(self.map_widget)
        left.addWidget(radar_group, stretch=4)

        telem_group = QGroupBox("Sub-Satellite & Link Telemetry")
        telem_layout = QGridLayout(telem_group)
        telem_layout.setContentsMargins(10, 8, 10, 8)
        telem_layout.setSpacing(6)

        self.val_altitude = QLabel("—")
        self.val_speed = QLabel("—")
        self.val_freq = QLabel("—")
        self.val_azimuth = QLabel("—")
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
        self.battery_bar.setStyleSheet("QProgressBar::chunk { background-color: #16A34A; border-radius: 3px; }")
        telem_layout.addWidget(self.battery_bar, 3, 1, 1, 3)

        obs_name = TELEMETRY_OBSERVER.get("name", "Ground Station")
        self.telemetry_note = QLabel(
            f"Catatan: SNR/daya/baterai/azimuth simulasi tampilan. Alt/spd, posisi, ground track, "
            f"dan prediksi lintasan (≥5°, 12 jam, stasiun {obs_name}) untuk satelit NORAD "
            f"berasal dari TLE CelesTrak (SGP4)."
        )
        self.telemetry_note.setWordWrap(True)
        self.telemetry_note.setStyleSheet("color: #94A3B8; font-size: 10px;")
        telem_layout.addWidget(self.telemetry_note, 4, 0, 1, 4)
        left.addWidget(telem_group, stretch=3)

        self.pass_group = QGroupBox(f"Pass Prediction (Next 12h, {obs_name})")
        pass_layout = QVBoxLayout(self.pass_group)
        pass_layout.setContentsMargins(6, 6, 6, 6)
        self.pass_table = QTableWidget()
        self.pass_table.setColumnCount(5)
        self.pass_table.setHorizontalHeaderLabels(["Pass #", "Satellite Target", "AOS (UTC)", "Max Elev", "Duration"])
        self.pass_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.pass_table.setMaximumHeight(170)
        self._set_pass_placeholder("Pilih satelit untuk melihat prediksi lintasan.")
        pass_layout.addWidget(self.pass_table)
        left.addWidget(self.pass_group, stretch=3)
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

    # --- satellite selection / TLE ---
    def on_satellite_changed(self, index: int) -> None:
        sat_name = self.satellite_combo.currentText()
        data = SATELLITES_DATA.get(sat_name, {})
        if not data:
            return

        norad_id = data.get("norad_id")
        callsign = data.get("callsign", sat_name)
        simulated = bool(data.get("simulated")) or norad_id is None

        self._current_norad_id = norad_id if not simulated else None
        self._satrec = None
        self._tle_line2 = None
        self._tle_epoch = None
        self._tle_source_mode = "SIMULATED"
        self._real_update_timer.stop()

        self.val_freq.setText(data.get("freq", "—"))
        self.val_azimuth.setText(f"{random.randint(40, 280)}.4° (Antenna A)")
        self.val_snr.setText(f"+{random.uniform(22.0, 27.5):.1f} dB")
        self.val_solar.setText(f"{random.randint(1350, 1490)} W (Sunlit)")
        self.battery_bar.setValue(random.randint(78, 98))

        if simulated:
            self.map_widget.set_simulated(callsign, initial_angle=random.uniform(20.0, 180.0))
            self.val_altitude.setText(data.get("alt", "—"))
            self.val_speed.setText(data.get("spd", "—"))
            self.tle_status_label.setText("TLE: Simulasi lokal (satelit tanpa NORAD ID).")
            self._populate_simulated_pass_schedule()
            self._log_terminal(f"[TLE] {callsign}: mode simulasi (tidak ada NORAD ID).")
            return

        self.map_widget.set_real_data(callsign, [], None, "Memuat TLE CelesTrak...")
        self.val_altitude.setText("—")
        self.val_speed.setText("—")
        self._set_pass_placeholder("Memuat TLE & menghitung prediksi lintasan…")
        self.tle_status_label.setText(f"TLE: Memuat dari CelesTrak (NORAD {norad_id})…")
        self._log_terminal(f"[TLE] Request CelesTrak GP untuk {callsign} (NORAD {norad_id}).")
        self._start_tle_fetch(int(norad_id))

    def _refresh_current_tle(self) -> None:
        if self._current_norad_id is None:
            self.on_satellite_changed(self.satellite_combo.currentIndex())
            return
        self._set_pass_placeholder("Memuat ulang TLE & menghitung prediksi lintasan…")
        self.tle_status_label.setText(f"TLE: Memuat ulang dari CelesTrak (NORAD {self._current_norad_id})…")
        self._start_tle_fetch(int(self._current_norad_id))

    def _start_tle_fetch(self, norad_id: int) -> None:
        self._tle_worker = TleFetchWorker(norad_id)
        self._tle_worker.signals.finished.connect(self._on_tle_loaded)
        self._tle_worker.signals.failed.connect(self._on_tle_error)
        QThreadPool.globalInstance().start(self._tle_worker)

    def _on_tle_loaded(self, response) -> None:
        tle = getattr(response, "tle", None) or {}
        norad_id = tle.get("norad_id")
        if norad_id != self._current_norad_id:
            return

        sat_name = self.satellite_combo.currentText()
        data = SATELLITES_DATA.get(sat_name, {})
        callsign = data.get("callsign", sat_name)
        mode = "CACHE" if getattr(response, "from_cache", False) else "LIVE"
        fetched_at = getattr(response, "fetched_at", "—")
        self._tle_source_mode = mode
        self._tle_epoch = tle.get("epoch")
        self._tle_line2 = tle.get("line2")

        if not sgp4_available():
            self.tle_status_label.setText(
                f"TLE: {mode} (CelesTrak, NORAD {norad_id}, epoch {self._tle_epoch or '—'}) — "
                "library sgp4 tidak tersedia, fallback simulasi posisi."
            )
            self._fallback_simulated(data, callsign, reason="sgp4 tidak terpasang")
            return

        try:
            self._satrec = build_satrec(tle.get("line1", ""), tle.get("line2", ""))
            now = datetime.now(timezone.utc)
            lat, lon, alt, vel = propagate_position(self._satrec, now)
            track = compute_ground_track(self._satrec, tle.get("line2", ""), now)
            self.map_widget.set_real_data(callsign, track, (lat, lon), f"TLE {mode}")
            self.val_altitude.setText(f"{alt:.1f} km")
            self.val_speed.setText(f"{vel:.2f} km/s")
            self.tle_status_label.setText(
                f"TLE: {mode} • CelesTrak NORAD {norad_id} • epoch {self._tle_epoch or '—'} • diperbarui {fetched_at}"
            )
            self._log_terminal(
                f"[TLE] {callsign} NORAD {norad_id} termuat ({mode}). "
                f"Pos: {lat:.2f},{lon:.2f} alt {alt:.1f} km vel {vel:.2f} km/s."
            )
            self._update_pass_schedule(self._satrec, callsign)
            self._real_update_timer.start()
        except Exception as exc:  # noqa: BLE001
            self.tle_status_label.setText(
                f"TLE: {mode} diterima (NORAD {norad_id}) tetapi propagasi gagal: {exc}. Fallback simulasi."
            )
            self._fallback_simulated(data, callsign, reason=str(exc))

    def _on_tle_error(self, message: str) -> None:
        sat_name = self.satellite_combo.currentText()
        data = SATELLITES_DATA.get(sat_name, {})
        callsign = data.get("callsign", sat_name)
        norad_id = data.get("norad_id")
        if norad_id != self._current_norad_id:
            return
        self.tle_status_label.setText(
            f"TLE: Gagal memuat CelesTrak (NORAD {norad_id}). Fallback simulasi. ({message})"
        )
        self._log_terminal(f"[TLE] Gagal NORAD {norad_id}: {message}. Menggunakan simulasi.")
        self._fallback_simulated(data, callsign, reason=message)

    def _fallback_simulated(self, data: dict, callsign: str, reason: str = "") -> None:
        self._satrec = None
        self._tle_line2 = None
        self._real_update_timer.stop()
        self.map_widget.set_simulated(callsign, initial_angle=random.uniform(20.0, 180.0))
        self.val_altitude.setText(data.get("alt", "—"))
        self.val_speed.setText(data.get("spd", "—"))
        self._set_pass_placeholder(
            "Prediksi lintasan tidak tersedia (TLE gagal/tidak tersedia). Tampilan orbit: simulasi."
        )

    def _update_real_position(self) -> None:
        if self._satrec is None or self._current_norad_id is None:
            return
        try:
            now = datetime.now(timezone.utc)
            lat, lon, alt, vel = propagate_position(self._satrec, now)
            self.val_altitude.setText(f"{alt:.1f} km")
            self.val_speed.setText(f"{vel:.2f} km/s")
            info = f"TLE {self._tle_source_mode}"
            self.map_widget.set_real_position((lat, lon), info)
        except Exception:
            return

    # --- pass prediction ---
    def _set_pass_placeholder(self, message: str) -> None:
        self.pass_table.clearSpans()
        self.pass_table.setRowCount(1)
        self.pass_table.setSpan(0, 0, 1, self.pass_table.columnCount())
        item = QTableWidgetItem(message)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        self.pass_table.setItem(0, 0, item)

    def _populate_simulated_pass_schedule(self) -> None:
        passes = [
            ("P-1042", "SADAP-SV09", "22:48:12 UTC", "72° NE", "09m 45s"),
            ("P-1043", "ISS (ZARYA)", "23:14:05 UTC", "58° WSW", "06m 12s"),
            ("P-1044", "LANDSAT-9", "00:22:40 UTC", "84° N", "11m 30s"),
            ("P-1045", "SENTINEL-2A", "01:05:18 UTC", "65° S", "10m 05s"),
        ]
        self.pass_table.clearSpans()
        self.pass_table.setRowCount(len(passes))
        for row, values in enumerate(passes):
            for col, value in enumerate(values):
                self.pass_table.setItem(row, col, QTableWidgetItem(value))

    def _update_pass_schedule(self, satrec, callsign: str) -> None:
        obs = TELEMETRY_OBSERVER or {}
        lat = obs.get("lat")
        lon = obs.get("lon")
        alt_m = obs.get("elevation_m", 0.0)
        if lat is None or lon is None or satrec is None:
            self._set_pass_placeholder("Prediksi lintasan tidak tersedia (observer/TLE tidak valid).")
            return
        try:
            passes = compute_passes(
                satrec,
                float(lat),
                float(lon),
                float(alt_m),
                hours=12,
                step_seconds=30,
                min_elevation_deg=5.0,
            )
        except Exception as exc:  # noqa: BLE001
            self._set_pass_placeholder(f"Prediksi lintasan gagal dihitung: {exc}")
            return

        if not passes:
            self._set_pass_placeholder("Tidak ada lintasan ≥5° dalam 12 jam ke depan untuk stasiun ini.")
            return

        self.pass_table.clearSpans()
        self.pass_table.setRowCount(len(passes))
        for row, p in enumerate(passes):
            aos = p.get("aos")
            los = p.get("los")
            max_el = p.get("max_elev_deg", 0.0)
            max_az = p.get("max_elev_az_deg", 0.0)
            compass = az_to_compass(max_az)
            duration = (los - aos).total_seconds() if aos and los else 0
            dur_m, dur_s = divmod(max(0, int(duration)), 60)
            values = [
                f"P-{row + 1:03d}",
                callsign,
                aos.strftime("%H:%M:%S UTC") if aos else "—",
                f"{max_el:.0f}° {compass}".strip(),
                f"{dur_m:02d}m {dur_s:02d}s",
            ]
            for col, value in enumerate(values):
                self.pass_table.setItem(row, col, QTableWidgetItem(value))

    # --- compatibility & existing behaviors ---
    def select_default(self) -> None:
        self.on_satellite_changed(0)

    def _init_terminal_stream(self) -> None:
        self.terminal_view.setPlainText(
            "\n".join(
                [
                    "[SYSTEM] Ground Station Core v2.4 initialized. S-Band / X-Band phased array online.",
                    "[EPHEMERIS] TLE orbital elements: CelesTrak GP (NORAD) — fetch on satellite selection.",
                    "[DOWNLINK] 2.245 GHz stream synced at 150.2 Mbps. Signal lock confirmed.",
                ]
            )
        )

    def _log_terminal(self, line: str) -> None:
        self.terminal_view.append(line)
        lines = self.terminal_view.toPlainText().splitlines()
        if len(lines) > 80:
            self.terminal_view.setPlainText("\n".join(lines[-40:]))

    def append_telemetry_event(self) -> None:
        sat = self.satellite_combo.currentText().split()[0] if self.satellite_combo.currentText() else "SAT"
        frame_id = random.randint(10000, 99999)
        now_time = datetime.now().strftime("%H:%M:%S")
        events = [
            f"[{now_time}] [{sat}] RX-FRAME #{frame_id}: Doppler shift compensated. Telemetry CRC32 OK.",
            f"[{now_time}] [{sat}] SENSOR-TELEMETRY: Bus voltage 28.4V | Solar array 5.12A | Thermal nominal.",
            f"[{now_time}] [{sat}] DOWNLINK-STREAM: Demodulated 64-APSK packet block #{frame_id}. Signal quality 99.8%.",
            f"[{now_time}] [{sat}] ATTITUDE-CONTROL: Reaction wheels RPM nominal | Star tracker locked.",
        ]
        self.terminal_view.append(random.choice(events))
        lines = self.terminal_view.toPlainText().splitlines()
        if len(lines) > 80:
            self.terminal_view.setPlainText("\n".join(lines[-40:]))
