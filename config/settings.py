"""
Sadap GroundStation (Sadap Crypto) - System Configuration Settings
"""
from pathlib import Path

# Base Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
ASSETS_DIR = BASE_DIR / "assets"
ICONS_DIR = ASSETS_DIR / "icons"
SAMPLE_IMAGES_DIR = ASSETS_DIR / "sample_images"
STYLES_DIR = ASSETS_DIR / "styles"

# Ensure runtime directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
(DATA_DIR / "keys").mkdir(parents=True, exist_ok=True)
ASSETS_DIR.mkdir(parents=True, exist_ok=True)
ICONS_DIR.mkdir(parents=True, exist_ok=True)
SAMPLE_IMAGES_DIR.mkdir(parents=True, exist_ok=True)
STYLES_DIR.mkdir(parents=True, exist_ok=True)
MODELS_DIR = ASSETS_DIR / "models"
MODELS_DIR.mkdir(parents=True, exist_ok=True)

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
STEGO_HEADER_LEN = 8  # 4 bytes magic + 4 bytes payload length

# Blockchain Settings
BLOCKCHAIN_DIFFICULTY = 3  # Proof of Work prefix: "000"
BLOCKCHAIN_GENESIS_PREV_HASH = "0" * 64
