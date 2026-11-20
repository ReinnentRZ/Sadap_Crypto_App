"""Local weather forecast page backed by the public Open-Meteo API (global)."""
from __future__ import annotations

from PyQt6.QtCore import Qt, QThreadPool, pyqtSignal
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDoubleSpinBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from config.settings import SATELLITE_PRESETS
from core.api.weather_client import WeatherResponse
from core.api.weather_endpoints import describe_weather_code
from gui.components.weather_map_picker import WeatherLocationPickerDialog
from gui.components.weather_worker import GeocodeSearchWorker, WeatherFetchWorker


class CoverWeatherForecastPage(QWidget):
    """Shows current conditions, 7-day and 3-hourly forecasts for any global target."""

    use_map_target_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._forecast_worker: WeatherFetchWorker | None = None
        self._geocode_worker: GeocodeSearchWorker | None = None
        self._coords_by_label: dict[str, tuple[float, float]] = {
            name: (preset["lat"], preset["lon"]) for name, preset in SATELLITE_PRESETS.items()
        }
        self._geocode_results: list[dict] = []
        self._latitude, self._longitude = next(iter(self._coords_by_label.values()))
        self._location_label_text = next(iter(self._coords_by_label.keys()))
        self._init_ui()
        self._sync_coord_inputs(self._latitude, self._longitude)
        self.refresh()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------
    def _init_ui(self) -> None:
        main = QVBoxLayout(self)
        main.setContentsMargins(18, 16, 18, 16)
        main.setSpacing(10)

        title = QLabel("WEATHER FORECAST")
        title.setStyleSheet("font-size: 18px; font-weight: 800; color: #0F172A;")
        subtitle = QLabel(
            "Prakiraan cuaca global melalui Open-Meteo (API publik, tanpa API key). "
            "Pilih preset, cari nama lokasi, masukkan koordinat, atau pilih via peta."
        )
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color: #64748B; font-size: 12px;")
        main.addWidget(title)
        main.addWidget(subtitle)

        # --- Preset + map actions ---
        controls = QHBoxLayout()
        controls.addWidget(QLabel("<b>Lokasi:</b>"))
        self.city_combo = QComboBox()
        self.city_combo.addItems(SATELLITE_PRESETS.keys())
        self.city_combo.currentTextChanged.connect(self._on_location_changed)
        controls.addWidget(self.city_combo, stretch=1)

        self.btn_map_target = QPushButton("🎯 Gunakan Target Peta")
        self.btn_map_target.setObjectName("secondaryBtn")
        self.btn_map_target.setStyleSheet("padding: 7px 12px;")
        self.btn_map_target.clicked.connect(self.use_map_target_requested.emit)
        controls.addWidget(self.btn_map_target)

        self.btn_pick_map = QPushButton("🗺️ Pilih di Peta…")
        self.btn_pick_map.setObjectName("secondaryBtn")
        self.btn_pick_map.setStyleSheet("padding: 7px 12px;")
        self.btn_pick_map.clicked.connect(self._open_map_picker)
        controls.addWidget(self.btn_pick_map)

        self.btn_refresh = QPushButton("⟳ Refresh Forecast")
        self.btn_refresh.setObjectName("primaryBtn")
        self.btn_refresh.setStyleSheet("padding: 7px 14px; font-weight: 700;")
        self.btn_refresh.clicked.connect(self.refresh)
        controls.addWidget(self.btn_refresh)
        main.addLayout(controls)

        # --- Manual coordinates ---
        coord_group = QGroupBox("Koordinat Manual")
        coord_layout = QHBoxLayout(coord_group)
        coord_layout.setContentsMargins(10, 8, 10, 8)
        coord_layout.addWidget(QLabel("Latitude:"))
        self.lat_spin = QDoubleSpinBox()
        self.lat_spin.setRange(-90.0, 90.0)
        self.lat_spin.setDecimals(6)
        self.lat_spin.setSingleStep(0.01)
        self.lat_spin.setMinimumWidth(130)
        coord_layout.addWidget(self.lat_spin)
        coord_layout.addWidget(QLabel("Longitude:"))
        self.lon_spin = QDoubleSpinBox()
        self.lon_spin.setRange(-180.0, 180.0)
        self.lon_spin.setDecimals(6)
        self.lon_spin.setSingleStep(0.01)
        self.lon_spin.setMinimumWidth(130)
        coord_layout.addWidget(self.lon_spin)

        self.btn_apply_coords = QPushButton("Terapkan Koordinat")
        self.btn_apply_coords.setObjectName("secondaryBtn")
        self.btn_apply_coords.clicked.connect(self._apply_manual_coordinates)
        coord_layout.addWidget(self.btn_apply_coords)
        coord_layout.addStretch()
        main.addWidget(coord_group)

        # --- Geocoding search ---
        search_group = QGroupBox("Cari Lokasi (Geocoding Open-Meteo)")
        search_layout = QVBoxLayout(search_group)
        search_layout.setContentsMargins(10, 8, 10, 8)
        search_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Ketik nama kota/daerah/negara, mis. London, Kyoto, Denpasar…")
        self.search_edit.returnPressed.connect(self._search_location)
        search_row.addWidget(self.search_edit, stretch=1)
        self.btn_search = QPushButton("🔎 Cari Lokasi")
        self.btn_search.setObjectName("secondaryBtn")
        self.btn_search.clicked.connect(self._search_location)
        search_row.addWidget(self.btn_search)
        search_layout.addLayout(search_row)

        self.search_results = QListWidget()
        self.search_results.setMaximumHeight(110)
        self.search_results.setAlternatingRowColors(True)
        self.search_results.itemClicked.connect(self._on_geocode_selected)
        self.search_results.setVisible(False)
        self.search_results.setStyleSheet(
            """
            QListWidget {
                background-color: #FFFFFF;
                alternate-background-color: #F8FAFC;
                color: #0F172A;
                border: 1px solid #CBD5E1;
                border-radius: 6px;
                padding: 4px;
                outline: none;
            }
            QListWidget::item {
                padding: 6px 8px;
                border-radius: 4px;
                color: #0F172A;
                background: transparent;
            }
            QListWidget::item:hover {
                background-color: #F1F5F9;
                color: #0284C7;
            }
            QListWidget::item:selected {
                background-color: #E0F2FE;
                color: #0369A1;
                font-weight: 600;
            }
            """
        )
        search_layout.addWidget(self.search_results)

        self.search_status = QLabel("")
        self.search_status.setStyleSheet("color: #64748B; font-size: 11px;")
        search_layout.addWidget(self.search_status)
        main.addWidget(search_group)

        # --- Current conditions ---
        current_card = QFrame()
        current_card.setObjectName("currentWeatherCard")
        current_card.setStyleSheet(
            """
            QFrame#currentWeatherCard {
                background-color: #FFFFFF;
                border: 1px solid #E2E8F0;
                border-radius: 8px;
            }
            """
        )
        current_layout = QHBoxLayout(current_card)
        current_layout.setContentsMargins(18, 12, 18, 12)
        current_layout.setSpacing(16)

        self.icon_label = QLabel("⏳")
        self.icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.icon_label.setFixedWidth(60)
        self.icon_label.setStyleSheet("font-size: 42px;")

        self.temp_label = QLabel("—°")
        self.temp_label.setStyleSheet("font-size: 34px; font-weight: 800; color: #0284C7;")

        details = QVBoxLayout()
        details.setSpacing(2)
        self.condition_label = QLabel("Memuat kondisi terkini...")
        self.condition_label.setStyleSheet("font-size: 15px; font-weight: 700; color: #0F172A;")
        self.location_label = QLabel("—")
        self.location_label.setStyleSheet("font-size: 11px; color: #64748B;")
        self.time_label = QLabel("—")
        self.time_label.setStyleSheet("font-size: 11px; color: #94A3B8;")
        details.addWidget(self.condition_label)
        details.addWidget(self.location_label)
        details.addWidget(self.time_label)

        current_layout.addWidget(self.icon_label)
        current_layout.addWidget(self.temp_label)
        current_layout.addLayout(details, stretch=1)
        main.addWidget(current_card)

        metrics = QHBoxLayout()
        metrics.setSpacing(8)
        self.metric_feels = QLabel("Terasa: —")
        self.metric_humidity = QLabel("Kelembapan: —")
        self.metric_wind = QLabel("Angin: —")
        self.metric_rain = QLabel("Curah hujan: —")
        for label in (
            self.metric_feels,
            self.metric_humidity,
            self.metric_wind,
            self.metric_rain,
        ):
            label.setStyleSheet(
                "background-color: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 6px; "
                "padding: 7px 10px; font-size: 11px; color: #334155;"
            )
            metrics.addWidget(label)
        main.addLayout(metrics)

        self.status_label = QLabel("Memuat data Open-Meteo...")
        self.status_label.setStyleSheet("color: #64748B; font-size: 11px;")
        main.addWidget(self.status_label)

        self.tabs = QTabWidget()
        self.daily_table = self._make_table(
            ["Tanggal", "Kondisi", "Min", "Maks", "Hujan", "Prob.", "Angin", "Matahari"],
            stretch_columns=(1,),
        )
        self.hourly_table = self._make_table(
            ["Waktu", "Kondisi", "Suhu", "Prob. Hujan", "Angin"],
            stretch_columns=(1,),
        )
        self.tabs.addTab(self.daily_table, "Prakiraan 7 Hari")
        self.tabs.addTab(self.hourly_table, "Prakiraan 3 Jam")
        main.addWidget(self.tabs, stretch=1)

    @staticmethod
    def _make_table(headers: list[str], stretch_columns: tuple[int, ...] = ()) -> QTableWidget:
        table = QTableWidget()
        table.setColumnCount(len(headers))
        table.setHorizontalHeaderLabels(headers)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setAlternatingRowColors(True)
        header = table.horizontalHeader()
        for col in range(len(headers)):
            header.setSectionResizeMode(
                col,
                QHeaderView.ResizeMode.Stretch if col in stretch_columns else QHeaderView.ResizeMode.ResizeToContents,
            )
        table.verticalHeader().setVisible(False)
        table.setMinimumHeight(180)
        return table

    # ------------------------------------------------------------------
    # Location handling
    # ------------------------------------------------------------------
    def _sync_coord_inputs(self, lat: float, lon: float) -> None:
        self.lat_spin.blockSignals(True)
        self.lon_spin.blockSignals(True)
        self.lat_spin.setValue(float(lat))
        self.lon_spin.setValue(float(lon))
        self.lat_spin.blockSignals(False)
        self.lon_spin.blockSignals(False)

    def _on_location_changed(self, name: str) -> None:
        coords = self._coords_by_label.get(name)
        if coords is None:
            return
        self._latitude, self._longitude = coords
        self._location_label_text = name
        self._sync_coord_inputs(*coords)
        self.refresh()

    def apply_map_target(self, latitude: float, longitude: float, label: str) -> None:
        """Adopt coordinates (e.g. from Earth Observation map or picker)."""
        self._set_location(latitude, longitude, label, refresh=True)

    def _set_location(
        self,
        latitude: float,
        longitude: float,
        label: str,
        refresh: bool = True,
        select_in_combo: bool = True,
    ) -> None:
        lat = max(-90.0, min(90.0, float(latitude)))
        lon = max(-180.0, min(180.0, float(longitude)))
        display = label or f"Koordinat ({lat:.4f}, {lon:.4f})"
        self._latitude, self._longitude = lat, lon
        self._location_label_text = display
        self._coords_by_label[display] = (lat, lon)
        self._sync_coord_inputs(lat, lon)

        if select_in_combo:
            self.city_combo.blockSignals(True)
            if self.city_combo.findText(display) < 0:
                self.city_combo.insertItem(0, display)
            self.city_combo.setCurrentText(display)
            self.city_combo.blockSignals(False)

        if refresh:
            self.refresh()

    def _apply_manual_coordinates(self) -> None:
        lat = self.lat_spin.value()
        lon = self.lon_spin.value()
        label = f"Koordinat Manual ({lat:.4f}, {lon:.4f})"
        self._set_location(lat, lon, label, refresh=True)

    def _open_map_picker(self) -> None:
        dialog = WeatherLocationPickerDialog(
            self._latitude,
            self._longitude,
            self._location_label_text,
            parent=self,
        )
        if dialog.exec() == WeatherLocationPickerDialog.DialogCode.Accepted and dialog.selected:
            lat, lon, label = dialog.selected
            self._set_location(lat, lon, label, refresh=True)

    # ------------------------------------------------------------------
    # Geocoding
    # ------------------------------------------------------------------
    def _search_location(self) -> None:
        query = self.search_edit.text().strip()
        if not query:
            self.search_status.setText("Masukkan nama lokasi untuk dicari.")
            return

        self.search_status.setText("Mencari lokasi…")
        self.btn_search.setEnabled(False)
        self.search_results.setVisible(False)
        self.search_results.clear()
        self._geocode_results = []

        self._geocode_worker = GeocodeSearchWorker(query)
        self._geocode_worker.signals.finished.connect(self._on_geocode_results)
        self._geocode_worker.signals.failed.connect(self._on_geocode_error)
        QThreadPool.globalInstance().start(self._geocode_worker)

    def _on_geocode_error(self, message: str) -> None:
        self.btn_search.setEnabled(True)
        self.search_status.setText(f"Pencarian gagal: {message}")

    def _on_geocode_results(self, results: object) -> None:
        self.btn_search.setEnabled(True)
        items = list(results) if isinstance(results, list) else []
        self._geocode_results = [r for r in items if isinstance(r, dict)]
        self.search_results.clear()

        if not self._geocode_results:
            self.search_results.setVisible(False)
            self.search_status.setText("Lokasi tidak ditemukan. Coba kata kunci lain.")
            return

        for result in self._geocode_results:
            name = result.get("name", "Lokasi")
            parts = [p for p in [result.get("admin1"), result.get("country")] if p]
            suffix = ", ".join(parts)
            lat = result.get("latitude", 0.0)
            lon = result.get("longitude", 0.0)
            text = f"{name}" + (f", {suffix}" if suffix else "") + f"  ({lat:.4f}, {lon:.4f})"
            item = QListWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, result)
            self.search_results.addItem(item)

        self.search_results.setVisible(True)
        self.search_status.setText(f"Ditemukan {len(self._geocode_results)} lokasi. Klik untuk memilih.")

    def _on_geocode_selected(self, item: QListWidgetItem) -> None:
        result = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(result, dict):
            return
        name = result.get("name", "Lokasi")
        parts = [p for p in [result.get("admin1"), result.get("country")] if p]
        label = ", ".join([name] + parts) if parts else name
        lat = result.get("latitude", self._latitude)
        lon = result.get("longitude", self._longitude)
        self.search_status.setText(f"Lokasi dipilih: {label}")
        self._set_location(lat, lon, label, refresh=True)

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------
    def refresh(self) -> None:
        self.status_label.setText("Memuat data Open-Meteo...")
        self._forecast_worker = WeatherFetchWorker(self._latitude, self._longitude)
        self._forecast_worker.signals.finished.connect(self._on_data)
        self._forecast_worker.signals.failed.connect(self._on_error)
        QThreadPool.globalInstance().start(self._forecast_worker)

    def _on_error(self, message: str) -> None:
        self.status_label.setText(f"Gagal memuat prakiraan cuaca: {message}")

    def _on_data(self, response: WeatherResponse) -> None:
        data = response.data
        current = data.get("current") or {}
        units = data.get("current_units") or {}
        temp_unit = units.get("temperature_2m", "°C")
        wind_unit = units.get("wind_speed_10m", "km/h")

        description, icon = describe_weather_code(current.get("weather_code"))
        self.icon_label.setText(icon)
        self.temp_label.setText(f"{self._fmt(current.get('temperature_2m'))}{temp_unit}")
        self.condition_label.setText(description)
        self.location_label.setText(
            f"{self._location_label_text} · {data.get('latitude', self._latitude):.4f}, "
            f"{data.get('longitude', self._longitude):.4f}"
        )
        self.time_label.setText(
            f"Lokal: {current.get('time', '—')} · {data.get('timezone_abbreviation') or data.get('timezone', '—')}"
        )

        self.metric_feels.setText(f"Terasa: {self._fmt(current.get('apparent_temperature'))}{temp_unit}")
        self.metric_humidity.setText(f"Kelembapan: {self._fmt(current.get('relative_humidity_2m'))}%")
        self.metric_wind.setText(
            f"Angin: {self._fmt(current.get('wind_speed_10m'))} {wind_unit} "
            f"({self._fmt(current.get('wind_direction_10m'))}°)"
        )
        self.metric_rain.setText(f"Curah hujan: {self._fmt(current.get('precipitation'))} mm")

        mode = "CACHE" if response.from_cache else "LIVE"
        self.status_label.setText(
            f"Open-Meteo · {mode} · diperbarui {response.fetched_at} · "
            f"zonasi {data.get('timezone', 'auto')}"
        )

        self._populate_daily(data.get("daily") or {}, wind_unit)
        self._populate_hourly(data.get("hourly") or {}, current, temp_unit, wind_unit)

    @staticmethod
    def _fmt(value: object) -> str:
        if value is None or value == "":
            return "—"
        if isinstance(value, (int, float)):
            return f"{value:g}"
        return str(value)

    @staticmethod
    def _at(section: dict, key: str, index: int, default: object = "—") -> object:
        values = section.get(key) or []
        if 0 <= index < len(values):
            return values[index]
        return default

    def _populate_daily(self, daily: dict, wind_unit: str) -> None:
        dates = daily.get("time") or []
        self.daily_table.setRowCount(len(dates))
        for row, date in enumerate(dates):
            description, icon = describe_weather_code(self._at(daily, "weather_code", row))
            sunrise = str(self._at(daily, "sunrise", row))
            sunset = str(self._at(daily, "sunset", row))
            values = [
                str(date),
                f"{icon} {description}",
                f"{self._fmt(self._at(daily, 'temperature_2m_min', row))}°",
                f"{self._fmt(self._at(daily, 'temperature_2m_max', row))}°",
                f"{self._fmt(self._at(daily, 'precipitation_sum', row))} mm",
                f"{self._fmt(self._at(daily, 'precipitation_probability_max', row))}%",
                f"{self._fmt(self._at(daily, 'wind_speed_10m_max', row))} {wind_unit}",
                f"{sunrise[11:] or '—'} / {sunset[11:] or '—'}",
            ]
            for col, value in enumerate(values):
                self.daily_table.setItem(row, col, QTableWidgetItem(value))

    def _populate_hourly(
        self, hourly: dict, current: dict, temp_unit: str, wind_unit: str
    ) -> None:
        times = hourly.get("time") or []
        current_hour = str(current.get("time", ""))[:13]
        start = next((i for i, value in enumerate(times) if value[:13] >= current_hour), 0)
        indexes = list(range(start, min(start + 24, len(times)), 3))

        self.hourly_table.setRowCount(len(indexes))
        for row, index in enumerate(indexes):
            description, icon = describe_weather_code(self._at(hourly, "weather_code", index))
            values = [
                str(self._at(hourly, "time", index))[11:] or "—",
                f"{icon} {description}",
                f"{self._fmt(self._at(hourly, 'temperature_2m', index))}{temp_unit}",
                f"{self._fmt(self._at(hourly, 'precipitation_probability', index))}%",
                f"{self._fmt(self._at(hourly, 'wind_speed_10m', index))} {wind_unit}",
            ]
            for col, value in enumerate(values):
                cell = QTableWidgetItem(value)
                if col == 3 and self._high_rain_chance(hourly.get("precipitation_probability", []), index):
                    cell.setForeground(Qt.GlobalColor.darkMagenta)
                self.hourly_table.setItem(row, col, cell)

    @staticmethod
    def _high_rain_chance(values: list, index: int) -> bool:
        try:
            return 0 <= index < len(values) and float(values[index]) >= 70
        except (TypeError, ValueError):
            return False
