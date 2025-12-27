import os
import subprocess
import shutil
import sys

# Paths
XRAY_BIN_PATH = "/usr/local/bin/xray"
SERVICE_SRC = "/usr/local/lib/vortex-x/configs/systemd/xray.service"
SERVICE_DST = "/etc/systemd/system/xray.service"
XRAY_CONF_DIR = "/usr/local/etc/xray"
XRAY_LOG_DIR = "/var/log/xray"

def install_xray_binary():
    """
    Downloads and installs Xray core if not present.
    In a real scenario, this would fetch the latest release from GitHub.
    For this prototype, we'll verify if it exists or simulate installation.
    """
    if os.path.exists(XRAY_BIN_PATH):
        print("[INFO] Xray binary already installed.")
        return

    print("[INFO] Installing Xray Core...")
    # Using the official install script is standard, but here we can't fetch easily.
    # We will assume the user has internet access or we provide a helper.
    # For now, we will try to download the official install script.
    try:
        install_cmd = "bash -c \"$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)\" @ install"
        subprocess.run(install_cmd, shell=True, check=True)
        print("[SUCCESS] Xray installed.")
    except Exception as e:
        print(f"[ERROR] Failed to install Xray: {e}")
        print("Please install Xray manually: bash -c \"$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)\" @ install")

def harden_xray_service():
    print("[INFO] Applying Xray Systemd Hardening...")
    
    if not os.path.exists(SERVICE_SRC):
        # Fallback for dev environment
        dev_path = "./vpn_system/configs/systemd/xray.service"
        if os.path.exists(dev_path):
            shutil.copy(dev_path, SERVICE_DST)
        else:
            print(f"[ERROR] Service file not found at {SERVICE_SRC}")
            return
    else:
        shutil.copy(SERVICE_SRC, SERVICE_DST)

    # Reload Daemon
    subprocess.run(["systemctl", "daemon-reload"], check=False)
    subprocess.run(["systemctl", "enable", "xray"], check=False)
    
    # Permissions
    print("[INFO] Setting permissions...")
    dirs = [XRAY_CONF_DIR, XRAY_LOG_DIR]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
        subprocess.run(["chown", "-R", "vortex-x:vortex-x", d], check=False)
        subprocess.run(["chmod", "750", d], check=False) # Only owner and group can read
    
    # Ensure binary is executable
    if os.path.exists(XRAY_BIN_PATH):
        # Allow vortex-x to bind ports (if systemd caps fail for some reason, though caps are preferred)
        subprocess.run(["setcap", "cap_net_bind_service=+ep", XRAY_BIN_PATH], check=False)

    print("[SUCCESS] Xray service hardened and ready.")

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("This script must be run as root.")
        sys.exit(1)
        
    install_xray_binary()
    harden_xray_service()
