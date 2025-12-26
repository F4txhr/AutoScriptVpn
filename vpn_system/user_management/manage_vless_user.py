import argparse
import json
import os
import sys
import uuid
from typing import Dict, Any, List

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.models import Host, UserAccount
from protocol_adapters.vless import VlessAdapter

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'configs', 'db.json')
XRAY_CONFIG_PATH = "/usr/local/etc/xray/config.json" # In a real system, this path is correct

def load_db() -> Dict[str, Any]:
    """Loads a simple JSON database for hosts and users."""
    if not os.path.exists(DB_PATH):
        return {"hosts": [], "users": []}
    with open(DB_PATH, 'r') as f:
        return json.load(f)

def save_db(data: Dict[str, Any]):
    """Saves data to the JSON database."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    with open(DB_PATH, 'w') as f:
        json.dump(data, f, indent=4)

def add_vless_user(username: str, domain: str):
    """
    Adds a new VLESS user, creates necessary inbounds, and generates URIs.
    """
    db = load_db()
    adapter = VlessAdapter(config_path=XRAY_CONFIG_PATH)

    # --- Host Management ---
    host = next((h for h in db['hosts'] if h['domain'] == domain), None)
    if not host:
        print(f"No host found for domain {domain}. Creating a new host entry.")
        host = Host(
            hostname=domain.split('.')[0],
            domain=domain,
            ip="127.0.0.1", # Placeholder
            location="default",
            status="active",
            supported_protocols=["vless"],
            health_score=100.0
        ).__dict__
        db['hosts'].append(host)

    # --- User Management ---
    user = next((u for u in db['users'] if u['username'] == username and u['host_id'] == host['host_id']), None)
    if user:
        print(f"User '{username}' already exists on host '{domain}'.")
        return

    print(f"Creating new user '{username}' on host '{domain}'.")

    # Create a single user object with a consistent UUID
    user_credentials = {"uuid": str(uuid.uuid4())}
    new_user = UserAccount(
        username=username,
        protocol="vless",
        host_id=host['host_id'],
        credentials=user_credentials,
        quota=0, used_traffic=0, expiry_date="", status="active", last_active=""
    ).__dict__
    db['users'].append(new_user)

    # --- Inbound and Config Generation ---
    # Define the transports that should be automatically generated for VLESS
    vless_presets = {
        "vless-443-ws-tls": {"port": 443, "transport": "ws", "tls": True},
        "vless-8443-grpc-tls": {"port": 8443, "transport": "grpc", "tls": True},
        "vless-80-ws-http": {"port": 80, "transport": "ws", "tls": False}
    }

    generated_uris: List[str] = []

    for preset_name, preset_details in vless_presets.items():
        # Check if a suitable inbound already exists
        inbound = next((ib for ib in adapter.config.get("inbounds", []) if ib.get("port") == preset_details['port']), None)

        if not inbound:
            print(f"Inbound for port {preset_details['port']} not found. Generating new one...")
            inbound = adapter.generate_inbound(
                port=preset_details['port'],
                transport=preset_details['transport'],
                tls=preset_details['tls'],
                domain=domain
            )
            adapter.config.get("inbounds", []).append(inbound)

        # Add user to this inbound (using the consistent UUID)
        print(f"Adding user '{username}' to inbound '{inbound['tag']}'...")
        user_for_inbound = {
            "id": user_credentials['uuid'],
            "email": username,
            "flow": ""
        }

        # Ensure the 'clients' list exists
        if 'clients' not in inbound['settings']:
            inbound['settings']['clients'] = []

        inbound['settings']['clients'].append(user_for_inbound)

        # Generate output URI
        uri = adapter.get_user_uri(user_for_inbound, inbound, host)
        generated_uris.append(uri)

    # --- Finalization ---
    adapter._save_config()
    save_db(db)

    print("\\n" + "="*50)
    print(f"Successfully created user '{username}'")
    print("Xray config updated. Please reload the Xray service.")
    print("Generated Client URIs:")
    for uri in generated_uris:
        print(f"  - {uri}")
    print("="*50)


def main():
    parser = argparse.ArgumentParser(description="Manage VLESS users and configurations.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # --- Add user command ---
    parser_add = subparsers.add_parser("add", help="Add a new VLESS user.")
    parser_add.add_argument("-u", "--username", required=True, help="Username for the new user.")
    parser_add.add_argument("-d", "--domain", required=True, help="The domain/host for the user.")

    args = parser.parse_args()

    # For demonstration, we'll use a local mock config path
    global XRAY_CONFIG_PATH
    XRAY_CONFIG_PATH = os.path.join(os.path.dirname(__file__), '..', 'configs', 'xray_config.json')

    if args.command == "add":
        add_vless_user(args.username, args.domain)

if __name__ == "__main__":
    main()