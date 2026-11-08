# Konteks & Deskripsi Aplikasi: AeroSat GroundStation (Sadap Crypto)

---

## 1. Ringkasan Eksekutif

**AeroSat GroundStation** adalah aplikasi desktop berbasis Python dan PyQt6 yang dirancang dengan konsep **_Plausible Deniability_** (Aplikasi Berkamuflase / *Chameleon Application*). Aplikasi ini memiliki identitas ganda (*Dual-Mode Architecture*):

1. **Mode Publik (The Cover Story)**: Berfungsi sebagai *Ground Station Console* stasiun penerima citra satelit dan analisis geospasial observasi bumi bertema putih/terang minimalis. Mode ini dapat dibuka dan digunakan oleh siapa saja untuk melihat peta bumi, citra satelit permukaan, dan data telemetri cuaca tanpa menimbulkan kecurigaan.
2. **Mode Intelijen / Rahasia (The Covert Crypto Vault)**: Hanya dapat diakses oleh operator terverifikasi melalui mekanisme **Zero-Trust 3-Factor Authentication** (Hardware USB Dongle + Face Recognition + Master Passcode Hash). Mode ini membuka instrumen kriptografi militer tingkat tinggi untuk transmisi pesan ter-super-enkripsi, proteksi file rahasia, steganografi citra satelit, brankas basis data terenkripsi, serta pencatatan integritas aset menggunakan teknologi *Simple Blockchain*.

---

## 2. Latar Belakang & Filosofi Desain

Dalam dunia spionase digital dan keamanan informasi tingkat tinggi, menyembunyikan isi pesan (*kriptografi*) terkadang tidak cukup jika keberadaan aplikasi itu sendiri sudah mencurigakan. Jika penyerang melihat aplikasi bernama *"Secret Encryptor"* di laptop target, mereka akan langsung menginterogasi atau memaksa pemilik untuk membukanya.

**AeroSat GroundStation** memecahkan masalah ini dengan filosofi:
> *"Keamanan terbaik adalah ketika musuh bahkan tidak menyadari bahwa ada sesuatu yang sedang disembunyikan."*

Aplikasi ini menyamarkan instrumen spionase modern ke dalam perangkat lunak analisis satelit ilmiah bereputasi tinggi. Alasan penggunaan proteksi biometrik dan USB dongle menjadi sangat masuk akal di mata publik, karena stasiun pengendali satelit nyata memang membutuhkan otorisasi fisik untuk mencegah pembajakan transmisi orbit.

---

## 3. Fitur Utama & Peleburan Kriptografi

### A. Gatekeeper Otorisasi (3-Factor Zero-Trust)
Untuk beralih dari stasiun satelit biasa ke mode intelijen, sistem mewajibkan pemenuhan tiga faktor otentikasi:
* **Faktor 1 (What You Have - Hardware USB Token)**: Dongle USB fisik yang memiliki file *cryptographic signature key* dan volume serial hardware yang terdaftar. Tanpa USB ini, pintu rahasia tidak akan pernah muncul.
* **Faktor 2 (Who You Are - Biometric Face Recognition)**: Pemindaian wajah operator secara langsung melalui webcam. Menggunakan deteksi landmark wajah dan pencocokan embedding wajah untuk memastikan keaslian fisik operator.
* **Faktor 3 (What You Know - Cryptographic Hash)**: Verifikasi *Passcode Master* menggunakan algoritma hash modern ber-salt (Argon2id / PBKDF2-HMAC-SHA256) untuk mencegah serangan kamus dan *rainbow table*.

---

### B. Super-Enkripsi Pesan Teks (Vigenère + RSA-OAEP)
Pesan intelijen (*Ground-to-Orbit Directive*) dilindungi dengan enkripsi ganda menggabungkan kriptografi klasik dan modern:
1. **Lapisan Klasik (Extended Vigenère Cipher)**: Mengacak karakter teks asli (*plaintext*) menggunakan kunci simetris dinamis dengan dukungan seluruh tabel karakter ASCII/Base64.
2. **Lapisan Modern (RSA-OAEP 2048/4096-bit)**: Teks hasil Vigenère kemudian dienkripsi kembali menggunakan kunci publik asimetris RSA dengan skema *Optimal Asymmetric Encryption Padding* (OAEP).
* **Hasil**: Pesan tidak dapat dipecahkan meskipun kunci Vigenère diketahui (karena masih terkunci oleh RSA) atau sebaliknya.

---

### C. Enkripsi File Sensitif (AES-256-GCM)
Pengamanan dokumen rahasia, peta taktis, dan arsip data intelijen:
* Menggunakan algoritma simetris modern **AES-256 dalam mode GCM (Galois/Counter Mode)**.
* Memberikan jaminan *Confidentiality* (kerahasiaan) dan *Integrity / Authenticity* (keutuhan file via *authentication tag*).
* File diproses secara *streaming chunk* sehingga aman dan ringan untuk file berukuran besar (ratusan megabyte).

---

### D. Steganografi Citra Satelit (LSB - Least Significant Bit)
Menyembunyikan pesan rahasia di dalam citra satelit resolusi tinggi:
* Menggunakan teknik substitusi LSB pada kanal RGB piksel citra lossless (PNG/BMP).
* Dilengkapi *metadata header* (panjang payload + magic byte verifikasi).
* Secara kasat mata, citra satelit terlihat normal dan tidak menunjukkan distorsi visual (*imperceptible*), namun membawa muatan pesan rahasia di dalamnya.

---

### E. Basis Data Terenkripsi Lokal (Encrypted Database at Rest)
Penyimpanan riwayat komunikasi dan log operasi:
* Menggunakan basis data relasional SQLite.
* Seluruh kolom sensitif (isi pesan, metadata transmisi, log agen) dienkripsi menggunakan AES-256 sebelum disimpan ke dalam disk (*field-level encryption*).
* Kunci enkripsi basis data dibuat secara dinamis di memori RAM dan dibersihkan seketika saat aplikasi ditutup.

---

### F. Simple Blockchain Ledger (Integritas Aset & Audit Trail)
Menjaga rekam jejak aset intelijen agar tidak dapat dimanipulasi:
* Mengimplementasikan rantai blok desentralisasi sederhana dengan hashing SHA-256.
* Menggunakan konsensus *Proof of Work (PoW)* sederhana untuk mencetak blok baru.
* Mencatat hash unik file rahasia, sertifikat kepemilikan aset intelijen, dan log transmisi.
* Memiliki fungsi verifikasi keabsahan rantai (`is_chain_valid()`) untuk mendeteksi upaya pemalsuan data masa lalu secara instan.

---

## 4. Sasaran Pengguna & Nilai Proyek

* **Nilai Akademik & Portofolio**: Membuktikan pemahaman mendalam tentang siklus hidup kriptografi lengkap—mulai dari kriptografi klasik (Vigenère), modern (RSA, AES, Hash), steganografi citra, hingga struktur data modern (*blockchain* dan *biometric AI*).
* **Nilai Terap & Keamanan**: Memberikan solusi praktis penyimpanan dan transmisi rahasia dengan perlindungan berlapis dan *deniability* yang sangat realistis.
