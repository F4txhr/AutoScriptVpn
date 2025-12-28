import os
import time
import psutil
import socket
import json
import subprocess
from datetime import datetime, timedelta

DB_PATH = "/usr/local/etc/vortex-x/db.json"

def get_size(bytes, suffix="B"):
    factor = 1024
    for unit in ["", "K", "M", "G", "T", "P"]:
        if bytes < factor:
            return f"{bytes:.2f}{unit}{suffix}"
        bytes /= factor

def check_service(service_name):
    """
    Check if a systemd service is active.
    """
    try:
        # Check systemd status
        cmd = ["systemctl", "is-active", service_name]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        if result.returncode == 0 and result.stdout.strip() == "active":
            return "Active"
        else:
            return "Stopped"
    except Exception:
        return "Unknown"

def get_ssl_days_left(domain):
    cert_path = f"/etc/letsencrypt/live/{domain}/fullchain.pem"
    if not os.path.exists(cert_path):
        return "No Cert"
    
    try:
        cmd = f"openssl x509 -enddate -noout -in {cert_path}"
        res = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        if res.returncode == 0:
            # Output format: notAfter=Mar 27 14:49:19 2026 GMT
            date_str = res.stdout.strip().split('=')[1]
            # Parse date
            cert_date = datetime.strptime(date_str, "%b %d %H:%M:%S %Y %Z")
            days_left = (cert_date - datetime.now()).days
            return f"{days_left} days"
    except Exception as e:
        return "Error"
    
    return "Unknown"

def get_metrics():
    # Uptime
    try:
        with open('/proc/uptime', 'r') as f:
            uptime_seconds = float(f.readline().split()[0])
            uptime_str = str(timedelta(seconds=int(uptime_seconds))).split('.')[0] # Remove microseconds
    except:
        uptime_str = "Unknown"

    # CPU & RAM
    try:
        cpu_usage = f"{psutil.cpu_percent(interval=0.1)}%"
        ram = psutil.virtual_memory()
        ram_usage = f"{get_size(ram.used)}/{get_size(ram.total)}"
    except:
        cpu_usage = "N/A"
        ram_usage = "N/A"
    
    # Disk
    try:
        disk = psutil.disk_usage('/')
        disk_usage = f"{disk.percent}%"
    except:
        disk_usage = "N/A"
    
    # Network Traffic
    try:
        net_io = psutil.net_io_counters()
        rx = get_size(net_io.bytes_recv)
        tx = get_size(net_io.bytes_sent)
    except:
        rx = "N/A"
        tx = "N/A"
    
    # App Specifics
    domain = ""
    total_users = 0
    
    if os.path.exists(DB_PATH):
        try:
            with open(DB_PATH, 'r') as f:
                data = json.load(f)
                domain = data.get("settings", {}).get("domain", "")
                total_users = len(data.get("users", []))
        except:
            pass

    ssl_info = get_ssl_days_left(domain) if domain else "No Domain"

    services = {
        "Xray": check_service("xray"),
        "Nginx": check_service("nginx"),
        "WireGuard": check_service("wg-quick@wg0"), # Assuming standard wg-quick service name
        "OpenVPN": check_service("openvpn")
    }

    metrics = {
        "hostname": socket.gethostname(),
        "os": "Linux",
        "uptime": uptime_str,
        "cpu": cpu_usage,
        "ram": ram_usage,
        "disk": disk_usage,
        "net_rx": rx,
        "net_tx": tx,
        "total_users": str(total_users),
        "ssl_expiry": ssl_info,
        "services": services
    }
    return metrics

if __name__ == "__main__":
    print(json.dumps(get_metrics()))