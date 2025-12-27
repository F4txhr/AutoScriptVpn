import os
import sys
import json
import base64
from typing import Dict, Any, List

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.models import Database
from protocol_adapters.vless import VlessAdapter
from protocol_adapters.vmess import VmessAdapter
from protocol_adapters.trojan import TrojanAdapter
from protocol_adapters.shadowsocks import ShadowsocksAdapter

class OutputGenerator:
    def __init__(self):
        self.db = Database()
        self.adapters = {
            "vless": VlessAdapter(),
            "vmess": VmessAdapter(),
            "trojan": TrojanAdapter(),
            "shadowsocks": ShadowsocksAdapter()
        }

    def generate_outputs(self, username: str, protocol: str) -> List[Dict[str, str]]:
        user = self.db.get_user(username, protocol)
        if not user:
            return [{"error": f"User {username} not found for {protocol}"}]

        host = self.db.get_host(user['host_id'])
        if not host:
            return [{"error": "Host not found"}]

        outputs = []

        if protocol in self.adapters:
            adapter = self.adapters[protocol]
            inbounds = [i for i in self.db.data['inbounds'] if i['protocol'] == protocol and i['bound_host'] == host['host_id']]
            
            for ib in inbounds:
                # Reconstruct Xray inbound fragment enough for URI generation
                # This is a bit redundant but keeps adapters decoupling
                ib_mock = {
                    "port": ib['port'],
                    "settings": {"method": "aes-256-gcm"}, # Default method
                    "streamSettings": {
                        "network": ib['transport'],
                        "security": "tls" if ib['port'] in [443, 8443, 8444, 8445, 2087] else "none"
                    }
                }
                if ib['transport'] == "ws":
                    ib_mock["streamSettings"]["wsSettings"] = {"path": "/Vortex-x"}
                elif ib['transport'] == "grpc":
                    ib_mock["streamSettings"]["grpcSettings"] = {"serviceName": "Vortex-x"}

                user_creds = user['credentials']
                # Adapter expected user object format
                if protocol == 'vless':
                    user_obj = {"id": user_creds['uuid']}
                elif protocol == 'vmess':
                    user_obj = {"id": user_creds['uuid']}
                elif protocol == 'trojan':
                    user_obj = {"password": user_creds['password']}
                elif protocol == 'shadowsocks':
                    user_obj = {"password": user_creds['password']}
                
                uri = adapter.get_user_uri(user_obj, ib_mock, host)
                res = {
                    "name": f"{protocol.upper()} {ib['transport'].upper()} {'TLS' if ib_mock['streamSettings']['security'] == 'tls' else ''}".strip(),
                    "uri": uri
                }
                
                # Add JSON config for VLESS, VMess, and Trojan
                if protocol in ['vless', 'vmess', 'trojan']:
                    res["json_client"] = adapter.get_client_json(user_obj, ib_mock, host)
                
                outputs.append(res)

        elif protocol == 'wireguard':
            creds = user['credentials']
            # We need server public key. Let's assume it's stored or we can get it.
            # For this demo, let's use a placeholder if not found.
            server_pub = "SERVER_PUBLIC_KEY_PLACEHOLDER"
            if os.path.exists("/etc/wireguard/publickey"):
                with open("/etc/wireguard/publickey", "r") as f:
                    server_pub = f.read().strip()
            
            endpoint = f"{host['domain']}:51820"
            conf = f"[Interface]\nPrivateKey = {creds['private_key']}\nAddress = {creds['address']}\nDNS = 1.1.1.1\n\n[Peer]\nPublicKey = {server_pub}\nEndpoint = {endpoint}\nAllowedIPs = 0.0.0.0/0\nPersistentKeepalive = 25"
            outputs.append({
                "name": "WireGuard Config",
                "config": conf
            })

        elif protocol == 'openvpn':
            template = user['credentials'].get('ovpn_template', '')
            conf = template.replace("REPLACE_MY_IP", host['domain'])
            outputs.append({
                "name": "OpenVPN Config",
                "config": conf
            })

        return outputs

    def generate_clash_meta(self, username: str, protocol: str) -> str:
        # Simplified Clash Meta generator
        outputs = self.generate_outputs(username, protocol)
        # In a real system, this would be a full YAML
        return "Clash Meta config generation not fully implemented yet."

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--username", required=True)
    parser.add_argument("-p", "--protocol", required=True)
    args = parser.parse_args()
    
    gen = OutputGenerator()
    results = gen.generate_outputs(args.username, args.protocol)
    print(json.dumps(results, indent=4))
