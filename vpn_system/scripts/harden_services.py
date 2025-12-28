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
    
    # Remove any conflicting drop-ins from other installers
    dropin_dir = "/etc/systemd/system/xray.service.d"
    if os.path.exists(dropin_dir):
        print(f"[INFO] Removing conflicting drop-in directory: {dropin_dir}")
        shutil.rmtree(dropin_dir)

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
    print("[INFO] Setting permissions for vortex-x user...")
    dirs = [XRAY_CONF_DIR, XRAY_LOG_DIR]
    
    # Ensure vortex-x user exists
    subprocess.run(["id", "-u", "vortex-x"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if subprocess.run(["id", "-u", "vortex-x"], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode != 0:
        subprocess.run(["useradd", "-r", "-s", "/usr/sbin/nologin", "vortex-x"], check=False)

    for d in dirs:
        os.makedirs(d, exist_ok=True)
        # Force ownership to vortex-x
        subprocess.run(["chown", "-R", "vortex-x:vortex-x", d], check=False)
        subprocess.run(["chmod", "-R", "755", d], check=False) 
        
        # SELinux context fix for logs (Critical for RHEL/Alinux)
        if d == XRAY_LOG_DIR and command_exists("chcon"):
            print(f"[INFO] Setting SELinux context for {d}...")
            subprocess.run(["chcon", "-R", "-t", "var_log_t", d], check=False)
    
    # Ensure log files exist and are writable
    for log_f in ["access.log", "error.log"]:
        log_p = os.path.join(XRAY_LOG_DIR, log_f)
        if not os.path.exists(log_p):
            with open(log_p, 'a'): os.utime(log_p, None)
        subprocess.run(["chown", "vortex-x:vortex-x", log_p], check=False)
        subprocess.run(["chmod", "664", log_p], check=False)
        if command_exists("chcon"):
            subprocess.run(["chcon", "-t", "var_log_t", log_p], check=False)

def command_exists(cmd):
    return shutil.which(cmd) is not None

    # Ensure binary is executable
    if os.path.exists(XRAY_BIN_PATH):
        subprocess.run(["setcap", "cap_net_bind_service=+ep", XRAY_BIN_PATH], check=False)

    print("[SUCCESS] Xray service hardened and log permissions fixed.")

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("This script must be run as root.")
        sys.exit(1)
        
    install_xray_binary()
    harden_xray_service()
