"""Qt worker for Open-Meteo forecast requests."""
from PyQt6.QtCore import QObject, QRunnable, pyqtSignal

from core.api.weather_client import fetch_forecast


class WeatherSignals(QObject):
    finished = pyqtSignal(object)
    failed = pyqtSignal(str)


class WeatherFetchWorker(QRunnable):
    """Fetch a forecast in the global thread pool so the GUI never blocks."""

    def __init__(self, latitude: float, longitude: float, forecast_days: int = 7):
        super().__init__()
        self.latitude = latitude
        self.longitude = longitude
        self.forecast_days = forecast_days
        self.signals = WeatherSignals()

    def run(self) -> None:
        try:
            response = fetch_forecast(self.latitude, self.longitude, self.forecast_days)
            self.signals.finished.emit(response)
        except Exception as exc:  # noqa: BLE001 - surfaced to the GUI signal
            self.signals.failed.emit(str(exc))
