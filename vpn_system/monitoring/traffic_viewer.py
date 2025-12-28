import os
import time
import sys
import json
import subprocess

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.models import VortexDB

def get_traffic_stats():
    db = VortexDB()
    # Membersihkan layar terminal
    os.system('clear')
    print("==================================================")
    print("        VORTEX-X REAL-TIME TRAFFIC MONITOR        ")
    print("==================================================")
    print(f"{'USERNAME':<15} | {'PROTOCOL':<10} | {'USAGE':<10} | {'STATUS':<10}")
    print("-" * 50)

    for user in db.data.get("users", []):
        username = user.get("username", "Unknown")
        protocol = user.get("protocol", "N/A")
        # Konversi bytes ke MB/GB agar mudah dibaca
        usage_bytes = user.get("used_bandwidth", 0)
        if usage_bytes > 1024**3:
            usage = f"{usage_bytes / (1024**3):.2f} GB"
        else:
            usage = f"{usage_bytes / (1024**2):.2f} MB"
        
        status = user.get("status", "active")
        
        print(f"{username:<15} | {protocol:<10} | {usage:<10} | {status:<10}")
    
    print("-" * 50)
    print("Press Ctrl+C to return to Main Menu")

if __name__ == "__main__":
    try:
        while True:
            get_traffic_stats()
            time.sleep(2) # Refresh setiap 2 detik
    except KeyboardInterrupt:
        sys.exit(0)
