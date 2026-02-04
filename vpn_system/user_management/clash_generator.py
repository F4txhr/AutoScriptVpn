import yaml
import json
from core.models import VortexDB

class ClashGenerator:
    def __init__(self):
        self.db = VortexDB()
        settings = self.db.data.get("settings", {})
        self.domain = settings.get("domain", "YOUR_DOMAIN")
        self.address = settings.get("connect_domain") or self.domain
        self.sni = settings.get("sni") or self.domain
        self.host = settings.get("host") or self.domain
        self.port = settings.get("port", 443)
        self.tls_insecure = settings.get("tls_insecure", False)
        self.vless_path = settings.get("vless_path", "/vortex-vless")
        self.vmess_path = settings.get("vmess_path", "/vortex-vmess")
        self.trojan_path = settings.get("trojan_path", "/vortex-trojan")

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
            "server": self.address,
            "port": self.port,
            "udp": True,
            "tls": True,
            "skip-cert-verify": self.tls_insecure
        }
        if self.sni:
            proxy["sni"] = self.sni

        if user["protocol"] == "vless":
            proxy.update({
                "type": "vless",
                "uuid": user["uuid"],
                "network": "ws",
                "ws-opts": {"path": self.vless_path}
            })
        elif user["protocol"] == "vmess":
            proxy.update({
                "type": "vmess",
                "uuid": user["uuid"],
                "alterId": 0,
                "cipher": "auto",
                "network": "ws",
                "ws-opts": {"path": self.vmess_path}
            })
        elif user["protocol"] == "trojan":
            proxy.update({
                "type": "trojan",
                "password": user["uuid"],
                "network": "ws",
                "ws-opts": {"path": self.trojan_path}
            })

        if self.host and proxy.get("network") == "ws":
            proxy["ws-opts"].setdefault("headers", {})["Host"] = self.host

        config["proxies"].append(proxy)
        return yaml.dump(config, default_flow_style=False)

if __name__ == "__main__":
    gen = ClashGenerator()
    # print(gen.generate_config("test_user"))
