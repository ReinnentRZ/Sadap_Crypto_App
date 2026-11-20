"""Qt worker that keeps CelesTrak TLE network calls off the GUI thread."""
from PyQt6.QtCore import QObject, QRunnable, pyqtSignal

from core.api.tle_client import fetch_tle


class TleSignals(QObject):
    finished = pyqtSignal(object)
    failed = pyqtSignal(str)


class TleFetchWorker(QRunnable):
    """Fetch TLE for a NORAD catalog number in the global thread pool."""

    def __init__(self, norad_id: int):
        super().__init__()
        self.norad_id = norad_id
        self.signals = TleSignals()

    def run(self) -> None:
        try:
            self.signals.finished.emit(fetch_tle(self.norad_id))
        except Exception as exc:  # noqa: BLE001 - surfaced to the GUI signal
            self.signals.failed.emit(str(exc))
