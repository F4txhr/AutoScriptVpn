import json
import uuid
from typing import Dict, Any

class VlessAdapter:
    """
    Adapter for managing VLESS protocol configurations for Xray.
    """

    def __init__(self, config_path: str = "/usr/local/etc/xray/config.json"):
        self.config_path = config_path
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Loads the Xray configuration file."""
        try:
            with open(self.config_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            # Return a default structure with stats and policy enabled
            return {
                "stats": {},
                "policy": {
                    "levels": {"0": {"statsUserUplink": True, "statsUserDownlink": True}},
                    "system": {"statsInboundUplink": True, "statsInboundDownlink": True}
                },
                "inbounds": [], 
                "outbounds": [{"protocol": "freedom", "tag": "direct"}]
            }
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON in {self.config_path}")

    def _save_config(self):
        """Saves the configuration back to the file using an atomic write."""
        import tempfile
        import os

        # Create a temporary file in the same directory to ensure atomic move works
        dir_name = os.path.dirname(self.config_path)
        
        # Ensure directory exists
        if not os.path.exists(dir_name):
            try:
                os.makedirs(dir_name, exist_ok=True)
            except OSError as e:
                raise RuntimeError(f"Failed to create directory {dir_name}: {e}")

        try:
            with tempfile.NamedTemporaryFile('w', dir=dir_name, delete=False) as tf:
                json.dump(self.config, tf, indent=4)
                temp_name = tf.name
            
            # Atomic replacement
            os.replace(temp_name, self.config_path)
            
            # Fix ownership so Xray service (nobody) can read it
            try:
                import shutil
                # Using subprocess for chown as it's more reliable for system users
                import subprocess
                subprocess.run(["chown", "nobody:nobody", self.config_path], check=False)
                os.chmod(self.config_path, 0o644)
            except:
                pass
        except (IOError, OSError) as e:
            if 'temp_name' in locals() and os.path.exists(temp_name):
                os.remove(temp_name)
            raise RuntimeError(f"Failed to save Xray config to {self.config_path}: {e}")

    def generate_inbound(self, port: int, transport: str, tls: bool, domain: str) -> Dict[str, Any]:
        """
        Generates a VLESS inbound configuration fragment with custom path /Vortex-x.
        """
        inbound_tag = f"vless-{port}-{transport}"
        custom_path = "/Vortex-x"

        inbound = {
            "tag": inbound_tag,
            "port": port,
            "listen": "::", # Support IPv4 and IPv6
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
            inbound["streamSettings"]["wsSettings"] = {"path": custom_path}
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
        """
        Adds a user to a specific VLESS inbound and returns the user object.
        """
        user_uuid = str(uuid.uuid4())
        # According to Xray docs, 'encryption' should NOT be here on the server side.
        user_object = {
            "id": user_uuid,
            "email": username,
            "flow": ""
        }

        inbound_found = False
        for inbound in self.config.get("inbounds", []):
            if inbound.get("tag") == inbound_tag:
                inbound["settings"]["clients"].append(user_object)
                inbound_found = True
                break

        if not inbound_found:
            raise ValueError(f"Inbound with tag '{inbound_tag}' not found.")

        # self._save_config() # Defer saving to a more explicit call
        return user_object

    def remove_user(self, username: str) -> bool:
        """
        Removes a user by email (username) from ALL inbounds.
        Returns True if at least one user was removed.
        """
        removed = False
        for inbound in self.config.get("inbounds", []):
            clients = inbound.get("settings", {}).get("clients", [])
            original_count = len(clients)
            # Filter out the user
            inbound["settings"]["clients"] = [c for c in clients if c.get("email") != username]
            if len(inbound["settings"]["clients"]) < original_count:
                removed = True
        
        return removed

    def get_user_uri(self, user: Dict, inbound: Dict, host: Dict) -> str:
        """
        Generates a VLESS URI for a given user and inbound configuration.
        """
        user_id = user["id"]
        address = host['domain']
        port = inbound['port']
        transport = inbound['streamSettings']['network']

        params = [f"type={transport}", "encryption=none"]

        if transport == "ws":
            path = inbound['streamSettings']['wsSettings']['path'].replace('/', '%2F')
            params.append(f"path={path}")
        elif transport == "grpc":
            service_name = inbound['streamSettings']['grpcSettings']['serviceName']
            params.append(f"serviceName={service_name}")
            params.append("mode=multi")

        if inbound['streamSettings'].get('security') == 'tls':
            params.append("security=tls")
            params.append(f"sni={host['domain']}")

        return f"vless://{user_id}@{address}:{port}?{'&'.join(params)}#{host['hostname']}-{transport}"

    def get_client_json(self, user: Dict, inbound: Dict, host: Dict) -> Dict[str, Any]:
        """
        Generates the full JSON configuration for clients like HTTP Custom.
        """
        transport = inbound['streamSettings']['network']
        security = inbound['streamSettings'].get('security', 'none')
        
        config = {
            "inbounds": [],
            "outbounds": [
                {
                    "mux": {"enabled": False},
                    "protocol": "vless",
                    "settings": {
                        "vnext": [
                            {
                                "address": host['domain'],
                                "port": inbound['port'],
                                "users": [
                                    {
                                        "id": user['id'],
                                        "level": 8,
                                        "encryption": "none"
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
                    "tag": "VLESS"
                }
            ],
            "policy": {
                "levels": {
                    "8": {
                        "connIdle": 300,
                        "downlinkOnly": 1,
                        "handshake": 4,
                        "uplinkOnly": 1
                    }
                }
            }
        }

        if transport == "ws":
            config["outbounds"][0]["streamSettings"]["wsSettings"] = {
                "headers": {},
                "path": inbound['streamSettings']['wsSettings']['path']
            }
        elif transport == "grpc":
            config["outbounds"][0]["streamSettings"]["grpcSettings"] = {
                "serviceName": inbound['streamSettings']['grpcSettings']['serviceName'],
                "multiMode": True
            }

        return config

if __name__ == '__main__':
    # Example usage (for testing)
    adapter = VlessAdapter(config_path="./config.json")

    # 1. Create a host entity (mock)
    my_host = {"domain": "test.com", "hostname": "server1"}

    # 2. Generate inbounds
    vless_ws_tls = adapter.generate_inbound(10001, "ws", tls=True, domain=my_host['domain'])
    vless_grpc_tls = adapter.generate_inbound(8443, "grpc", tls=True, domain=my_host['domain'])

    adapter.config["inbounds"].extend([vless_ws_tls, vless_grpc_tls])

    # 3. Add a user to both inbounds
    user1_ws = adapter.add_user(vless_ws_tls['tag'], "user-01")
    user1_grpc = adapter.add_user(vless_grpc_tls['tag'], "user-01") # In reality, you'd add the same user object

    # 4. Generate URIs
    uri1 = adapter.get_user_uri(user1_ws, vless_ws_tls, my_host)
    uri2 = adapter.get_user_uri(user1_grpc, vless_grpc_tls, my_host)

    print("Generated URIs:")
    print(uri1)
    print(uri2)

    # 5. Save the final config
    adapter._save_config()
    print("\\nSaved config.json with new inbounds and user.")
