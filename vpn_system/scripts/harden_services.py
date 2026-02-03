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

def command_exists(cmd):
    return shutil.which(cmd) is not None

def get_selinux_status():
    if not command_exists("getenforce"):
        return "Disabled"
    try:
        res = subprocess.run(["getenforce"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        return res.stdout.strip()
    except:
        return "Disabled"

def apply_selinux_context(path, context_type="var_log_t"):
    status = get_selinux_status()
    if status == "Disabled":
        return

    print(f"[INFO] Applying SELinux context to {path}...")
    
    # Method 1: restorecon (Standard)
    if command_exists("restorecon"):
        subprocess.run(["restorecon", "-R", path], check=False)
    
    # Method 2: chcon with full context (more forceful for unlabeled)
    if command_exists("chcon"):
        # Full context string helps if file is currently unlabeled
        full_context = f"system_u:object_r:{context_type}:s0"
        subprocess.run(["chcon", "-R", "-t", context_type, path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        # If still fails, try forcing the full string
        subprocess.run(["chcon", "-R", full_context, path], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

def install_xray_binary():
    if os.path.exists(XRAY_BIN_PATH):
        print("[INFO] Xray binary already installed.")
        return

    print("[INFO] Installing Xray Core...")
    try:
        install_cmd = "bash -c \"$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)\" @ install"
        subprocess.run(install_cmd, shell=True, check=True)
        print("[SUCCESS] Xray installed.")
    except Exception as e:
        print(f"[ERROR] Failed to install Xray: {e}")

def harden_xray_service():
    print("[INFO] Applying Xray Systemd Hardening...")
    
    # Remove any conflicting drop-ins
    dropin_dir = "/etc/systemd/system/xray.service.d"
    if os.path.exists(dropin_dir):
        shutil.rmtree(dropin_dir)

    # Deploy Service File
    src = SERVICE_SRC if os.path.exists(SERVICE_SRC) else "./vpn_system/configs/systemd/xray.service"
    if os.path.exists(src):
        shutil.copy(src, SERVICE_DST)
    
    subprocess.run(["systemctl", "daemon-reload"], check=False)
    subprocess.run(["systemctl", "enable", "xray"], check=False)
    
    # User Creation
    subprocess.run(["id", "-u", "vortex-x"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if subprocess.run(["id", "-u", "vortex-x"], stdout=subprocess.PIPE, stderr=subprocess.PIPE).returncode != 0:
        subprocess.run(["useradd", "-r", "-s", "/usr/sbin/nologin", "vortex-x"], check=False)

    # Permissions
    dirs = [XRAY_CONF_DIR, XRAY_LOG_DIR]
    for d in dirs:
        os.makedirs(d, exist_ok=True)
        subprocess.run(["chown", "-R", "vortex-x:vortex-x", d], check=False)
        subprocess.run(["chmod", "750", d], check=False)
        apply_selinux_context(d)

    config_path = os.path.join(XRAY_CONF_DIR, "config.json")
    if os.path.exists(config_path):
        subprocess.run(["chown", "vortex-x:vortex-x", config_path], check=False)
        subprocess.run(["chmod", "644", config_path], check=False)
    
    # Specific Log Files
    for log_f in ["access.log", "error.log"]:
        log_p = os.path.join(XRAY_LOG_DIR, log_f)
        if not os.path.exists(log_p):
            with open(log_p, 'a'): os.utime(log_p, None)
        subprocess.run(["chown", "vortex-x:vortex-x", log_p], check=False)
        subprocess.run(["chmod", "664", log_p], check=False)
        apply_selinux_context(log_p)

    # Binary Capabilities
    if os.path.exists(XRAY_BIN_PATH):
        subprocess.run(["setcap", "cap_net_bind_service=+ep", XRAY_BIN_PATH], check=False)

    print("[SUCCESS] Xray service hardened and SELinux applied.")

if __name__ == "__main__":
    if os.geteuid() != 0:
        print("This script must be run as root.")
        sys.exit(1)
    install_xray_binary()
    harden_xray_service()
