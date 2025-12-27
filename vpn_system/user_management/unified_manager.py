import os
import sys
import uuid
from typing import Dict, Any, List

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.models import Database, UserAccount, Host
from protocol_adapters.vless import VlessAdapter
from protocol_adapters.vmess import VmessAdapter
from protocol_adapters.trojan import TrojanAdapter
from protocol_adapters.shadowsocks import ShadowsocksAdapter
from protocol_adapters.wireguard import WireguardAdapter
from protocol_adapters.openvpn import OpenVpnAdapter

XRAY_CONFIG_PATH = "/usr/local/etc/xray/config.json"

class UnifiedUserManager:
    def __init__(self):
        self.db = Database()
        self.xray_adapters = {
            "vless": VlessAdapter(XRAY_CONFIG_PATH),
            "vmess": VmessAdapter(XRAY_CONFIG_PATH),
            "trojan": TrojanAdapter(XRAY_CONFIG_PATH),
            "shadowsocks": ShadowsocksAdapter(XRAY_CONFIG_PATH)
        }

    def add_user(self, username: str, protocol: str, host_id: str) -> Dict[str, Any]:
        host_data = self.db.get_host(host_id)
        if not host_data:
            raise ValueError(f"Host with ID {host_id} not found.")
        
        # Check if user already exists
        if self.db.get_user(username, protocol):
             print(f"User {username} already exists for protocol {protocol}.")
             return self.db.get_user(username, protocol)

        credentials = {}
        
        if protocol in self.xray_adapters:
            adapter = self.xray_adapters[protocol]
            inbounds = [i for i in self.db.data['inbounds'] if i['protocol'] == protocol and i['bound_host'] == host_id]
            
            if not inbounds:
                raise ValueError(f"No inbounds found for protocol {protocol} on host {host_id}")

            # For Xray, usually all inbounds share the same credential for the same user
            user_uuid = str(uuid.uuid4())
            
            for ib in inbounds:
                # We need to modify the add_user in adapters to accept an optional ID to keep it consistent
                # For now, let's just use the first one's returned object and assume we can reuse ID
                if protocol == 'vless':
                    user_obj = adapter.add_user(ib['tag'], username)
                    credentials['uuid'] = user_obj['id']
                elif protocol == 'vmess':
                    user_obj = adapter.add_user(ib['tag'], username)
                    credentials['uuid'] = user_obj['id']
                elif protocol == 'trojan':
                    user_obj = adapter.add_user(ib['tag'], username)
                    credentials['password'] = user_obj['password']
                elif protocol == 'shadowsocks':
                    user_obj = adapter.add_user(ib['tag'], username)
                    credentials['password'] = user_obj['password']

            adapter._save_config()
            # Restart Xray
            import subprocess
            subprocess.run(["systemctl", "restart", "xray"], check=False)

        elif protocol == 'wireguard':
            adapter = WireguardAdapter()
            client_priv, client_pub = adapter.generate_keys()
            # Server info needed
            # In a real system, we'd store server pub key in Host entity
            # For now, let's assume we can get it from wg0.conf or similar
            credentials = {
                "private_key": client_priv,
                "public_key": client_pub,
                "address": "10.0.0.x/32" # Need a proper IP allocator
            }
            # Simplified IP allocation
            used_ips = [u['credentials'].get('address') for u in self.db.data['users'] if u['protocol'] == 'wireguard']
            next_ip = self._allocate_ip(used_ips, "10.0.0.0/24")
            credentials['address'] = next_ip
            
            peer_config = adapter.get_peer_config(client_pub, next_ip)
            adapter.add_peer_to_config(peer_config)
            subprocess.run(["wg", "syncconf", "wg0", "/etc/wireguard/wg0.conf"], check=False)

        elif protocol == 'openvpn':
            adapter = OpenVpnAdapter()
            ovpn_content = adapter.add_user(username)
            credentials = {"ovpn_template": ovpn_content}

        new_user = UserAccount(
            username=username,
            protocol=protocol,
            host_id=host_id,
            credentials=credentials
        )
        self.db.add_user(new_user)
        return new_user.to_dict()

    def _allocate_ip(self, used_ips: List[str], network: str) -> str:
        # Very basic allocator
        base = network.split('.')[0:3]
        for i in range(2, 254):
            ip = f"{'.'.join(base)}.{i}/32"
            if ip not in used_ips:
                return ip
        raise RuntimeError("No available IPs in network")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["add"])
    parser.add_argument("-u", "--username", required=True)
    parser.add_argument("-p", "--protocol", required=True)
    parser.add_argument("-hid", "--host_id", help="Host ID to use (defaults to first host)")
    
    args = parser.parse_args()
    
    manager = UnifiedUserManager()
    if args.command == "add":
        host_id = args.host_id
        if not host_id and manager.db.data['hosts']:
            host_id = manager.db.data['hosts'][0]['host_id']
        
        if not host_id:
            print("Error: No hosts found. Run system_init.py first.")
            sys.exit(1)
            
        user = manager.add_user(args.username, args.protocol, host_id)
        print(f"User {args.username} added successfully.")
