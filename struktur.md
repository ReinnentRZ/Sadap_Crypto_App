# Struktur Direktori & File Proyek: AeroSat GroundStation

Dokumen ini menjelaskan struktur direktori, penataan file, serta pembagian tanggung jawab (*separation of concerns*) untuk codebase **AeroSat GroundStation (Sadap Crypto)**.

---

## 1. Visualisasi Pohon Direktori

```text
Sadap-Crypto-App/
│
├── .venv/                          # Virtual environment Python 3.13
│
├── assets/                         # Asset statis, gambar, dan stylesheet GUI
│   ├── icons/                      # Ikon antarmuka (satelit, kunci, shield, kamera, dsb.)
│   ├── sample_images/              # Citra satelit contoh untuk demo steganografi
│   └── styles/
│       └── light_theme.qss         # Stylesheet tema putih/terang minimalis PyQt6
│
├── config/                         # Konfigurasi aplikasi
│   ├── __init__.py
│   └── settings.py                 # Parameter sistem (RSA key size, AES parameters, PoW difficulty)
│
├── core/                           # Logika bisnis inti & algoritma kriptografi
│   ├── __init__.py
│   │
│   ├── auth/                       # Modul Gatekeeper (3-Factor Authentication)
│   │   ├── __init__.py
│   │   ├── usb_dongle.py           # Deteksi hardware USB & pembacaan signature key
│   │   ├── face_recog.py           # Face detection & landmark matching (OpenCV)
│   │   └── hasher.py               # Algoritma hash password (Argon2 / PBKDF2)
│   │
│   ├── crypto/                     # Modul Enkripsi & Dekripsi
│   │   ├── __init__.py
│   │   ├── vigenere.py             # Extended Vigenère Cipher (ASCII printable)
│   │   ├── rsa_engine.py           # Pembangkit kunci RSA & RSA-OAEP engine
│   │   ├── super_text_cipher.py    # Pipeline Super-Enkripsi Teks (Vigenère + RSA)
│   │   └── file_aes.py             # AES-256-GCM file stream encryptor/decryptor
│   │
│   ├── stego/                      # Modul Steganografi Citra Satelit
│   │   ├── __init__.py
│   │   └── lsb_engine.py           # Penyisip dan ekstraktor bit LSB pada citra PNG/BMP
│   │
│   ├── database/                   # Modul Penyimpanan Terenkripsi
│   │   ├── __init__.py
│   │   ├── db_manager.py           # SQLite connection & CRUD dengan field-level encryption
│   │   └── models.py               # Definisi skema tabel data (memos, files, audit)
│   │
│   ├── blockchain/                 # Modul Ledger Integritas Aset
│   │   ├── __init__.py
│   │   ├── block.py                # Struktur objek Block (Index, PrevHash, Data, Nonce, Hash)
│   │   ├── chain.py                # Rantai Blockchain, Proof of Work, validasi integritas
│   │   └── asset_tracker.py        # Pencatatan dan verifikasi hash aset dokumen intelijen
│   │
│   └── utils/                      # Fungsi pembantu umum
│       ├── __init__.py
│       ├── crypto_helpers.py       # Helper konversi byte, hex, base64, dan random sagilt
│       └── logger.py               # Logging aktivitas sistem
│
├── data/                           # Direktori penyimpanan data lokal (dikecualikan dari git) 
│   ├── vault.db                    # Basis data SQLite terenkripsi lokal
│   ├── blockchain_ledger.json      # File persistensi rantai blok
│   └── keys/                       # Penyimpanan kunci publik/privat terdaftar
│
├── gui/                            # Antarmuka Pengguna Berbasis PyQt6 (Tema Terang)
│   ├── __init__.py
│   ├── main_cover_window.py        # Mode Publik: Konsol Stasiun Satelit & Peta Bumi
│   ├── auth_dialog.py              # Modal Dialog: Verifikasi USB + Kamera Wajah + Passcode
│   ├── secret_dashboard.py         # Mode Rahasia: Dashboard Tab Kriptografi Utama
│   │
│   ├── tabs/                       # Tab-tab fungsional dalam Dashboard Rahasia
│   │   ├── __init__.py
│   │   ├── tab_super_text.py       # Tab Super-Enkripsi Teks (Vigenère + RSA)
│   │   ├── tab_file_crypto.py      # Tab Enkripsi File (AES-256-GCM)
│   │   ├── tab_stego_lab.py        # Tab Steganografi Citra Satelit LSB
│   │   ├── tab_database_vault.py   # Tab Penjelajah Data Terenkripsi
│   │   └── tab_blockchain_view.py  # Tab Penjelajah Blok & Audit Integritas
│   │
│   └── components/                 # Komponen UI modular
│       ├── __init__.py
│       ├── camera_widget.py        # Widget preview feed webcam untuk face scan
│       ├── satellite_map_widget.py # Widget peta simulasi stasiun bumi
│       └── block_card_widget.py    # Widget visualisasi kartu blok blockchain
│
├── tools/                          # Script utilitas administratif & penyiapan
│   ├── setup_dongle.py             # Script CLI untuk mendaftarkan USB Flashdisk menjadi Dongle resmi
│   └── register_face.py            # Script CLI untuk merekam wajah operator terdaftar
│
├── tests/                          # Automated Unit & Integration Tests
│   ├── __init__.py
│   ├── test_auth.py                # Pengujian deteksi USB, face matching, dan hasher
│   ├── test_super_crypto.py        # Pengujian Vigenère + RSA (enkripsi & dekripsi bolak-balik)
│   ├── test_file_aes.py            # Pengujian AES file crypto & integritas tag
│   ├── test_stego.py               # Pengujian penyisipan & ekstraksi bit LSB
│   ├── test_database.py            # Pengujian enkripsi level field pada SQLite
│   └── test_blockchain.py          # Pengujian penambangan blok, rantai, dan deteksi tampering
│
├── main.py                         # File Entry Point utama aplikasi
├── requirements.txt                # Daftar pustaka Python yang dibutuhkan
├── context.md                      # Dokumen penjelasan konteks, kegunaan, dan konsep sistem
├── planning.md                     # Dokumen roadmap langkah kerja dan output konkret
└── struktur.md                     # Dokumen penjelasan arsitektur file & direktori (file ini)
```

---

## 2. Rincian Tanggung Jawab Tiap Folder & Modul

### 1. `config/`
* **Tanggung Jawab**: Menyimpan seluruh konfigurasi global yang bersifat statis atau parameter operasional.
* **File Utama**:
  - `settings.py`: Berisi konstanta panjang kunci RSA (2048/4096), ukuran nonce AES (12 byte), algoritma hash default (Argon2id/PBKDF2), tingkat kesulitan Proof of Work blockchain (misal prefix 4 nol `"0000"`), serta path lokasi penyimpanan data.

---

### 2. `core/auth/`
* **Tanggung Jawab**: Menangani pintu gerbang otentikasi 3-faktor sebelum aplikasi beralih ke mode rahasia.
* **File Utama**:
  - `usb_dongle.py`: Memindai drive eksternal (*removable drives*), membaca file signature `aerosat.sig`, dan memvalidasi hardware volume serial USB flashdisk.
  - `face_recog.py`: Mengontrol webcam, mendeteksi wajah dengan OpenCV, mengekstrak representasi vektor/embedding wajah, dan membandingkannya dengan template wajah operator yang sah.
  - `hasher.py`: Menghasilkan salt acak kriptografi, melakukan hashing passcode dengan algoritma kuat, dan melakukan validasi *constant-time comparison* untuk mencegah *timing attacks*.

---

### 3. `core/crypto/`
* **Tanggung Jawab**: Menyediakan mesin matematika kriptografi independen tanpa ketergantungan pada UI.
* **File Utama**:
  - `vigenere.py`: Mengimplementasikan Extended Vigenère Cipher dengan dukungan karakter ASCII penuh (0-255 atau Base64) agar teks dengan spasi/simbol tidak korup.
  - `rsa_engine.py`: Mengatur siklus hidup kunci RSA (pembuatan pasangan kunci publik/privat, penyimpanan PEM, enkripsi dan dekripsi menggunakan skema OAEP padding).
  - `super_text_cipher.py`: Menggabungkan Vigenère dan RSA ke dalam satu alur super-enkripsi (Plaintext $\to$ Vigenère $\to$ RSA $\to$ Base64) dan proses dekripsi sebaliknya.
  - `file_aes.py`: Melakukan enkripsi dan dekripsi file berbasis stream blok (chunk 64 KB) menggunakan **AES-256-GCM** yang menjamin kerahasiaan dan integritas file.

---

### 4. `core/stego/`
* **Tanggung Jawab**: Menangani rekayasa steganografi citra.
* **File Utama**:
  - `lsb_engine.py`: Memanipulasi bit terendah (LSB) pada tiap saluran warna (R, G, B) dari citra lossless (PNG/BMP). Menyisipkan header metadata (panjang pesan dan magic signature) serta mengekstrak kembali pesan rahasia secara presisi.

---

### 5. `core/database/`
* **Tanggung Jawab**: Pengelolaan persistensi data relasional dengan proteksi *encryption at rest*.
* **File Utama**:
  - `db_manager.py`: Mengatur koneksi SQLite, eksekusi query, serta pembungkusan enkripsi/dekripsi otomatis pada kolom-kolom teks sensitif.
  - `models.py`: Mendefinisikan struktur skema tabel basis data untuk memo intelijen, arsip berkas, dan log aktivitas.

---

### 6. `core/blockchain/`
* **Tanggung Jawab**: Menyediakan buku besar terdistribusi sederhana (*immutable ledger*) untuk menjamin keaslian aset digital intelijen.
* **File Utama**:
  - `block.py`: Representasi struktur data sebuah blok (index, timestamp, data hash, previous hash, nonce, hash).
  - `chain.py`: Mengelola rantai blok, pembuatan genesis block, kalkulasi konsensus Proof of Work (PoW), dan fungsi verifikasi keutuhan rantai (`is_chain_valid`).
  - `asset_tracker.py`: Menyediakan fungsi tingkat tinggi untuk mendaftarkan hash file intelijen ke dalam blockchain dan memvalidasi apakah file yang ada saat ini masih orisinil atau sudah dimodifikasi.

---

### 7. `gui/`
* **Tanggung Jawab**: Menangani seluruh tampilan visual antarmuka pengguna berbasis **PyQt6** bertema putih/terang.
* **File Utama**:
  - `main_cover_window.py`: Jendela mode publik stasiun satelit yang menampilkan visual peta bumi, koordinat lintang/bujur, dan telemetri cuaca. Dilengkapi pemicu rahasia (*trigger*).
  - `auth_dialog.py`: Jendela popup otorisasi yang menampilkan status koneksi USB, live feed webcam untuk face scan, dan input passcode.
  - `secret_dashboard.py`: Jendela induk mode rahasia yang memuat 5 tab utama (Super Text, File AES, Stego Lab, DB Vault, Blockchain Explorer).
  - `tabs/`: Modul tampilan terpisah untuk masing-masing instrumen kriptografi.
  - `components/`: Komponen UI yang dapat digunakan kembali (*reusable widgets*), seperti penampil kamera, kartu blok, dan peta geospasial.

---

### 8. `tools/`
* **Tanggung Jawab**: Skrip utilitas CLI yang dijalankan di luar siklus utama aplikasi untuk kebutuhan setup administratif.
* **File Utama**:
  - `setup_dongle.py`: Digunakan oleh pemilik sistem untuk memformat dan menyuntikkan token signature ke dalam USB Flashdisk miliknya.
  - `register_face.py`: Digunakan saat pertama kali untuk mengambil sampel wajah operator melalui webcam dan menyimpannya sebagai template biometrik terenkripsi.

---

### 9. `tests/`
* **Tanggung Jawab**: Memastikan setiap modul logika keamanan bekerja 100% akurat sebelum diintegrasikan ke antarmuka grafis.
* Berisi *automated test cases* mandiri untuk autentikasi, super-enkripsi teks, enkripsi file AES, steganografi LSB, basis data, dan integritas blockchain.
