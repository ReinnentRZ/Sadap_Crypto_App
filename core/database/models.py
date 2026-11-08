"""
AeroSat GroundStation - Database Table Schemas & Constants
Defines SQLite relational structure for classified memos, encrypted file catalog,
steganography records, and security audit logs.
"""

SQL_CREATE_MEMOS_TABLE = """
CREATE TABLE IF NOT EXISTS secret_memos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    encrypted_content TEXT NOT NULL,
    vigenere_hint TEXT,
    author TEXT NOT NULL,
    created_at INTEGER NOT NULL
);
"""

SQL_CREATE_FILES_TABLE = """
CREATE TABLE IF NOT EXISTS encrypted_files_meta (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    encrypted_original_filename TEXT NOT NULL,
    file_path TEXT NOT NULL,
    file_size INTEGER NOT NULL,
    file_sha256 TEXT NOT NULL,
    encrypted_at INTEGER NOT NULL
);
"""

SQL_CREATE_STEGO_TABLE = """
CREATE TABLE IF NOT EXISTS stego_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    image_path TEXT NOT NULL,
    encrypted_secret_preview TEXT NOT NULL,
    payload_size INTEGER NOT NULL,
    psnr_db REAL NOT NULL,
    created_at INTEGER NOT NULL
);
"""

SQL_CREATE_AUDIT_TABLE = """
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,
    encrypted_details TEXT NOT NULL,
    operator_callsign TEXT NOT NULL,
    device_info TEXT NOT NULL,
    timestamp INTEGER NOT NULL
);
"""
