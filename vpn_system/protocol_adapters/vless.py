import json
import uuid
import os
import subprocess
from typing import Dict, Any

class VlessAdapter:
    def __init__(self, config_path: str = "/usr/local/etc/xray/config.json"):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except:
            return {
                "log": {"loglevel": "info"},
                "inbounds": [], 
                "outbounds": [{"protocol": "freedom", "tag": "direct"}]
            }

    def _save_config(self):
        dir_name = os.path.dirname(self.config_path)
        if not os.path.exists(dir_name):
            os.makedirs(dir_name, exist_ok=True)

        # Atomic save
        temp_name = self.config_path + ".tmp"
        with open(temp_name, 'w') as f:
            json.dump(self.config, f, indent=4)
        os.replace(temp_name, self.config_path)
        
        # FIX PERMISSIONS: Ensure nobody can read it
        subprocess.run(["chown", "nobody:nobody", self.config_path], check=False)
        os.chmod(self.config_path, 0o644)

    def generate_inbound(self, port: int, transport: str, tls: bool, domain: str) -> Dict[str, Any]:
        inbound_tag = f"vless-{port}-{transport}"
        inbound = {
            "tag": inbound_tag,
            "port": port,
            "listen": "127.0.0.1", # Always local when behind Nginx
            "protocol": "vless",
            "settings": {
                "clients": [],
                "decryption": "none"
            },
            "streamSettings": {
                "network": transport
            }
        }

        if transport == "ws":
            inbound["streamSettings"]["wsSettings"] = {"path": "/Vortex-x"}
        elif transport == "grpc":
            inbound["streamSettings"]["grpcSettings"] = {"serviceName": "Vortex-x"}

        if tls:
            inbound["streamSettings"]["security"] = "tls"
            inbound["streamSettings"]["tlsSettings"] = {
                "serverName": domain,
                "certificates": [
                    {
                        "certificateFile": f"/etc/ssl/certs/{domain}/fullchain.pem",
                        "keyFile": f"/etc/ssl/certs/{domain}/privkey.pem"
                    }
                ]
            }
        return inbound

    def add_user(self, inbound_tag: str, username: str) -> Dict[str, Any]:
        user_uuid = str(uuid.uuid4())
        # SERVER SIDE: NO encryption parameter allowed here
        user_object = {
            "id": user_uuid,
            "email": username,
            "level": 0
        }

        for inbound in self.config.get("inbounds", []):
            if inbound.get("tag") == inbound_tag:
                if "clients" not in inbound["settings"]:
                    inbound["settings"]["clients"] = []
                inbound["settings"]["clients"].append(user_object)
                return user_object
        
        raise ValueError(f"Inbound {inbound_tag} not found")

    def get_user_uri(self, user: Dict, inbound: Dict, host: Dict) -> str:
        user_id = user["id"]
        address = host['domain']
        # Link always uses public port (443) if behind Nginx
        port = 443 if inbound['port'] == 10001 else inbound['port']
        transport = inbound['streamSettings']['network']

        params = [f"type={transport}", "encryption=none"]

        if transport == "ws":
            params.append("path=%2FVortex-x")
        elif transport == "grpc":
            params.append("serviceName=Vortex-x&mode=multi")

        if inbound['streamSettings'].get('security') == 'tls' or port == 443:
            params.append("security=tls")
            params.append(f"sni={host['domain']}")

        return f"vless://{user_id}@{address}:{port}?{'&'.join(params)}#{host['hostname']}-{transport}"