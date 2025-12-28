import time
import os
import sys

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.models import VortexDB
from protocol_adapters.xray import XrayAdapter

def cleanup_expired_users():
    db = VortexDB()
    xray = XrayAdapter()
    now = int(time.time())
    expired_count = 0
    
    active_users = []
    
    for user in db.data["users"]:
        if user["expires_at"] < now:
            print(f"[INFO] User '{user['username']}' has expired. Removing...")
            # Remove from Xray Config
            remove_from_xray(xray, user)
            expired_count += 1
        else:
            active_users.append(user)
            
    if expired_count > 0:
        db.data["users"] = active_users
        db.save()
        xray.save()
        # Reload services
        os.system("systemctl reload xray")
        os.system("systemctl reload nginx")
        print(f"[SUCCESS] Cleaned up {expired_count} expired users.")
    else:
        print("[INFO] No expired users found.")

def remove_from_xray(xray_adapter, user_dict):
    """
    Removes a client from Xray configuration based on username/email.
    """
    for inbound in xray_adapter.config.get("inbounds", []):
        if "settings" in inbound and "clients" in inbound["settings"]:
            # Filter out the expired user
            original_count = len(inbound["settings"]["clients"])
            inbound["settings"]["clients"] = [
                c for c in inbound["settings"]["clients"] 
                if c.get("email") != user_dict["username"]
            ]
            if len(inbound["settings"]["clients"]) < original_count:
                print(f"  - Removed {user_dict['username']} from {inbound.get('protocol')} inbound")

if __name__ == "__main__":
    cleanup_expired_users()
