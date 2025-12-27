# 🗺️ Vortex-x Development Roadmap (v1.0 - Production Ready)

Platform VPN profesional berbasis VPS dengan dukungan multi-protokol, keamanan tingkat tinggi, dan monitoring lengkap.

---

## 🏗️ FASE 1: Fondasi & Infrastruktur Inti (Minggu 1)
*Fokus: Struktur sistem, installer, dan basis data.*
- [x] **Project Structure**: Setup direktori kerja modular.
- [x] **Core Models**: Implementasi database JSON dan class UserAccount.
- [x] **Smart Installer**: Deteksi OS otomatis, validasi sistem, dan instalasi base dependencies.
- [x] **Vortex-x CLI Core**: Membangun entry point `/usr/bin/vortex-x`.
- [x] **Directory Hardening**: Pengaturan izin akses (ACL) ketat di `/usr/local/etc/vortex-x`.

## 🔐 FASE 2: Protocol Engine & Proxy (Minggu 1-2)
*Fokus: Implementasi VPN core dan integrasi Nginx.*
- [x] **Xray Core Integration**: Konfigurasi otomatis VLESS, VMess, Trojan, dan Shadowsocks.
- [x] **Nginx Reverse Proxy**: Setup port 80/443 dengan dukungan WebSocket & gRPC.
- [x] **Advanced Transport**: Implementasi TLS 1.3, XTLS Vision, dan HTTP/2 (gRPC).
- [x] **Legacy VPN**: Setup WireGuard (Kernel mode) dan OpenVPN (TCP/UDP).

## 🛡️ FASE 3: Security Hardening (Minggu 2)
*Fokus: Keamanan tingkat kernel dan systemd.*
- [x] **Systemd Isolation**: Menjalankan semua VPN engine sebagai user `nobody` atau `vortex-x` (non-root).
- [x] **Network Security**: Setup UFW/Iptables dengan aturan anti brute-force (via Audit & Installer).
- [x] **Fail2ban**: Proteksi akses SSH dan probing ilegal pada port VPN (Config deployed).
- [x] **SSL Automation**: Integrasi Certbot dengan auto-renew dan permission fix.

## 📊 FASE 4: Dashboard CLI Vortex-x (Minggu 3)
*Fokus: UI/UX Management Interface.*
- [x] **Header Real-time**: Banner ASCII, info resource (CPU/RAM/Disk), dan traffic RX/TX.
- [x] **Interactive Root Menu**: Navigasi menu dinamis (Warna ANSI).
- [x] **SSL Tracker**: Menampilkan sisa hari aktif sertifikat langsung di header.
- [x] **Service Watchdog**: Monitoring status service (Running/Failed) secara visual.

## 🧑‍💻 FASE 5: User & Bandwidth Management (Minggu 3-4)
*Fokus: Logika akun dan pembatasan.*
- [x] **Auth Generator**: Pembuatan UUID dan password otomatis.
- [x] **IP Limiter**: Skrip pemutus koneksi jika user melebihi limit device.
- [x] **Expiry System**: Otomasi penghapusan akun expired via Cron.
- [x] **Traffic Logger**: Pencatatan penggunaan kuota bandwidth per user.

## 📦 FASE 6: Automation & Recovery (Minggu 4)
*Fokus: Maintenance dan keandalan.*
- [x] **Backup/Restore**: Sistem cadangan data user dan config ke cloud/local (Retention policy added).
- [ ] **System Update**: Fitur update core Vortex-x tanpa merusak konfigurasi.
- [x] **Logs & Debug**: Centralized logging untuk mempermudah troubleshooting (via Audit).

## 🌐 FASE 7: Advanced Features (Optional/SaaS Ready)
*Fokus: Ekspansi fitur.*
- [x] **Clash/Meta Config**: Auto-generate config untuk client premium.
- [x] **System Audit**: Final security and service audit logic (Implemented).
- [ ] **Web Panel API**: Backend untuk integrasi dengan aplikasi mobile/web.
- [ ] **Telegram Bot**: Bot manajemen akun via Telegram.

---
**Author:** F4txhr
**Project:** Vortex-x VPN Platform
**Status:** Production Release Candidate
