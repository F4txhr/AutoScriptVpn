import argparse
import json
import os
import shutil
import subprocess
from typing import Dict, Any

# Try to import psutil, provide a helpful error message if it's not installed.
try:
    import psutil
except ImportError:
    print("Error: The 'psutil' library is required for monitoring. Please install it using 'pip install psutil'")
    exit(1)

def get_system_metrics() -> Dict[str, Any]:
    """Gathers basic system metrics: CPU, RAM, and Disk."""
    metrics = {}

    # CPU
    metrics['cpu'] = {
        "usage_percent": psutil.cpu_percent(interval=1),
        "load_avg": [round(x / psutil.cpu_count() * 100, 2) for x in psutil.getloadavg()]
    }

    # RAM
    ram = psutil.virtual_memory()
    metrics['ram'] = {
        "total_gb": round(ram.total / (1024**3), 2),
        "used_gb": round(ram.used / (1024**3), 2),
        "free_gb": round(ram.available / (1024**3), 2),
        "usage_percent": ram.percent
    }

    # Disk
    disk = psutil.disk_usage('/')
    metrics['disk'] = {
        "total_gb": round(disk.total / (1024**3), 2),
        "used_gb": round(disk.used / (1024**3), 2),
        "free_gb": round(disk.free / (1024**3), 2),
        "usage_percent": disk.percent
    }

    return metrics

def get_service_status(service_name: str) -> str:
    """Checks the status of a systemd service."""
    try:
        # We use `is-active` for a simple 'active' or 'inactive'/'failed' state
        result = subprocess.run(
            ["systemctl", "is-active", service_name],
            capture_output=True,
            text=True,
            check=False # Don't raise exception for non-zero exit codes
        )
        status = result.stdout.strip()
        if status in ["active", "reloading"]:
             return "RUNNING"
        elif status == "inactive":
             return "STOPPED"
        elif status == "failed":
             return "FAILED"
        else:
             return status.upper()

    except FileNotFoundError:
        return "NOT_FOUND (systemctl missing?)"
    except Exception as e:
        return f"ERROR ({e})"

def calculate_health_score(metrics: Dict, services_status: Dict) -> float:
    """Calculates a numeric health score from 0 to 100."""
    score = 100.0
    
    # Resource penalties
    if metrics['cpu']['usage_percent'] > 80: score -= 10
    if metrics['cpu']['usage_percent'] > 95: score -= 20
    
    if metrics['ram']['usage_percent'] > 80: score -= 10
    if metrics['ram']['usage_percent'] > 95: score -= 20
    
    if metrics['disk']['usage_percent'] > 80: score -= 10
    if metrics['disk']['usage_percent'] > 95: score -= 20
    
    # Service penalties
    for service, status in services_status.items():
        if status != "RUNNING":
            score -= 15
    
    return max(0.0, score)

def generate_report(metrics: Dict, services_status: Dict, health_score: float) -> str:
    """Generates a human-readable report."""
    report = []
    report.append("="*30)
    report.append(f"  System Health: {health_score}/100")
    report.append("="*30)
    report.append("\\n--- Host Metrics ---")
    report.append(f"  CPU Usage: {metrics['cpu']['usage_percent']}%")
    report.append(f"  CPU Load (1, 5, 15 min): {metrics['cpu']['load_avg']}")
    report.append(f"  RAM Usage: {metrics['ram']['usage_percent']}% ({metrics['ram']['used_gb']} GB / {metrics['ram']['total_gb']} GB)")
    report.append(f"  Disk Usage (/): {metrics['disk']['usage_percent']}% ({metrics['disk']['used_gb']} GB / {metrics['disk']['total_gb']} GB)")

    report.append("\\n--- VPN Service Status ---")
    for service, status in services_status.items():
        report.append(f"  {service}: {status}")

    report.append("\\n" + "="*30)
    return "\\n".join(report)

def main():
    """Main function to run the health check."""
    parser = argparse.ArgumentParser(description="System and VPN service health check.")
    parser.add_argument("--json", action="store_true", help="Output the report in JSON format.")
    args = parser.parse_args()

    # --- Gather Data ---
    system_metrics = get_system_metrics()

    # List of services to monitor
    vpn_services = ["xray", "wg-quick@wg0", "openvpn@server", "nginx"]
    services_status = {service: get_service_status(service) for service in vpn_services}
    
    health_score = calculate_health_score(system_metrics, services_status)

    # --- Output Report ---
    if args.json:
        full_report = {
            "health_score": health_score,
            "host_metrics": system_metrics,
            "service_status": services_status
        }
        print(json.dumps(full_report, indent=4))
    else:
        report_str = generate_report(system_metrics, services_status, health_score)
        print(report_str)

if __name__ == "__main__":
    main()
