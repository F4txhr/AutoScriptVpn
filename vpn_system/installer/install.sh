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
        *rhel*|*centos*|*fedora*|*almalinux*|*rocky*)
            log_info "Using dnf/yum for RHEL/CentOS-based system."
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
            log_error "Unsupported operating system: $OS. This script supports Debian, Ubuntu, CentOS, RHEL, Rocky, and AlmaLinux."
            ;;
    esac

    log_info "Installing Python dependencies..."
    # Use apt to install psutil on Debian-based systems to comply with PEP 668
    case "$ID_LIKE" in
        *debian*|*ubuntu*)
            apt-get install -y python3-psutil
            ;;
        *rhel*|*centos*|*fedora*|*almalinux*|*rocky*)
            # For RHEL-based systems, pip is generally fine, or use dnf/yum if available
            pip3 install psutil
            ;;
    esac

    log_info "Base dependencies installed successfully."
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
    install_vpn_system

    log_info "VPN system installation completed successfully."
}

# Run the main function
main
