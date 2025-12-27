import json
import base64
from typing import Dict, Any

class ShadowsocksAdapter:
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

    def generate_inbound(self, port: int, method: str = "aes-256-gcm") -> Dict[str, Any]:
        inbound_tag = f"ss-{port}"
        
        inbound = {
            "tag": inbound_tag,
            "port": port,
            "listen": "0.0.0.0",
            "protocol": "shadowsocks",
            "settings": {
                "clients": [],
                "network": "tcp,udp",
                "method": method
            }
        }
        return inbound

    def add_user(self, inbound_tag: str, username: str) -> Dict[str, Any]:
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
        method = inbound["settings"]["method"]
        address = host['domain']
        port = inbound['port']
        
        # ss://base64(method:password)@address:port#tag
        auth = f"{method}:{password}"
        auth_base64 = base64.b64encode(auth.encode('utf-8')).decode('utf-8')
        return f"ss://{auth_base64}@{address}:{port}#{host['hostname']}"
    def remove_user(self, username: str) -> bool:
        removed = False
        for inbound in self.config.get("inbounds", []):
            clients = inbound.get("settings", {}).get("clients", [])
            original_count = len(clients)
            inbound["settings"]["clients"] = [c for c in clients if c.get("email") != username]
            if len(inbound["settings"]["clients"]) < original_count:
                removed = True
        return removed
