import json
import os
import sys
import datetime
import subprocess
import shutil

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from protocol_adapters.vless import VlessAdapter
from protocol_adapters.wireguard import WireguardAdapter

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'configs', 'db.json')
XRAY_CONFIG_PATH = "/usr/local/etc/xray/config.json"
WG_CONFIG_PATH = "/etc/wireguard/wg0.conf"

def load_db():
    if not os.path.exists(DB_PATH):
        return None
    with open(DB_PATH, 'r') as f:
        return json.load(f)

def save_db(data):
    with open(DB_PATH, 'w') as f:
        json.dump(data, f, indent=4)

def restart_service(service_name):
    if shutil.which("systemctl"):
        try:
            subprocess.run(["systemctl", "restart", service_name], check=True)
            print(f"Restarted {service_name}")
        except Exception as e:
            print(f"Failed to restart {service_name}: {e}")

def main():
    print("--- Running Auto-Expiry Check ---")
    db = load_db()
    if not db:
        print("Database not found.")
        return

    users = db.get("users", [])
    if not users:
        print("No users found.")
        return

    today = datetime.datetime.now().strftime("%Y-%m-%d")
    users_to_remove = []
    
    # Identify expired users
    for user in users:
        expiry = user.get("expiry_date")
        if expiry and expiry < today:
            users_to_remove.append(user)

    if not users_to_remove:
        print("No expired users found.")
        return

    # Process removals
    vless_changes = False
    wg_changes = False

    vless_adapter = VlessAdapter(config_path=XRAY_CONFIG_PATH)
    wg_adapter = WireguardAdapter(config_path=WG_CONFIG_PATH)

    active_users = []
    
    # Rebuild user list (excluding expired)
    # We do this carefully to ensure we call the adapter removal logic
    
    for user in users:
        if user in users_to_remove:
            print(f"Removing expired user: {user['username']} (Protocol: {user['protocol']})")
            
            if user['protocol'] == 'vless':
                if vless_adapter.remove_user(user['username']):
                    vless_changes = True
            
            elif user['protocol'] == 'wireguard':
                pub_key = user.get('credentials', {}).get('public_key')
                if pub_key:
                    wg_adapter.remove_peer(pub_key)
                    wg_changes = True
        else:
            active_users.append(user)

    # Save changes
    if vless_changes:
        vless_adapter._save_config()
        restart_service("xray")

    # WireGuard adapter saves immediately on remove_peer, just reload
    if wg_changes:
        restart_service("wg-quick@wg0")

    db['users'] = active_users
    save_db(db)
    print(f"Cleanup complete. Removed {len(users_to_remove)} users.")

if __name__ == "__main__":
    main()
