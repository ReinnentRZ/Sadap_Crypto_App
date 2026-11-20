"""
Sadap GroundStation (Sadap Crypto) - System Configuration Settings
"""
import os
import sys
from pathlib import Path

# Base Paths detection (Frozen .exe vs Development environment)
if getattr(sys, "frozen", False):
    # Running as compiled binary from PyInstaller
    BASE_DIR = Path(sys.executable).resolve().parent
    BUNDLE_DIR = Path(getattr(sys, "_MEIPASS", BASE_DIR))
else:
    # Running from source in development
    BASE_DIR = Path(__file__).resolve().parent.parent
    BUNDLE_DIR = BASE_DIR


def _load_env_file(env_path: Path) -> None:
    """Load KEY=VALUE pairs from .env without overwriting real environment variables."""
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


try:
    from dotenv import load_dotenv
    load_dotenv(BASE_DIR / ".env")
except ImportError:
    _load_env_file(BASE_DIR / ".env")

# Read-only assets directory (prioritize bundle directory, fallback to _internal, then BASE_DIR)
ASSETS_DIR = BUNDLE_DIR / "assets"
if not ASSETS_DIR.exists():
    ASSETS_DIR = BASE_DIR / "_internal" / "assets"
if not ASSETS_DIR.exists():
    ASSETS_DIR = BASE_DIR / "assets"

MAP_DIR = ASSETS_DIR / "map"
ICONS_DIR = ASSETS_DIR / "icons"
SAMPLE_IMAGES_DIR = ASSETS_DIR / "sample_images"
STYLES_DIR = ASSETS_DIR / "styles"
MODELS_DIR = ASSETS_DIR / "models"

# Persistent user data directory (always located next to executable or project root)
DATA_DIR = BASE_DIR / "data"

# Ensure runtime directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
(DATA_DIR / "keys").mkdir(parents=True, exist_ok=True)
ASSETS_DIR.mkdir(parents=True, exist_ok=True)
ICONS_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
STYLES_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR = ASSETS_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

# NASA Open APIs (key is read from .env, DEMO_KEY keeps the app usable without setup)
NASA_API_KEY = os.getenv("NASA_API_KEY", "DEMO_KEY")
NASA_CACHE_DIR = DATA_DIR / "cache" / "nasa"
NASA_CACHE_DIR.mkdir(parents=True, exist_ok=True)
NASA_CACHE_TTL_SECONDS = 900  # 15 minutes

# Database & Ledger File Paths
DB_PATH = DATA_DIR / "vault.db"
BLOCKCHAIN_PATH = DATA_DIR / "blockchain_ledger.json"
BIOMETRIC_TEMPLATE_PATH = DATA_DIR / "keys" / "face_template.npz"

# AI Face Recognition Models
YUNET_MODEL_PATH = MODELS_DIR / "face_detection_yunet.onnx"
SFACE_MODEL_PATH = MODELS_DIR / "face_recognition_sface.onnx"

# Authentication Settings
USB_TOKEN_FILENAME = "sadap.sig"
USB_SIGNATURE_MAGIC = "SADAP-UPLINK-KEY-v1.0"
FACE_COSINE_THRESHOLD = 0.363  # SFace recommended cosine similarity threshold (higher is more similar)
FACE_L2_THRESHOLD = 1.128      # SFace L2 distance threshold (lower is more similar)
PASSWORD_HASH_ALGORITHM = "PBKDF2_SHA256"
PASSWORD_SALT_BYTES = 16
PASSWORD_KDF_ITERATIONS = 200_000

# Cryptography Settings
RSA_KEY_SIZE = 2048
RSA_PUBLIC_EXPONENT = 65537
AES_KEY_SIZE_BYTES = 32  # 256-bit AES
AES_NONCE_SIZE_BYTES = 12  # 96-bit nonce for AES-GCM
AES_CHUNK_SIZE_BYTES = 64 * 1024  # 64 KB buffer for streaming

# Steganography Settings
STEGO_MAGIC_BYTES = b"AERO"
STEGO_HEADER_LEN = 9  # 4 bytes magic + 1 byte flags + 4 bytes payload length

# Blockchain Settings
BLOCKCHAIN_DIFFICULTY = 3  # Proof of Work prefix: "000"
BLOCKCHAIN_GENESIS_PREV_HASH = "0" * 64

# Cover Mode - Indonesian observation targets
SATELLITE_PRESETS = {
    "Jakarta Metropolitan & Port Zone": {
        "lat": -6.2088, "lon": 106.8456, "zoom": 13,
        "coords": "-06° 12' 31\" S, 106° 50' 44\" E",
        "elevation": "8.0 m ASL", "cloud_cover": "12.4%"
    },
    "IKN Nusantara Capital Zone": {
        "lat": -0.9730, "lon": 116.7040, "zoom": 14,
        "coords": "-00° 58' 22\" S, 116° 42' 15\" E",
        "elevation": "45.2 m ASL", "cloud_cover": "18.1%"
    },
    "Surabaya Urban & Port Corridor": {
        "lat": -7.2575, "lon": 112.7521, "zoom": 13,
        "coords": "-07° 15' 27\" S, 112° 45' 08\" E",
        "elevation": "5.0 m ASL", "cloud_cover": "9.8%"
    },
    "Bandung Basin & Highland Belt": {
        "lat": -6.9175, "lon": 107.6191, "zoom": 13,
        "coords": "-06° 55' 03\" S, 107° 37' 09\" E",
        "elevation": "768.0 m ASL", "cloud_cover": "14.2%"
    },
    "Medan Metropolitan & Strait Coast": {
        "lat": 3.5952, "lon": 98.6722, "zoom": 13,
        "coords": "03° 35' 43\" N, 098° 40' 20\" E",
        "elevation": "25.0 m ASL", "cloud_cover": "22.5%"
    },
    "Makassar Coastal & Port Zone": {
        "lat": -5.1408, "lon": 119.4319, "zoom": 13,
        "coords": "-05° 08' 27\" S, 119° 25' 55\" E",
        "elevation": "12.0 m ASL", "cloud_cover": "7.4%"
    },
    "Denpasar & Bali Urban Belt": {
        "lat": -8.6500, "lon": 115.2167, "zoom": 13,
        "coords": "-08° 39' 00\" S, 115° 13' 00\" E",
        "elevation": "4.0 m ASL", "cloud_cover": "6.1%"
    },
    "Jayapura & Sentani Corridor": {
        "lat": -2.5335, "lon": 140.7020, "zoom": 13,
        "coords": "-02° 32' 01\" S, 140° 42' 07\" E",
        "elevation": "18.0 m ASL", "cloud_cover": "31.6%"
    },
    "Indonesia Archipelago Overview": {
        "lat": -2.5489, "lon": 118.0149, "zoom": 5,
        "coords": "-02° 32' 56\" S, 118° 00' 54\" E",
        "elevation": "Regional mosaic", "cloud_cover": "Variable"
    },
}

SATELLITES_DATA = {
    "SADAP-SV09 (National Remote Sensing)": {"callsign": "SADAP-SV09", "alt": "542.4 km", "spd": "7.61 km/s", "freq": "2.245 GHz (S-Band)", "inc": "97.4°"},
    "ISS (ZARYA) - Space Station": {"callsign": "ISS-ALPHA", "alt": "418.2 km", "spd": "7.66 km/s", "freq": "145.80 MHz (VHF)", "inc": "51.6°"},
    "LANDSAT-9 (USGS/NASA)": {"callsign": "LANDSAT-9", "alt": "705.0 km", "spd": "7.50 km/s", "freq": "8.212 GHz (X-Band)", "inc": "98.2°"},
    "SENTINEL-2A (Copernicus ESA)": {"callsign": "SENTINEL-2A", "alt": "786.1 km", "spd": "7.45 km/s", "freq": "8.045 GHz (X-Band)", "inc": "98.5°"},
    "NOAA-20 (JPSS-1 Polar Weather)": {"callsign": "NOAA-20", "alt": "824.0 km", "spd": "7.42 km/s", "freq": "1.707 GHz (L-Band)", "inc": "98.7°"},
}
