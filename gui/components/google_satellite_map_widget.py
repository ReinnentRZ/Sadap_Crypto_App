"""
Sadap GroundStation - Interactive Google Maps & Satellite Observation Canvas Widget
Embeds interactive Google Maps Satellite and ESRI World Imagery tiles using QWebEngineView.
Supports smooth panning, dynamic zooming, layer switching, and tactical reticle overlays.
"""
from pathlib import Path
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QSizePolicy
from PyQt6.QtCore import QUrl, QTimer
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings, QWebEnginePage

from core.utils.logger import get_logger
from config.settings import MAP_DIR, ASSETS_DIR

logger = get_logger("GoogleSatMap")


class MapWebEnginePage(QWebEnginePage):
    """Custom web engine page to capture JavaScript logs and network events."""

    def javaScriptConsoleMessage(self, level, message, lineNumber, sourceID):
        # Forward meaningful JS messages to Python logger
        if "Uncaught" in message or "Error" in message:
            logger.error(f"[MapJS Line {lineNumber}]: {message}")
        else:
            logger.debug(f"[MapJS Line {lineNumber}]: {message}")


class GoogleSatelliteMapWidget(QWidget):
    """Interactive Google Maps and Satellite Imagery Observation Widget."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(480, 320)

        # Robust path resolution for development and compiled binary
        map_path = MAP_DIR / "map_viewer.html"
        if not map_path.exists():
            map_path = ASSETS_DIR / "map" / "map_viewer.html"
        if not map_path.exists():
            map_path = Path(__file__).resolve().parent.parent.parent / "assets" / "map" / "map_viewer.html"
        self.html_file = map_path

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.web_view = QWebEngineView(self)
        self.web_view.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        # Attach custom page
        self.page = MapWebEnginePage(self.web_view)
        self.web_view.setPage(self.page)

        # Configure WebEngine Settings for seamless tile streaming
        settings = self.web_view.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.ScrollAnimatorEnabled, True)

        self.web_view.loadFinished.connect(self._on_load_finished)
        layout.addWidget(self.web_view)

        self._load_map()

    def _load_map(self):
        """Load local Leaflet map template with Google Maps satellite layers."""
        if self.html_file.exists():
            url = QUrl.fromLocalFile(str(self.html_file))
            self.web_view.setUrl(url)
            logger.info(f"Loaded satellite map viewer from {self.html_file}")
        else:
            logger.error(f"Map template file not found: {self.html_file}")

    def _on_load_finished(self, ok: bool):
        """Called when HTML and Leaflet scripts finish loading."""
        if ok:
            logger.info("Satellite Map WebEngine canvas loaded successfully.")
            # Trigger Leaflet invalidateSize after layout rendering settles
            QTimer.singleShot(300, self.invalidate_map_size)
        else:
            logger.error("Failed to load Satellite Map WebEngine canvas.")

    def resizeEvent(self, event):
        """Ensure Leaflet map tiles dynamically re-fit on window or container resize."""
        super().resizeEvent(event)
        self.invalidate_map_size()

    def invalidate_map_size(self):
        """Trigger Leaflet container size invalidation."""
        js = "if (typeof map !== 'undefined' && map.invalidateSize) { map.invalidateSize(); }"
        self.web_view.page().runJavaScript(js)

    def fly_to_coordinates(self, lat: float, lon: float, zoom: int = 14):
        """Smoothly animate map view to specified latitude, longitude, and zoom level."""
        script = f"flyToLocation({lat}, {lon}, {zoom});"
        self.web_view.page().runJavaScript(script)
