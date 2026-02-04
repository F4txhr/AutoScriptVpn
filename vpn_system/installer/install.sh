#!/bin/bash

# ==================================================
# Project: Vortex-x VPN Platform
# Author: F4txhr
# Description: Professional VPN Installer & Hardening
# ==================================================

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Paths
VORTEX_LIB="/usr/local/lib/vortex-x"
VORTEX_ETC="/usr/local/etc/vortex-x"
VORTEX_BIN="/usr/local/bin/vortex-x"

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[SUCCESS]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# --- Check Environment ---
check_env() {
    log_info "Checking environment..."
    if [ -d "/data/data/com.termux" ] || [ -n "$PROOT_TMPDIR" ]; then
        log_warn "Running in PRoot/Termux environment. Full system hardening and kernel protocols (WG/OVPN) might fail execution."
        IS_PROOT=true
    else
        IS_PROOT=false
        [ "$(id -u)" -ne 0 ] && log_error "This script must be run as root on a real VPS."
    fi
}

# --- Detect OS ---
detect_os() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        OS=$ID
        VER=$VERSION_ID
    else
        log_error "Unsupported OS."
    fi
    log_info "Detected OS: $NAME ($VER)"
}

# --- Install Dependencies ---
install_deps() {
    log_info "Installing dependencies..."
    case "$OS" in
        ubuntu|debian)
            apt-get update -y
            apt-get install -y python3 python3-pip python3-venv python3-psutil \
                nginx certbot curl wget rsync socat cron jq vnstat fail2ban ufw
            ;;
        centos|almalinux|rocky|alinux)
            dnf install -y epel-release
            dnf makecache
            # Try installing core packages. split ufw/firewalld logic
            dnf install -y python3 python3-pip nginx wget rsync socat cronie jq firewalld
            
            # Optional packages (might be missing on some cloud repos)
            dnf install -y vnstat fail2ban || log_warn "Optional tools (vnstat/fail2ban) not found. Skipping."
            
            # Try install certbot, fallback to pip if missing
            if ! dnf install -y certbot; then
                pip3 install certbot
            fi
            ;;
        *)
            log_error "Distribution $OS not supported yet."
            ;;
    esac
}

# --- Deploy Files ---
deploy_files() {
    log_info "Deploying Vortex-x files..."
    mkdir -p "$VORTEX_LIB" "$VORTEX_ETC"
    
    # Sync project files
    cp -r ./vpn_system/* "$VORTEX_LIB/"
    
    # Register CLI
    ln -sf "$VORTEX_LIB/cli/vortex-x" "$VORTEX_BIN"
    chmod +x "$VORTEX_BIN"
    ln -sf "$VORTEX_BIN" "/usr/bin/vortex-x"

    # Deploy Configs (Fail2ban)
    if [ -d "/etc/fail2ban" ]; then
        log_info "Configuring Fail2ban..."
        cp "$VORTEX_LIB/configs/fail2ban/jail.local" "/etc/fail2ban/jail.local"
        cp "$VORTEX_LIB/configs/fail2ban/filter.d/xray.conf" "/etc/fail2ban/filter.d/xray.conf"
        systemctl restart fail2ban || true
    fi

    # Cleanup Default Nginx Configs
    log_info "Cleaning up default Nginx configurations..."
    rm -f /etc/nginx/conf.d/default.conf
    rm -f /etc/nginx/sites-enabled/default
    
    # Ensure a clean, compatible nginx.conf
    if [ -f "/etc/nginx/nginx.conf" ]; then
        cp /etc/nginx/nginx.conf /etc/nginx/nginx.conf.bak
    fi
    
    cat > /etc/nginx/nginx.conf <<EOF
user nginx;
worker_processes auto;
error_log /var/log/nginx/error.log;
pid /run/nginx.pid;
include /usr/share/nginx/modules/*.conf;

events {
    worker_connections 1024;
}

http {
    log_format  main  '\$remote_addr - \$remote_user [\$time_local] "\$request" '
                      '\$status \$body_bytes_sent "\$http_referer" '
                      '"\$http_user_agent" "\$http_x_forwarded_for"';

    access_log  /var/log/nginx/access.log  main;

    sendfile            on;
    tcp_nopush          on;
    tcp_nodelay         on;
    keepalive_timeout   65;
    types_hash_max_size 2048;

    include             /etc/nginx/mime.types;
    default_type        application/octet-stream;

    include /etc/nginx/conf.d/*.conf;
}
EOF
}

# --- Hardening ---
apply_hardening() {
    if [ "$IS_PROOT" = false ]; then
        log_info "Applying system hardening..."
        # Create non-root user for services
        id -u vortex-x &>/dev/null || useradd -r -s /usr/sbin/nologin vortex-x
        
        # Directory permissions
        chown -R vortex-x:vortex-x "$VORTEX_ETC"
        chmod 750 "$VORTEX_ETC"
        if [ -f "$VORTEX_ETC/db.json" ]; then
            chmod 600 "$VORTEX_ETC/db.json"
        fi
        
        # Firewall setup (Detect UFW or Firewalld)
        if command -v ufw &> /dev/null; then
            log_info "Configuring UFW..."
            ufw allow 80/tcp
            ufw allow 443/tcp
            ufw allow ssh
            # ufw --force enable # Optional: auto-enable
        elif command -v firewall-cmd &> /dev/null; then
            log_info "Configuring Firewalld..."
            systemctl start firewalld
            systemctl enable firewalld
            firewall-cmd --permanent --add-service=http
            firewall-cmd --permanent --add-service=https
            firewall-cmd --permanent --add-service=ssh
            # Enable standard VPN ports
            firewall-cmd --permanent --add-port=51820/udp
            firewall-cmd --permanent --add-port=1194/udp
            firewall-cmd --permanent --add-port=1194/tcp
            # Enable Masquerade for VPN Tunneling
            firewall-cmd --permanent --add-masquerade
            firewall-cmd --reload
        else
            log_warn "No supported firewall manager found (ufw/firewalld). Ports might be closed."
        fi
        
        # Run Service Hardening
        python3 "$VORTEX_LIB/scripts/harden_services.py"

        # Repair Xray config to ensure deprecated transports are removed
        python3 "$VORTEX_LIB/scripts/repair_xray_config.py"
        systemctl restart xray || true
        
        # SELinux Context for Nginx Proxy (Critical for RHEL/Alinux)
        if command -v getsebool &> /dev/null; then
            log_info "Configuring SELinux for Nginx Proxy..."
            setsebool -P httpd_can_network_connect 1 || true
        fi

        log_success "Hardening applied."
    fi
}

# --- Setup Cron ---
setup_cron() {
    log_info "Setting up Cron Jobs for Monitoring..."
    CRON_FILE="/etc/cron.d/vortex-x"
    cat > "$CRON_FILE" <<EOF
* * * * * root python3 $VORTEX_LIB/monitoring/traffic_monitor.py
* * * * * root python3 $VORTEX_LIB/user_management/ip_limiter.py
0 * * * * root python3 $VORTEX_LIB/user_management/expiry_manager.py
0 0 * * * root python3 $VORTEX_LIB/scripts/ssl_manager.py renew
EOF
    chmod 644 "$CRON_FILE"
    
    # Try restarting cron services quietly
    if systemctl restart crond &>/dev/null; then
        log_success "Cron service (crond) restarted."
    elif systemctl restart cron &>/dev/null; then
        log_success "Cron service (cron) restarted."
    elif systemctl restart cronie &>/dev/null; then
         log_success "Cron service (cronie) restarted."
    else
        log_warn "Could not restart cron service automatically. Please check 'crond' status."
    fi
}

main() {
    check_env
    detect_os
    
    if [ "$IS_PROOT" = false ]; then
        install_deps
        deploy_files
        apply_hardening
        setup_cron
        log_success "Vortex-x installed successfully!"
        log_info "Type 'vortex-x' to start."
    else
        log_warn "Installer skipped system execution due to PRoot environment."
        log_info "Source files are ready in ./vpn_system"
    fi
}

main "$@"
