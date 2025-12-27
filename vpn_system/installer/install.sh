#!/bin/bash

# Exit immediately if a command exits with a non-zero status.
set -e

# --- Logging functions ---
log_info() {
    echo "[INFO] $1"
}

log_warn() {
    echo "[WARN] $1"
}

log_error() {
    echo "[ERROR] $1" >&2
    exit 1
}

# --- OS Detection ---
detect_os() {
    if [ -f /etc/os-release ]; then
        # freedesktop.org and systemd
        . /etc/os-release
        OS=$NAME
        VER=$VERSION_ID
        ID_LIKE=${ID_LIKE:-$ID} # Set ID_LIKE to ID if it's not set
    else
        log_error "Cannot detect operating system."
    fi

    log_info "Detected OS: $OS $VER"
}

# --- Dependency Installation ---
install_dependencies() {
    log_info "Installing base dependencies..."
    case "$ID_LIKE" in
        *debian*|*ubuntu*)
            log_info "Using apt-get for Debian/Ubuntu-based system."
            export DEBIAN_FRONTEND=noninteractive
            apt-get update -y
            apt-get install -y python3 python3-pip python3-venv coreutils curl wget socat iptables-persistent net-tools
            ;;
        *rhel*|*centos*|*fedora*|*almalinux*|*rocky*|*alinux*)
            log_info "Using dnf/yum for RHEL/CentOS/Alibaba-based system."
            # Use dnf if available, otherwise fall back to yum
            if command -v dnf &> /dev/null; then
                PKG_MANAGER="dnf"
            else
                PKG_MANAGER="yum"
            fi
            $PKG_MANAGER install -y epel-release || log_warn "Could not install EPEL release. Some packages may be unavailable."
            $PKG_MANAGER install -y python3 python3-pip python3-devel coreutils curl wget socat iptables-services net-tools
            ;;
        *)
            log_error "Unsupported operating system: $OS. This script supports Debian, Ubuntu, CentOS, RHEL, Rocky, AlmaLinux, and Alibaba Cloud Linux."
            ;;
    esac

    log_info "Installing Python dependencies..."
    # Use apt to install psutil on Debian-based systems to comply with PEP 668
    case "$ID_LIKE" in
        *debian*|*ubuntu*)
            apt-get install -y python3-psutil
            ;;
        *rhel*|*centos*|*fedora*|*almalinux*|*rocky*|*alinux*)
            # For RHEL-based systems, pip is generally fine, or use dnf/yum if available
            pip3 install psutil
            ;;
    esac

    log_info "Base dependencies installed successfully."
}

# --- Install Certbot (SSL) ---
install_certbot() {
    log_info "Installing Certbot..."
    case "$ID_LIKE" in
        *debian*|*ubuntu*)
            apt-get install -y certbot
            ;;
        *rhel*|*centos*|*fedora*|*almalinux*|*rocky*|*alinux*)
            $PKG_MANAGER install -y certbot
            ;;
    esac
}

# --- Network & Firewall Setup ---
setup_network_firewall() {
    log_info "Configuring Network and Firewall..."

    # 1. Enable IP Forwarding
    echo "net.ipv4.ip_forward = 1" > /etc/sysctl.d/99-vpn.conf
    sysctl --system
    log_info "IP Forwarding enabled."

    # 2. Configure Firewall (Try UFW, then Firewalld, then IPTables)
    if command -v ufw &> /dev/null; then
        log_info "Configuring UFW..."
        ufw allow 80/tcp
        ufw allow 443/tcp
        ufw allow 51820/udp
        ufw allow ssh
        # ufw enable # CAUTION: Don't auto-enable to avoid locking out, just allow ports.
    elif command -v firewall-cmd &> /dev/null; then
        log_info "Configuring Firewalld..."
        if systemctl is-active --quiet firewalld; then
            firewall-cmd --permanent --add-service=http
            firewall-cmd --permanent --add-service=https
            firewall-cmd --permanent --add-port=51820/udp
            firewall-cmd --permanent --add-masquerade
            firewall-cmd --reload
        else
            log_warn "Firewalld is installed but not active. Skipping configuration."
        fi
    else
        log_info "Configuring raw IPTables..."
        iptables -I INPUT -p tcp --dport 80 -j ACCEPT
        iptables -I INPUT -p tcp --dport 443 -j ACCEPT
        iptables -I INPUT -p udp --dport 51820 -j ACCEPT
        netfilter-persistent save || service iptables save || true
    fi
}

# --- Cron Job for Monitoring & Backup ---
setup_cron() {
    log_info "Setting up Cron Jobs..."
    
    # 1. Expiry Monitor (Daily)
    CRON_EXPIRY="0 0 * * * /usr/bin/python3 /usr/local/lib/vpn_system/user_management/expiry_monitor.py >> /var/log/vpn_expiry.log 2>&1"
    
    # 2. Traffic Monitor (Every 5 Minutes)
    CRON_TRAFFIC="*/5 * * * * /usr/bin/python3 /usr/local/lib/vpn_system/user_management/traffic_monitor.py >> /var/log/vpn_traffic.log 2>&1"
    
    # 3. Backup Telegram (Daily)
    CRON_BACKUP="0 1 * * * /usr/bin/python3 /usr/local/lib/vpn_system/user_management/backup_telegram.py >> /var/log/vpn_backup.log 2>&1"

    (crontab -l 2>/dev/null | grep -v "user_management" ; echo "$CRON_EXPIRY" ; echo "$CRON_TRAFFIC" ; echo "$CRON_BACKUP") | crontab -
}

# --- System Optimization (BBR, Time, Swap, Limits) ---
optimize_system() {
    log_info "Applying System Optimizations (BBR, Swap, Time Sync, Limits)..."

    # 1. Time Synchronization (Critical for VLESS/VMess)
    log_info "Configuring Time Synchronization..."
    case "$ID_LIKE" in
        *debian*|*ubuntu*)
            apt-get install -y chrony
            ;;
        *rhel*|*centos*|*fedora*|*almalinux*|*rocky*|*alinux*)
            $PKG_MANAGER install -y chrony
            ;;
    esac
    systemctl enable --now chronyd
    timedatectl set-ntp true

    # 2. Enable TCP BBR (Speed Boost)
    log_info "Enabling TCP BBR..."
    if ! grep -q "net.ipv4.tcp_congestion_control=bbr" /etc/sysctl.conf; then
        echo "net.core.default_qdisc=fq" >> /etc/sysctl.conf
        echo "net.ipv4.tcp_congestion_control=bbr" >> /etc/sysctl.conf
    fi

    # 3. Tuning System Limits (High Concurrency)
    log_info "Tuning System Limits..."
    if ! grep -q "fs.file-max" /etc/sysctl.conf; then
        echo "fs.file-max = 1000000" >> /etc/sysctl.conf
        echo "net.ipv4.ip_local_port_range = 1024 65535" >> /etc/sysctl.conf
        echo "net.ipv4.tcp_window_scaling = 1" >> /etc/sysctl.conf
        echo "net.ipv4.tcp_keepalive_time = 600" >> /etc/sysctl.conf
        echo "net.ipv4.tcp_keepalive_intvl = 10" >> /etc/sysctl.conf
        echo "net.ipv4.tcp_keepalive_probes = 6" >> /etc/sysctl.conf
    fi
    
    # Apply sysctl changes
    sysctl -p

    # Update limits.conf for max open files
    mkdir -p /etc/security/limits.d
    echo "* soft nofile 65535" > /etc/security/limits.d/20-vpn.conf
    echo "* hard nofile 65535" >> /etc/security/limits.d/20-vpn.conf
    echo "root soft nofile 65535" >> /etc/security/limits.d/20-vpn.conf
    echo "root hard nofile 65535" >> /etc/security/limits.d/20-vpn.conf

    # 4. Auto Swap (2GB) - Prevent OOM Kills
    log_info "Checking Swap Memory..."
    if [ $(free -m | awk '/^Swap:/{print $2}') -eq 0 ]; then
        log_info "No Swap detected. Creating 2GB Swap file..."
        # Try fallocate first, fallback to dd
        fallocate -l 2G /swapfile 2>/dev/null || dd if=/dev/zero of=/swapfile bs=1M count=2048
        chmod 600 /swapfile
        mkswap /swapfile
        swapon /swapfile
        echo '/swapfile none swap sw 0 0' >> /etc/fstab
        log_info "Swap created successfully."
    else
        log_info "Swap already exists."
    fi

    # 5. Log Rotation for Xray
    log_info "Configuring Log Rotation..."
    mkdir -p /etc/logrotate.d
    cat > /etc/logrotate.d/xray <<EOF
/var/log/xray/*.log {
    daily
    rotate 3
    missingok
    compress
    notifempty
    create 640 nobody nobody
    postrotate
        systemctl reload xray > /dev/null 2>/dev/null || true
    endscript
}
EOF
}

# --- Install Menu ---
install_menu() {
    log_info "Installing Interactive Menu..."
    mkdir -p /usr/local/lib/vpn_system/menu
    cp ./vpn_system/menu/menu.sh /usr/local/lib/vpn_system/menu/menu.sh
    chmod +x /usr/local/lib/vpn_system/menu/menu.sh
    ln -sf /usr/local/lib/vpn_system/menu/menu.sh /usr/local/bin/menu
    log_info "Menu installed. Type 'menu' to access."
}

# --- Install Xray Core ---
install_xray_core() {
    if command -v xray &> /dev/null; then
        log_info "Xray Core is already installed."
    else
        log_info "Installing Xray Core..."
        # Official Xray installation script
        bash -c "$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)" @ install
        if [ $? -eq 0 ]; then
            log_info "Xray Core installed successfully."
        else
            log_error "Failed to install Xray Core."
        fi
    fi
}

# --- Install WireGuard ---
install_wireguard() {
    if command -v wg &> /dev/null; then
        log_info "WireGuard Tools are already installed."
    else
        log_info "Installing WireGuard Tools..."
        case "$ID_LIKE" in
            *debian*|*ubuntu*)
                apt-get install -y wireguard
                ;;
            *rhel*|*centos*|*fedora*|*almalinux*|*rocky*|*alinux*)
                $PKG_MANAGER install -y wireguard-tools
                # On CentOS 7/8, elrepo might be needed for kmod-wireguard if kernel is old,
                # but modern kernels have it built-in. We assume a relatively modern kernel or user handles repo.
                ;;
        esac
        
        if command -v wg &> /dev/null; then
             log_info "WireGuard Tools installed successfully."
        else
             log_error "Failed to install WireGuard Tools."
        fi
    fi
}


# --- Install OpenVPN ---
install_openvpn() {
    if command -v openvpn &> /dev/null; then
        log_info "OpenVPN is already installed."
    else
        log_info "Installing OpenVPN & EasyRSA..."
        case "$ID_LIKE" in
            *debian*|*ubuntu*)
                apt-get install -y openvpn easy-rsa
                ;;
            *rhel*|*centos*|*fedora*|*almalinux*|*rocky*|*alinux*)
                $PKG_MANAGER install -y openvpn easy-rsa
                ;;
        esac
    fi
}

# --- Install Nginx ---
install_nginx() {
    if command -v nginx &> /dev/null; then
        log_info "Nginx is already installed."
    else
        log_info "Installing Nginx..."
        case "$ID_LIKE" in
            *debian*|*ubuntu*)
                apt-get install -y nginx
                ;;
            *rhel*|*centos*|*fedora*|*almalinux*|*rocky*|*alinux*)
                $PKG_MANAGER install -y nginx
                # Enable on boot for RHEL based
                systemctl enable nginx
                ;;
        esac
    fi
}

# --- Install VPN System ---
install_vpn_system() {
    log_info "Installing VPN system files..."

    # Define paths
    SRC_DIR="./vpn_system"
    LIB_INSTALL_DIR="/usr/local/lib/vpn_system"
    BIN_INSTALL_PATH="/usr/local/bin/vpn-ctl"
    CLI_SRC_PATH="$SRC_DIR/cli/vpn-ctl"

    if [ ! -d "$SRC_DIR" ]; then
        log_error "Source directory '$SRC_DIR' not found. Please run the installer from the repository root."
    fi

    # Create library directory and copy all system files
    rm -rf "$LIB_INSTALL_DIR" # Clean previous installation
    mkdir -p "$LIB_INSTALL_DIR"
    # Copy everything except the installer itself
    rsync -av --exclude 'installer/' "$SRC_DIR/" "$LIB_INSTALL_DIR/"
    if [ $? -ne 0 ]; then
        log_error "Failed to copy system files to $LIB_INSTALL_DIR."
    fi

    # Install the CLI script to the bin path
    cp "$CLI_SRC_PATH" "$BIN_INSTALL_PATH"
    if [ $? -ne 0 ]; then
        log_error "Failed to copy vpn-ctl to $BIN_INSTALL_PATH."
    fi

    # Make the CLI script executable
    chmod +x "$BIN_INSTALL_PATH"
    if [ $? -ne 0 ]; then
        log_error "Failed to make vpn-ctl executable."
    fi

    log_info "VPN system installed successfully."
    log_info "CLI tool is available at: $BIN_INSTALL_PATH"
}


# --- Main execution ---
main() {
    if [ "$(id -u)" -ne 0 ]; then
        log_error "This script must be run as root. Please use sudo."
    fi

    detect_os
    install_dependencies
    install_certbot
    setup_network_firewall
    install_nginx
    install_xray_core
    install_wireguard
    install_openvpn
    optimize_system
    install_vpn_system
    install_menu
    setup_cron

    log_info "VPN system installation completed successfully."
    
    # --- Auto Initialization ---
    echo ""
    echo "--------------------------------------------------------"
    echo "  SYSTEM INITIALIZATION & DOMAIN SETUP"
    echo "--------------------------------------------------------"
    read -p "Do you want to configure the domain and SSL now? [y/n]: " DO_INIT
    
    if [[ "$DO_INIT" =~ ^[Yy]$ ]]; then
        read -p "Enter your Domain/Host (e.g., vpn.example.com): " DOMAIN_NAME
        
        if [ -n "$DOMAIN_NAME" ]; then
            log_info "Verifying DNS for $DOMAIN_NAME..."
            
            # Get Public IP
            PUBLIC_IP=$(curl -s --max-time 5 https://api.ipify.org)
            # Get Domain IP
            DOMAIN_IP=$(getent hosts "$DOMAIN_NAME" | awk '{ print $1 }' | head -n 1)
            
            echo "  > Server Public IP : $PUBLIC_IP"
            echo "  > Domain Resolve IP: ${DOMAIN_IP:-"Not Resolved"}"
            
            PROCEED_SSL=false
            
            if [ "$PUBLIC_IP" == "$DOMAIN_IP" ]; then
                log_info "DNS Verified! Domain points to this server."
                PROCEED_SSL=true
            elif [ -z "$DOMAIN_IP" ]; then
                log_warn "Domain could not be resolved. Please check your DNS settings."
                read -p "Force proceed anyway? (SSL setup may fail) [y/n]: " FORCE
                [[ "$FORCE" =~ ^[Yy]$ ]] && PROCEED_SSL=true
            else
                log_warn "IP Mismatch! Domain does not point to this server IP."
                echo "    This is normal if you are using Cloudflare Proxy (Orange Cloud)."
                echo "    Ensure your Cloudflare SSL/TLS setting is set to 'Full' or 'Strict'."
                read -p "Proceed with SSL setup (Certbot)? [y/n]: " FORCE
                [[ "$FORCE" =~ ^[Yy]$ ]] && PROCEED_SSL=true
            fi
            
            if [ "$PROCEED_SSL" = true ]; then
                log_info "Requesting SSL Certificate via Certbot..."
                # Stop Nginx/Xray temporarily to free port 80 if needed, though --nginx plugin or --standalone is used
                # We use --standalone to be safe and independent of nginx config state
                systemctl stop nginx || true
                
                certbot certonly --standalone --preferred-challenges http --agree-tos --email admin@"$DOMAIN_NAME" -d "$DOMAIN_NAME" --non-interactive
                
                if [ $? -eq 0 ]; then
                    log_info "SSL Certificate obtained successfully!"
                    
                    # Link certs to where Xray adapters expect them
                    # Adapters expect: /etc/ssl/certs/{domain}/fullchain.pem
                    mkdir -p "/etc/ssl/certs/$DOMAIN_NAME"
                    
                    # Certbot stores in /etc/letsencrypt/live/$DOMAIN_NAME/
                    ln -sf "/etc/letsencrypt/live/$DOMAIN_NAME/fullchain.pem" "/etc/ssl/certs/$DOMAIN_NAME/fullchain.pem"
                    ln -sf "/etc/letsencrypt/live/$DOMAIN_NAME/privkey.pem" "/etc/ssl/certs/$DOMAIN_NAME/privkey.pem"
                    
                    log_info "Certificates linked to system paths."
                    
                    # Restart Nginx
                    systemctl start nginx || true
                    
                    # Run Init
                    log_info "Initializing system configuration..."
                    /usr/local/bin/vpn-ctl init -d "$DOMAIN_NAME"
                    
                    if [ $? -eq 0 ]; then
                        log_info "System Initialized Successfully!"
                    else
                        log_error "Initialization failed."
                    fi
                else
                    log_error "Certbot failed to obtain SSL certificate. Check firewall (Port 80) and DNS."
                    systemctl start nginx || true
                fi
            else
                log_info "Skipping SSL and Initialization. You must fix DNS and run 'vpn-ctl init' later."
            fi
        else
            log_warn "Domain cannot be empty."
        fi
    else
        log_info "Skipping initialization."
        log_info "You MUST run 'vpn-ctl init -d yourdomain.com' manually before adding users."
    fi

    echo ""
    log_info "Type 'menu' to start the management interface."
}

# Run the main function
main
