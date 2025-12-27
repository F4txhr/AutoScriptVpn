import json
import os
import sys
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
    if not os.path.exists(DB_PATH): return None
    with open(DB_PATH, 'r') as f: return json.load(f)

def save_db(data):
    with open(DB_PATH, 'w') as f: json.dump(data, f, indent=4)

def get_xray_stats():
    """Queries xray-core for user statistics via CLI."""
    try:
        # Note: This requires xray to have an api inbound on a local port
        # For simplicity in this script, we might parse xray logs or 
        # assume the user will configure the gRPC API.
        # Alternatively, we can use a mock/simplified version for now.
        return {} 
    except:
        return {}

def get_wg_stats():
    """Parses wireguard transfer stats."""
    stats = {}
    try:
        output = subprocess.check_output(["wg", "show", "wg0", "transfer"], universal_newlines=True)
        for line in output.splitlines():
            parts = line.split()
            if len(parts) >= 3:
                pubkey = parts[0]
                # Combine rx and tx
                usage = int(parts[1]) + int(parts[2])
                stats[pubkey] = usage
    except:
        pass
    return stats

def main():
    db = load_db()
    if not db: return

    wg_stats = get_wg_stats()
    # xray_stats = get_xray_stats() # Future implementation

    users = db.get("users", [])
    changes = False

    vless_adapter = VlessAdapter(config_path=XRAY_CONFIG_PATH)
    wg_adapter = WireguardAdapter(config_path=WG_CONFIG_PATH)

    active_users = []
    for user in users:
        # Quota check (Quota 0 means unlimited)
        quota = user.get("quota", 0)
        used = user.get("used_traffic", 0)

        # Update WireGuard usage
        if user['protocol'] == 'wireguard':
            pubkey = user.get('credentials', {}).get('public_key')
            if pubkey in wg_stats:
                # WireGuard 'transfer' is since service start, 
                # a real system would need persistent calculation.
                user['used_traffic'] = wg_stats[pubkey]
                used = user['used_traffic']

        if quota > 0 and used >= quota:
            print(f"User {user['username']} exceeded quota. Removing...")
            if user['protocol'] == 'vless':
                vless_adapter.remove_user(user['username'])
            elif user['protocol'] == 'wireguard':
                wg_adapter.remove_peer(user.get('credentials', {}).get('public_key'))
            changes = True
        else:
            active_users.append(user)

    if changes:
        vless_adapter._save_config()
        db['users'] = active_users
        save_db(db)
        # Restart services
        if shutil.which("systemctl"):
            subprocess.run(["systemctl", "restart", "xray"], check=False)
            subprocess.run(["systemctl", "restart", "wg-quick@wg0"], check=False)

if __name__ == "__main__":
    main()
