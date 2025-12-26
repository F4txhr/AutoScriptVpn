import argparse
import json
import os
import sys

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.models import Host, UserAccount
from protocol_adapters.wireguard import WireguardAdapter

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'configs', 'db.json')
WG_CONFIG_PATH = "/etc/wireguard/wg0.conf"
CLIENT_CONFIG_DIR = os.path.join(os.path.dirname(__file__), '..', 'configs', 'wireguard_clients')

def load_db() -> dict:
    if not os.path.exists(DB_PATH):
        return {"hosts": [], "users": [], "wireguard": {"last_ip_octet": 1}}
    with open(DB_PATH, 'r') as f:
        return json.load(f)

def save_db(data: dict):
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with open(DB_PATH, 'w') as f:
        json.dump(data, f, indent=4)

def add_wireguard_user(username: str, domain: str):
    db = load_db()
    adapter = WireguardAdapter(config_path=WG_CONFIG_PATH)

    # Ensure the wireguard config section exists in the DB
    if 'wireguard' not in db:
        db['wireguard'] = {'last_ip_octet': 1}

    # --- Host and Server Setup ---
    host = next((h for h in db['hosts'] if h['domain'] == domain), None)
    if not host:
        print(f"No host found for domain {domain}. Please create the host first.")
        # In a real scenario, you'd create it or have a separate host management script.
        # For this example, we'll assume the host exists.
        # Let's create a placeholder host for now.
        host = Host(hostname=domain.split('.')[0], domain=domain, ip="127.0.0.1", location="default", status="active", supported_protocols=["wireguard"], health_score=100.0).__dict__
        db['hosts'].append(host)


    # Initialize WireGuard server config if it's not in the DB
    if 'server_public_key' not in db['wireguard']:
        print("WireGuard server details not found in DB. Initializing server config.")
        server_private_key, server_public_key = adapter.generate_keys()
        server_config = adapter.get_server_config(server_private_key, "10.0.0.1/24", 51820)

        os.makedirs(os.path.dirname(adapter.config_path), exist_ok=True)
        with open(adapter.config_path, "w") as f:
            f.write(server_config)

        db['wireguard']['server_public_key'] = server_public_key
        db['wireguard']['server_private_key'] = server_private_key

    server_public_key = db['wireguard']['server_public_key']

    # --- User and Peer Management ---
    user = next((u for u in db['users'] if u['username'] == username and u['protocol'] == 'wireguard'), None)
    if user:
        print(f"User '{username}' already exists for WireGuard.")
        return

    print(f"Creating new WireGuard user: {username}")

    # Simple IP allocation
    last_octet = db['wireguard'].get('last_ip_octet', 1) + 1
    client_ip = f"10.0.0.{last_octet}/32"
    db['wireguard']['last_ip_octet'] = last_octet

    client_private_key, client_public_key = adapter.generate_keys()

    # Add peer to server config
    peer_config = adapter.get_peer_config(client_public_key, client_ip)
    adapter.add_peer_to_config(peer_config)

    # Save user to DB
    new_user = UserAccount(
        username=username,
        protocol="wireguard",
        host_id=host['host_id'],
        credentials={"private_key": client_private_key, "public_key": client_public_key, "ip": client_ip},
        quota=0, used_traffic=0, expiry_date="", status="active", last_active=""
    ).__dict__
    db['users'].append(new_user)

    # --- Client Config Generation ---
    client_config = adapter.generate_client_config(
        private_key=client_private_key,
        client_address=client_ip.replace("/32", "/24"), # Client needs the subnet mask
        server_public_key=server_public_key,
        server_endpoint=f"{domain}:51820"
    )

    os.makedirs(CLIENT_CONFIG_DIR, exist_ok=True)
    client_config_path = os.path.join(CLIENT_CONFIG_DIR, f"{username}.conf")
    with open(client_config_path, "w") as f:
        f.write(client_config)

    save_db(db)

    print("\\n" + "="*50)
    print(f"Successfully created WireGuard user '{username}'")
    print("Server config updated. Please reload the WireGuard service (e.g., 'wg-quick down wg0 && wg-quick up wg0').")
    print(f"Client configuration file saved to: {client_config_path}")
    print("="*50)


def main():
    parser = argparse.ArgumentParser(description="Manage WireGuard users.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_add = subparsers.add_parser("add", help="Add a new WireGuard user.")
    parser_add.add_argument("-u", "--username", required=True, help="Username for the new user.")
    parser_add.add_argument("-d", "--domain", required=True, help="The server's public domain or IP.")

    args = parser.parse_args()

    # Use local mock paths for demonstration
    global WG_CONFIG_PATH, CLIENT_CONFIG_DIR
    WG_CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'configs', 'wg0.conf')
    CLIENT_CONFIG_DIR = os.path.join(os.path.dirname(__file__), '..', 'configs', 'wireguard_clients')

    if args.command == "add":
        add_wireguard_user(args.username, args.domain)

if __name__ == "__main__":
    main()
