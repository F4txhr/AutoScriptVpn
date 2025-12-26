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
            # Return a default structure if the config doesn't exist
            return {"inbounds": [], "outbounds": [{"protocol": "freedom", "tag": "direct"}]}
        except json.JSONDecodeError:
            raise ValueError(f"Invalid JSON in {self.config_path}")

    def _save_config(self):
        """Saves the configuration back to the file."""
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=4)

    def generate_inbound(self, port: int, transport: str, tls: bool, domain: str) -> Dict[str, Any]:
        """
        Generates a VLESS inbound configuration fragment.
        """
        inbound_tag = f"vless-{port}-{transport}"

        inbound = {
            "tag": inbound_tag,
            "port": port,
            "listen": "0.0.0.0",
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
            inbound["streamSettings"]["wsSettings"] = {"path": f"/{inbound_tag}"}
        elif transport == "grpc":
            inbound["streamSettings"]["grpcSettings"] = {"serviceName": inbound_tag}

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

    def get_user_uri(self, user: Dict, inbound: Dict, host: Dict) -> str:
        """
        Generates a VLESS URI for a given user and inbound configuration.
        """
        user_id = user["id"]
        address = host['domain']
        port = inbound['port']
        transport = inbound['streamSettings']['network']

        params = [f"type={transport}"]

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

if __name__ == '__main__':
    # Example usage (for testing)
    adapter = VlessAdapter(config_path="./config.json")

    # 1. Create a host entity (mock)
    my_host = {"domain": "test.com", "hostname": "server1"}

    # 2. Generate inbounds
    vless_ws_tls = adapter.generate_inbound(443, "ws", tls=True, domain=my_host['domain'])
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
