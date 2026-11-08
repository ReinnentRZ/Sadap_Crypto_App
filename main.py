"""
Sadap GroundStation (Sadap Crypto) - Main Application Entry Point
A dual-mode chameleon application featuring:
1. Public Portal: Legitimate Operator Login & Registration with SQLite PBKDF2 hash.
2. Public Cover Mode: Authentic, dense Satellite Earth Observation & Telemetry Console.
3. Secret Mode: Zero-Trust 3-Factor (USB + Face AI + Passcode) Covert Cryptography Vault.
"""
import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication

# Ensure project root is in Python module path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import STYLES_DIR
from gui.normal_login_window import NormalLoginWindow
from gui.main_cover_window import MainCoverWindow
from core.utils.logger import get_logger

logger = get_logger("SadapMain")


class SadapApplicationController:
    """Manages application lifecycle and transitions between Login, Cover, and Covert Vault."""

    def __init__(self, app: QApplication):
        self.app = app
        self.login_window: NormalLoginWindow | None = None
        self.cover_window: MainCoverWindow | None = None

    def start(self):
        """Start with the normal operator login portal."""
        self.show_login_portal()

    def show_login_portal(self):
        """Display the operator login and registration dialog."""
        if self.cover_window:
            self.cover_window.close()
            self.cover_window = None

        self.login_window = NormalLoginWindow()
        self.login_window.login_successful.connect(self._on_login_success)
        self.login_window.show()

    def _on_login_success(self, operator_data: dict):
        """Open the Public Cover Console upon successful regular login in full screen."""
        logger.info(f"Transitioning to Cover Mode for operator: {operator_data.get('username')}")
        self.cover_window = MainCoverWindow(operator_data=operator_data)
        self.cover_window.sign_out_requested.connect(self.show_login_portal)
        self.cover_window.showMaximized()


def load_stylesheet(app: QApplication):
    """Load and apply light aerospace QSS theme."""
    qss_file = STYLES_DIR / "light_theme.qss"
    if qss_file.exists():
        try:
            with open(qss_file, "r", encoding="utf-8") as f:
                stylesheet = f.read()
                app.setStyleSheet(stylesheet)
                logger.info("Aerospace light theme applied successfully.")
        except Exception as e:
            logger.warning(f"Could not load stylesheet: {e}")


def main():
    logger.info("Initializing Sadap GroundStation System...")
    app = QApplication(sys.argv)
    app.setApplicationName("Sadap GroundStation")
    app.setOrganizationName("Sadap Security Labs")

    # Apply White/Light Aerospace Theme
    load_stylesheet(app)

    # Initialize Controller and start portal
    controller = SadapApplicationController(app)
    controller.start()

    logger.info("Sadap GroundStation online. Standing by for operator sign-in.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
