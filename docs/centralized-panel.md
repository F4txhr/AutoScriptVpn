# Centralized Web Panel (Terpisah)

Dokumen ini mendefinisikan arsitektur panel terpisah (centralized control plane)
untuk mengelola banyak VPS Vortex-x dari satu dashboard.

---

## 1) Arsitektur Tingkat Tinggi

**Komponen utama:**
1. **Central Panel (Master)**  
   - Menyimpan data admin, node, users, traffic, logs.  
   - UI dashboard untuk monitoring & manajemen.  

2. **Node Agent (di setiap VPS)**  
   - Service ringan yang berkomunikasi dengan Panel.  
   - Mengirim telemetry (metrics & status).  
   - Menerima perintah (create user, revoke, restart).  

3. **Secure Channel**  
   - HTTPS + API token atau mTLS.  
   - Rate limit + audit logs.  

---

## 2) Alur Data (Ringkas)

**Panel → Agent**
- Create/Update/Delete user
- Restart service (xray, wg, ovpn, nginx)
- Sync config
- Rotate cert/renew SSL

**Agent → Panel**
- System metrics (CPU, RAM, Disk, RX/TX)
- Active users (per protocol)
- Traffic per user
- Status service + uptime
- SSL expiry countdown

---

## 3) API Contract (MVP)

### Auth
- Header: `Authorization: Bearer <token>`
- Rotasi token minimal setiap 30–90 hari

### Endpoint (Agent)
- `POST /v1/agent/heartbeat`
  - Payload: `node_id`, `metrics`, `services`, `ssl_days_left`, `users_active`
- `POST /v1/agent/traffic`
  - Payload: `node_id`, `user_id`, `protocol`, `rx`, `tx`, `timestamp`
- `POST /v1/agent/logs`
  - Payload: `node_id`, `level`, `message`, `timestamp`

### Endpoint (Panel)
- `POST /v1/panel/users`
  - Payload: `node_id`, `protocol`, `username`, `expiry`, `limit_ip`
- `DELETE /v1/panel/users/:id`
- `POST /v1/panel/services/restart`
  - Payload: `node_id`, `service`

---

## 4) Skema Database (Draft)

**nodes**
- id, name, host, status, last_seen, token_hash

**users**
- id, username, protocol, expiry, node_id, quota, status

**traffic**
- id, user_id, node_id, protocol, rx, tx, timestamp

**services**
- id, node_id, name, status, last_checked

**audit_logs**
- id, actor, action, node_id, timestamp, detail

---

## 5) MVP Dashboard (Scope Minimum)

- Login admin
- Daftar VPS (online/offline)
- Detail satu VPS (CPU, RAM, Disk, traffic, service status)
- Create/Delete user (pilih node + protocol)

---

## 6) Rekomendasi Implementasi

- Agent berbasis Python/Go (single binary) + systemd.
- Payload JSON standar agar bisa diintegrasikan ke Grafana/Prometheus.
- Rate limit + backoff untuk node yang tidak stabil.
