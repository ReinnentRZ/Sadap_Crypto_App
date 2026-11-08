"""
AeroSat GroundStation (Sadap Crypto) - Main Application Entry Point
A dual-mode chameleon security application featuring plausible deniability,
zero-trust biometric authentication, modern and classical super-cryptography,
AES-256 file encryption, LSB satellite steganography, and an immutable blockchain ledger.
"""
import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication

# Ensure project root is in Python module path
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import STYLES_DIR
from gui.main_cover_window import MainCoverWindow
from core.utils.logger import get_logger

logger = get_logger("AeroSatMain")


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
    logger.info("Initializing AeroSat GroundStation System...")
    app = QApplication(sys.argv)
    app.setApplicationName("AeroSat GroundStation")
    app.setOrganizationName("AeroSat Security Labs")

    # Apply White/Light Aerospace Theme
    load_stylesheet(app)

    # Launch in Public Cover Mode
    window = MainCoverWindow()
    window.show()

    logger.info("Cover Mode interface online. Standing by for telemetry and operator commands.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
