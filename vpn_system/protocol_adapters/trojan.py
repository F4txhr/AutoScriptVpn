import json
from typing import Dict, Any

class TrojanAdapter:
    def __init__(self, config_path: str = "/usr/local/etc/xray/config.json"):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        try:
            with open(self.config_path, 'r') as f: return json.load(f)
        except: return {"inbounds": [], "outbounds": []}

    def _save_config(self):
        import tempfile, os
        dir_name = os.path.dirname(self.config_path)
        try:
            with tempfile.NamedTemporaryFile('w', dir=dir_name, delete=False) as tf:
                json.dump(self.config, tf, indent=4)
                temp_name = tf.name
            os.replace(temp_name, self.config_path)
        except Exception as e:
            raise RuntimeError(f"Failed to save config: {e}")

    def generate_inbound(self, port: int, transport: str, tls: bool, domain: str) -> Dict[str, Any]:
        inbound_tag = f"trojan-{port}-{transport}"
        custom_path = "/Vortex-x"
        
        # Trojan essentially requires TLS
        inbound = {
            "tag": inbound_tag,
            "port": port,
            "listen": "0.0.0.0",
            "protocol": "trojan",
            "settings": {
                "clients": []
            },
            "streamSettings": {
                "network": transport,
                "security": "tls",
                "tlsSettings": {
                    "serverName": domain,
                    "certificates": [{"certificateFile": f"/etc/ssl/certs/{domain}/fullchain.pem", "keyFile": f"/etc/ssl/certs/{domain}/privkey.pem"}]
                }
            }
        }

        if transport == "ws":
            inbound["streamSettings"]["wsSettings"] = {"path": custom_path}
        elif transport == "grpc":
            inbound["streamSettings"]["grpcSettings"] = {"serviceName": "Vortex-x"}

        return inbound

    def add_user(self, inbound_tag: str, username: str) -> Dict[str, Any]:
        # Trojan uses password, usually we just use UUID as password for uniformity
        import uuid
        password = str(uuid.uuid4())
        
        user_object = {
            "password": password,
            "email": username
        }
        
        inbound_found = False
        for inbound in self.config.get("inbounds", []):
            if inbound.get("tag") == inbound_tag:
                inbound["settings"]["clients"].append(user_object)
                inbound_found = True
                break
        
        if not inbound_found: raise ValueError(f"Inbound {inbound_tag} not found")
        return user_object

    def get_user_uri(self, user: Dict, inbound: Dict, host: Dict) -> str:
        password = user["password"]
        address = host['domain']
        port = inbound['port']
        
        params = [f"sni={host['domain']}"]
        transport = inbound['streamSettings']['network']
        
    def remove_user(self, username: str) -> bool:
        removed = False
        for inbound in self.config.get("inbounds", []):
            clients = inbound.get("settings", {}).get("clients", [])
            original_count = len(clients)
            inbound["settings"]["clients"] = [c for c in clients if c.get("email") != username]
            if len(inbound["settings"]["clients"]) < original_count:
                removed = True
        return removed
