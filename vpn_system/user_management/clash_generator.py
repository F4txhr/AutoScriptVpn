import yaml
import json
from core.models import VortexDB

class ClashGenerator:
    def __init__(self):
        self.db = VortexDB()
        settings = self.db.data.get("settings", {})
        self.domain = settings.get("domain", "YOUR_DOMAIN")
        self.sni = settings.get("sni")
        self.host = settings.get("host")

    def generate_config(self, username: str) -> str:
        user = self.db.get_user(username)
        if not user:
            return "# User not found"

        config = {
            "port": 7890,
            "socks-port": 7891,
            "allow-lan": True,
            "mode": "rule",
            "log-level": "info",
            "proxies": [],
            "proxy-groups": [
                {
                    "name": "Vortex-x-Auto",
                    "type": "select",
                    "proxies": [user["username"], "DIRECT"]
                }
            ],
            "rules": ["MATCH,Vortex-x-Auto"]
        }

        proxy = {
            "name": user["username"],
            "server": self.domain,
            "port": 443,
            "udp": True,
            "tls": True,
            "skip-cert-verify": False
        }
        if self.sni:
            proxy["sni"] = self.sni

        if user["protocol"] == "vless":
            proxy.update({
                "type": "vless",
                "uuid": user["uuid"],
                "network": "ws",
                "ws-opts": {"path": "/vortex-vless"}
            })
        elif user["protocol"] == "vmess":
            proxy.update({
                "type": "vmess",
                "uuid": user["uuid"],
                "alterId": 0,
                "cipher": "auto",
                "network": "ws",
                "ws-opts": {"path": "/vortex-vmess"}
            })
        elif user["protocol"] == "trojan":
            proxy.update({
                "type": "trojan",
                "password": user["uuid"] # Using uuid as password for trojan
            })

        if self.host and proxy.get("network") == "ws":
            proxy["ws-opts"].setdefault("headers", {})["Host"] = self.host

        config["proxies"].append(proxy)
        return yaml.dump(config, default_flow_style=False)

if __name__ == "__main__":
    gen = ClashGenerator()
    # print(gen.generate_config("test_user"))
