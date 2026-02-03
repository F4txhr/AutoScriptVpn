# 🗺️ Vortex-x Development Roadmap (v1.0 - Production Ready)

Platform VPN profesional berbasis VPS dengan dukungan multi-protokol, keamanan tingkat tinggi, dan monitoring lengkap.

---

## 🏗️ FASE 1: Fondasi & Infrastruktur Inti
- [x] **Project Structure**: Setup direktori kerja modular.
- [x] **Core Models**: Implementasi database JSON dan class UserAccount.
- [x] **Smart Installer**: Deteksi OS otomatis (Ubuntu/Alibaba Cloud/CentOS).
- [x] **Vortex-x CLI Core**: Entry point `/usr/bin/vortex-x` aktif.
- [x] **Directory Hardening**: ACL ketat di folder config.

## 🔐 FASE 2: Protocol Engine & Proxy
- [x] **Xray Core Integration**: VLESS, VMess, Trojan, Shadowsocks.
- [x] **Nginx Reverse Proxy**: WebSocket & gRPC (HTTP/2) support.
- [x] **Advanced Transport**: gRPC Stealth mode aktif.
- [x] **Legacy VPN**: WireGuard & OpenVPN support.

## 🛡️ FASE 3: Security Hardening
- [x] **Systemd Isolation**: Service berjalan sebagai user `vortex-x`.
- [x] **Network Security**: Firewalld/UFW + Masquerading.
- [x] **Fail2ban**: Proteksi brute-force.
- [x] **SSL Automation**: Let's Encrypt auto-issue & renew.

## 📊 FASE 4: Dashboard CLI Vortex-x
- [x] **Header Real-time**: System resource & traffic monitoring.
- [x] **Interactive Root Menu**: Navigasi warna ANSI.
- [x] **SSL Tracker**: Notifikasi sisa hari sertifikat.
- [x] **Service Watchdog**: Visual status check.

## 🧑‍💻 FASE 5: User & Bandwidth Management
- [x] **Auth Generator**: UUID/Password otomatis.
- [x] **IP Limiter**: Monitoring multi-login IP via log.
- [x] **Expiry System**: Otomasi penghapusan akun expired.
- [x] **Traffic Logger**: Pencatatan penggunaan kuota bandwidth.

## 📦 FASE 6: Automation & Recovery
- [x] **Backup/Restore**: Sistem cadangan data user dan config.
- [ ] **System Update**: Fitur update core (Future update).
- [x] **Logs & Debug**: Centralized logging via System Audit.

## 🌐 FASE 7: Advanced Features
- [x] **Clash/Meta Config**: Auto-generate config client.
- [x] **System Audit**: Tool diagnostik "System Doctor".

## 🧭 FASE 8: Centralized Web Panel (Terpisah)
- [ ] **Central Panel (Master)**: Dashboard web terpisah untuk memonitor multi-VPS.
- [ ] **Node Agent**: Agen ringan di setiap VPS untuk kirim metrics dan terima perintah.
- [ ] **API Contract**: Endpoint dan payload JSON standar Panel ↔ Agent.
- [ ] **Security Layer**: API token/mTLS + rate limiting.
- [ ] **MVP UI**: Login admin, daftar node, status, dan create user.

---
**Author:** F4txhr
**Project:** Vortex-x VPN Platform
**Status:** ✅ v1.0 Production Ready
---
