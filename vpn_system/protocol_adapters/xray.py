import json
import os
import subprocess
from typing import Dict, Any, List

class XrayAdapter:
    def __init__(self, config_path: str = "/usr/local/etc/xray/config.json"):
        self.config_path = config_path
        self.config = self._load_default_config()
        # Ensure log section exists
        if "log" not in self.config:
            self.config["log"] = {}
        self.config["log"]["loglevel"] = "debug"
        self.config["log"]["access"] = "/var/log/xray/access.log"
        self.config["log"]["error"] = "/var/log/xray/error.log"

    def _load_default_config(self) -> Dict[str, Any]:
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    return json.load(f)
            except:
                pass
        
        return {
            "log": {
                "loglevel": "info",
                "access": "/var/log/xray/access.log",
                "error": "/var/log/xray/error.log"
            },
            "api": {"tag": "api", "services": ["HandlerService", "StatsService"]},
            "stats": {},
            "policy": {
                "levels": {"0": {"statsUserUplink": True, "statsUserDownlink": True}},
                "system": {"statsInboundUplink": True, "statsInboundDownlink": True}
            },
            "inbounds": [
                {
                    "listen": "127.0.0.1",
                    "port": 10085,
                    "protocol": "dokodemo-door",
                    "settings": {"address": "127.0.0.1"},
                    "tag": "api"
                }
            ],
            "outbounds": [
                {"protocol": "freedom", "tag": "direct"},
                {"protocol": "blackhole", "tag": "blocked"}
            ],
            "routing": {
                "rules": [
                    {"type": "field", "inboundTag": ["api"], "outboundTag": "api"},
                    {"type": "field", "ip": ["geoip:private"], "outboundTag": "blocked"}
                ]
            }
        }

    def add_inbound(self, protocol: str, port: int, tag: str, settings: Dict, stream_settings: Dict):
        inbound = {
            "protocol": protocol,
            "port": port,
            "listen": "127.0.0.1",
            "tag": tag,
            "settings": settings,
            "streamSettings": stream_settings,
            "sniffing": {"enabled": True, "destOverride": ["http", "tls"]}
        }
        self.config["inbounds"] = [
            i for i in self.config["inbounds"] 
            if i.get("tag") != tag and i.get("port") != port
        ]
        self.config["inbounds"].append(inbound)

    def clear_inbounds(self):
        self.config["inbounds"] = [
            i for i in self.config["inbounds"] if i.get("tag") == "api"
        ]

    def save(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, 'w') as f:
            json.dump(self.config, f, indent=4)
        
        # Ensure log directory and files exist
        log_dir = "/var/log/xray"
        os.makedirs(log_dir, exist_ok=True)
        
        # Permission handling is now centralized in harden_services.py
        # but we do a quick check here too
        try:
            subprocess.run(["chown", "-R", "vortex-x:vortex-x", os.path.dirname(self.config_path)], check=False)
            os.chmod(self.config_path, 0o644)
        except:
            pass

    def generate_vless_ws(self, port: int, path: str = "/vortex-vless"):
        settings = {"clients": [], "decryption": "none"}
        stream = {
            "network": "ws",
            "wsSettings": {"path": path}
        }
        self.add_inbound("vless", port, f"vless-ws-{port}", settings, stream)

    def generate_vmess_ws(self, port: int, path: str = "/vortex-vmess"):
        settings = {"clients": []}
        stream = {
            "network": "ws",
            "wsSettings": {"path": path}
        }
        self.add_inbound("vmess", port, f"vmess-ws-{port}", settings, stream)

    def generate_vless_grpc(self, port: int, service_name: str = "vortex-grpc"):
        settings = {"clients": [], "decryption": "none"}
        stream = {
            "network": "grpc",
            "grpcSettings": {"serviceName": service_name}
        }
        self.add_inbound("vless", port, f"vless-grpc-{port}", settings, stream)

    def generate_trojan_ws(self, port: int, path: str = "/vortex-trojan"):
        settings = {"clients": []}
        stream = {
            "network": "ws",
            "wsSettings": {"path": path}
        }
        self.add_inbound("trojan", port, f"trojan-ws-{port}", settings, stream)

    def generate_ss_ws(self, port: int, path: str = "/vortex-ss"):
        settings = {"clients": [], "method": "aes-256-gcm", "network": "tcp,udp"}
        stream = {
            "network": "ws",
            "wsSettings": {"path": path}
        }
        self.add_inbound("shadowsocks", port, f"ss-ws-{port}", settings, stream)

    def generate_vless_quic(self, port: int, security: str = "none", key: str = "", header_type: str = "none"):
        settings = {"clients": [], "decryption": "none"}
        stream = {
            "network": "quic",
            "quicSettings": {"security": security, "key": key, "header": {"type": header_type}}
        }
        self.add_inbound("vless", port, f"vless-quic-{port}", settings, stream)
