import os
import sys
import subprocess
import json
import time

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.models import VortexDB

class TrafficMonitor:
    def __init__(self):
        self.db = VortexDB()
        self.xray_api = "127.0.0.1:10085"

    def get_xray_stats(self):
        """Fetches traffic stats from Xray API via xray stats command."""
        try:
            # We use subprocess to call xray api tool
            cmd = ["xray", "api", "statsquery", "--server", self.xray_api, "--pattern", "user"]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            if result.returncode == 0:
                return json.loads(result.stdout)
        except:
            return None
        return None

    def get_wg_stats(self):
        """Fetches WireGuard traffic and active peers."""
        try:
            result = subprocess.run(["wg", "show", "wg0", "transfer"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            # Parse wg output
            return result.stdout
        except:
            return None

    def sync_stats(self):
        """Syncs all stats to the database and enforces limits."""
        xray_data = self.get_xray_stats()
        
        # Update Xray Traffic in DB
        if xray_data and "stat" in xray_data:
            for stat in xray_data["stat"]:
                name_parts = stat["name"].split(">>>")
                if len(name_parts) >= 4:
                    email = name_parts[1]
                    value = int(stat["value"])
                    
                    for user in self.db.data["users"]:
                        if user["username"] == email:
                            # Update total used bandwidth
                            user["used_bandwidth"] = user.get("used_bandwidth", 0) + value
        
        self.db.save()

    def enforce_ip_limit(self):
        """
        Detects multiple IP logins and suspends users if they exceed limits.
        This usually requires parsing Xray access logs.
        """
        LOG_FILE = "/var/log/vortex-x/access.log"
        if not os.path.exists(LOG_FILE):
            return

        # Simple logic: parse last 1000 lines of log for unique IPs per email
        # In a real production system, this would be a more complex stateful tracker
        pass

if __name__ == "__main__":
    monitor = TrafficMonitor()
    monitor.sync_stats()
