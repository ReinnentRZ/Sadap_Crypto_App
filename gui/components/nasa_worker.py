"""Qt workers that keep NASA network calls off the GUI thread."""
from PyQt6.QtCore import QObject, QRunnable, pyqtSignal

from core.api.nasa_client import fetch, fetch_image_bytes


class WorkerSignals(QObject):
    finished = pyqtSignal(object)
    failed = pyqtSignal(str)


class NasaFetchWorker(QRunnable):
    """Fetch JSON from a NASA endpoint in the global thread pool."""

    def __init__(self, endpoint: str, params: dict | None = None, **kwargs):
        super().__init__()
        self.endpoint = endpoint
        self.params = params or {}
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self) -> None:
        try:
            self.signals.finished.emit(fetch(self.endpoint, self.params, **self.kwargs))
        except Exception as exc:  # noqa: BLE001 - surfaced to the GUI signal
            self.signals.failed.emit(str(exc))


class NasaImageWorker(QRunnable):
    """Download a NASA image in the global thread pool."""

    def __init__(self, url: str, cache_name: str):
        super().__init__()
        self.url = url
        self.cache_name = cache_name
        self.signals = WorkerSignals()

    def run(self) -> None:
        try:
            payload, from_cache = fetch_image_bytes(self.url, self.cache_name)
            self.signals.finished.emit((payload, from_cache))
        except Exception as exc:  # noqa: BLE001 - surfaced to the GUI signal
            self.signals.failed.emit(str(exc))
