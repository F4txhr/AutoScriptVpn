import json
import uuid
from typing import Dict, Any

class VmessAdapter:
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
        inbound_tag = f"vmess-{port}-{transport}"
        custom_path = "/Vortex-x"
        
        inbound = {
            "tag": inbound_tag,
            "port": port,
            "listen": "0.0.0.0",
            "protocol": "vmess",
            "settings": {
                "clients": []
            },
            "streamSettings": {
                "network": transport
            }
        }

        if transport == "ws":
            inbound["streamSettings"]["wsSettings"] = {"path": custom_path}
        elif transport == "grpc":
            inbound["streamSettings"]["grpcSettings"] = {"serviceName": "Vortex-x"}

        if tls:
            inbound["streamSettings"]["security"] = "tls"
            inbound["streamSettings"]["tlsSettings"] = {
                "serverName": domain,
                "certificates": [{"certificateFile": f"/etc/ssl/certs/{domain}/fullchain.pem", "keyFile": f"/etc/ssl/certs/{domain}/privkey.pem"}]
            }
        return inbound

    def add_user(self, inbound_tag: str, username: str) -> Dict[str, Any]:
        user_uuid = str(uuid.uuid4())
        # VMess client structure
        user_object = {
            "id": user_uuid,
            "alterId": 0,
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
        # VMess usually uses a base64 JSON blob for sharing
        import base64
        transport = inbound['streamSettings']['network']
        tls = inbound['streamSettings'].get('security', 'none')
        path = "/Vortex-x"
        
        vmess_json = {
            "v": "2",
            "ps": f"{host['hostname']}-vmess",
            "add": host['domain'],
            "port": inbound['port'],
            "id": user['id'],
            "aid": "0",
            "net": transport,
            "type": "none",
            "host": host['domain'],
            "path": path,
            "tls": tls
        }
        
        if transport == "grpc":
            vmess_json["path"] = "Vortex-x" # ServiceName
            vmess_json["type"] = "multi" # GRPC mode
            
        json_str = json.dumps(vmess_json)
        encoded = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
        return f"vmess://{encoded}"

    def get_client_json(self, user: Dict, inbound: Dict, host: Dict) -> Dict[str, Any]:
        transport = inbound['streamSettings']['network']
        security = inbound['streamSettings'].get('security', 'none')
        
        config = {
            "inbounds": [],
            "outbounds": [
                {
                    "mux": {"enabled": False},
                    "protocol": "vmess",
                    "settings": {
                        "vnext": [
                            {
                                "address": host['domain'],
                                "port": inbound['port'],
                                "users": [
                                    {
                                        "id": user['id'],
                                        "alterId": 0,
                                        "level": 8,
                                        "security": "auto"
                                    }
                                ]
                            }
                        ]
                    },
                    "streamSettings": {
                        "network": transport,
                        "security": security,
                        "tlsSettings": {
                            "allowInsecure": True,
                            "serverName": host['domain']
                        }
                    },
                    "tag": "VMESS"
                }
            ],
            "policy": {
                "levels": {"8": {"connIdle": 300, "downlinkOnly": 1, "handshake": 4, "uplinkOnly": 1}}
            }
        }

        if transport == "ws":
            config["outbounds"][0]["streamSettings"]["wsSettings"] = {
                "headers": {},
                "path": "/Vortex-x"
            }
        elif transport == "grpc":
            config["outbounds"][0]["streamSettings"]["grpcSettings"] = {
                "serviceName": "Vortex-x",
                "multiMode": True
            }

        return config
    def remove_user(self, username: str) -> bool:
        removed = False
        for inbound in self.config.get("inbounds", []):
            clients = inbound.get("settings", {}).get("clients", [])
            original_count = len(clients)
            inbound["settings"]["clients"] = [c for c in clients if c.get("email") != username]
            if len(inbound["settings"]["clients"]) < original_count:
                removed = True
        return removed
