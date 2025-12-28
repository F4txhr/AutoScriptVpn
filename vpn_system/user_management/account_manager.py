import json
import os
import time
from core.models import VortexDB, UserAccount
from protocol_adapters.xray import XrayAdapter

class AccountManager:
    def __init__(self):
        self.db = VortexDB()
        self.xray = XrayAdapter()

    def create_user(self, username: str, protocol: str, days: int = 30) -> dict:
        # 1. Check if user already exists
        if self.db.get_user(username):
            raise ValueError(f"User '{username}' already exists.")

        # 2. Calculate expiry
        expires_at = int(time.time()) + (days * 86400)
        
        credentials = {}
        
        # 3. Handle Legacy Protocols
        if protocol == "wireguard":
            from protocol_adapters.wireguard import WireguardAdapter
            wg = WireguardAdapter()
            client_priv, client_pub = wg.generate_keys()
            # Simple IP allocation (next in line)
            user_count = len([u for u in self.db.data["users"] if u["protocol"] == "wireguard"])
            client_ip = f"10.0.0.{user_count + 2}/32"
            credentials = {
                "private_key": client_priv,
                "public_key": client_pub,
                "ip": client_ip
            }
            # Only add to peer if on a real VPS (not PRoot)
            if not os.environ.get("PROOT_TMPDIR"):
                try: wg.add_peer(client_pub, client_ip)
                except: pass

        elif protocol == "openvpn":
            # Call openvpn script to generate cert (simplified)
            try:
                subprocess.run(["/usr/local/lib/vortex-x/scripts/openvpn_helper.sh", "add", username], check=False)
            except: pass

        # 4. Create User Object
        new_user = UserAccount(
            username=username,
            protocol=protocol,
            expires_at=expires_at,
            password=credentials.get("password", "")
        )
        new_user.credentials = credentials # Custom field for legacy

        # 5. Sync with Xray if needed
        if protocol in ["vless", "vmess", "trojan", "shadowsocks"]:
            self._add_to_xray(new_user)
        
        self.db.add_user(new_user)
        self.xray.save()
        return new_user.to_dict()

    def generate_wg_config(self, user_dict: dict) -> str:
        creds = user_dict.get("credentials", {})
        domain = self.db.data["settings"].get("domain", "YOUR_DOMAIN")
        server_pub = ""
        try:
            with open("/usr/local/etc/vortex-x/server_wg_pub.key", "r") as f:
                server_pub = f.read().strip()
        except: server_pub = "SERVER_PUB_KEY_PLACEHOLDER"

        return f"""[Interface]
PrivateKey = {creds.get('private_key')}
Address = {creds.get('ip')}
DNS = 1.1.1.1

[Peer]
PublicKey = {server_pub}
Endpoint = {domain}:51820
AllowedIPs = 0.0.0.0/0
PersistentKeepalive = 25
"""

    def _add_to_xray(self, user: UserAccount) -> bool:
        found_inbound = False
        for inbound in self.xray.config.get("inbounds", []):
            if inbound.get("protocol") == user.protocol:
                # Add client based on protocol type
                if user.protocol in ["vless", "vmess"]:
                    client = {
                        "id": user.uuid,
                        "email": user.username,
                        "level": 0
                    }
                    if "clients" not in inbound["settings"]:
                        inbound["settings"]["clients"] = []
                    inbound["settings"]["clients"].append(client)
                    found_inbound = True
        return found_inbound

    def generate_vless_link(self, user_dict: dict) -> str:
        domain = self.db.data["settings"].get("domain", "YOUR_DOMAIN")
        uuid = user_dict["uuid"]
        name = user_dict["username"]
        path = "/vortex-vless"
        return f"vless://{uuid}@{domain}:443?type=ws&encryption=none&security=tls&path={path}&sni={domain}#{name}"

    def generate_vmess_link(self, user_dict: dict) -> str:
        import base64
        domain = self.db.data["settings"].get("domain", "YOUR_DOMAIN")
        vmess_config = {
            "v": "2",
            "ps": user_dict["username"],
            "add": domain,
            "port": "443",
            "id": user_dict["uuid"],
            "aid": "0",
            "scy": "auto",
            "net": "ws",
            "type": "none",
            "host": domain,
            "path": "/vortex-vmess",
            "tls": "tls",
            "sni": domain
        }
        encoded = base64.b64encode(json.dumps(vmess_config).encode()).decode()
        return f"vmess://{encoded}"
