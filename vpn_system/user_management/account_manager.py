import json
import os
import time
from urllib.parse import quote, urlencode
from core.models import VortexDB, UserAccount
from protocol_adapters.xray import XrayAdapter

class AccountManager:
    def __init__(self):
        self.db = VortexDB()
        self.xray = XrayAdapter()

    def _get_transport_settings(self) -> dict:
        settings = self.db.data.get("settings", {})
        domain = settings.get("domain", "YOUR_DOMAIN")
        address = settings.get("connect_domain") or domain
        ss_method = settings.get("ss_method") or "aes-256-gcm"
        if ss_method not in XrayAdapter.SUPPORTED_SS_METHODS:
            ss_method = "aes-256-gcm"
        return {
            "domain": domain,
            "address": address,
            "sni": settings.get("sni") or domain,
            "host": settings.get("host") or domain,
            "port": settings.get("port", 443),
            "ntls_port": settings.get("ntls_port", 80),
            "tls_insecure": settings.get("tls_insecure", False),
            "vless_path": settings.get("vless_path", "/vortex-vless"),
            "vmess_path": settings.get("vmess_path", "/vortex-vmess"),
            "trojan_path": settings.get("trojan_path", "/vortex-trojan"),
            "ss_path": settings.get("ss_path", "/vortex-ss"),
            "vless_grpc_service": settings.get("vless_grpc_service", "vortex-grpc"),
            "ss_method": ss_method,
            "ss_plugin_opts": settings.get("ss_plugin_opts")
        }

    def _build_query(self, params: list) -> str:
        return urlencode(params, safe="%")

    def _build_vless_link(self, user_dict: dict, transport: str, tls_enabled: bool) -> str:
        settings = self._get_transport_settings()
        domain = settings["address"]
        params = [
            ("encryption", "none"),
            ("security", "tls" if tls_enabled else "none")
        ]
        if transport == "ws":
            params.append(("type", "ws"))
            params.append(("path", quote(settings["vless_path"], safe="")))
        elif transport == "grpc":
            params.append(("type", "grpc"))
            params.append(("serviceName", settings["vless_grpc_service"]))
        if settings["host"]:
            if transport == "grpc":
                params.append(("authority", settings["host"]))
            else:
                params.append(("host", settings["host"]))
        if tls_enabled and settings["sni"]:
            params.append(("sni", settings["sni"]))
        if tls_enabled and settings["tls_insecure"]:
            params.append(("allowInsecure", "1"))
        query = self._build_query(params)
        port = settings["port"] if tls_enabled else settings["ntls_port"]
        return f"vless://{user_dict['uuid']}@{domain}:{port}?{query}#{user_dict['username']}"

    def _build_vmess_link(self, user_dict: dict, transport: str, tls_enabled: bool) -> str:
        import base64
        settings = self._get_transport_settings()
        domain = settings["address"]
        port = settings["port"] if tls_enabled else settings["ntls_port"]
        vmess_config = {
            "v": "2",
            "ps": user_dict["username"],
            "add": domain,
            "port": str(port),
            "id": user_dict["uuid"],
            "aid": "0",
            "scy": "auto",
            "net": transport,
            "type": "none"
        }
        if transport == "ws":
            vmess_config["path"] = settings["vmess_path"]
        elif transport == "grpc":
            vmess_config["path"] = settings["vless_grpc_service"]
        if settings["host"]:
            vmess_config["host"] = settings["host"]
        if tls_enabled:
            vmess_config["tls"] = "tls"
            if settings["sni"]:
                vmess_config["sni"] = settings["sni"]
            if settings["tls_insecure"]:
                vmess_config["allowInsecure"] = 1
        encoded = base64.b64encode(json.dumps(vmess_config).encode()).decode()
        return f"vmess://{encoded}"

    def _build_trojan_link(self, user_dict: dict, transport: str) -> str:
        settings = self._get_transport_settings()
        domain = settings["address"]
        params = [("security", "tls")]
        if transport == "ws":
            params.extend([
                ("type", "ws"),
                ("path", quote(settings["trojan_path"], safe=""))
            ])
        elif transport == "grpc":
            params.extend([
                ("type", "grpc"),
                ("serviceName", settings["vless_grpc_service"])
            ])
        if settings["host"]:
            params.append(("host", settings["host"]))
        if settings["sni"]:
            params.append(("sni", settings["sni"]))
        if settings["tls_insecure"]:
            params.append(("allowInsecure", "1"))
        query = self._build_query(params)
        return f"trojan://{user_dict['uuid']}@{domain}:{settings['port']}?{query}#{user_dict['username']}"

    def _build_ss_link(self, user_dict: dict, tls_mode: str) -> str:
        import base64
        import urllib.parse
        settings = self._get_transport_settings()
        domain = settings["address"]
        # Prefer broad client compatibility (including NekoBox)
        auth = base64.b64encode(
            f"{settings['ss_method']}:{user_dict['uuid']}".encode()
        ).decode().rstrip("=")
        if settings["ss_plugin_opts"]:
            plugin_opts = settings["ss_plugin_opts"]
        else:
            plugin_parts = ["v2ray-plugin"]
            if tls_mode == "tls":
                plugin_parts.append("tls")
            elif tls_mode == "ntls":
                plugin_parts.append("ntls")
            plugin_parts.extend([
                "mux=0",
                "mode=websocket",
                f"path={settings['ss_path']}"
            ])
            if settings["host"]:
                plugin_parts.append(f"host={settings['host']}")
            plugin_opts = ";".join(plugin_parts)
        # Keep plugin separators visible for clients that are strict in parser behavior
        encoded_opts = urllib.parse.quote(plugin_opts, safe=';=/:,')
        port = settings["port"] if tls_mode == "tls" else settings["ntls_port"]
        return f"ss://{auth}@{domain}:{port}?plugin={encoded_opts}#{user_dict['username']}"

    def generate_vless_links(self, user_dict: dict) -> dict:
        return {
            "WS TLS": self._build_vless_link(user_dict, "ws", True),
            "WS NTLS": self._build_vless_link(user_dict, "ws", False),
            "gRPC TLS": self._build_vless_link(user_dict, "grpc", True)
        }

    def generate_vmess_links(self, user_dict: dict) -> dict:
        return {
            "WS TLS": self._build_vmess_link(user_dict, "ws", True),
            "WS NTLS": self._build_vmess_link(user_dict, "ws", False)
        }

    def generate_trojan_links(self, user_dict: dict) -> dict:
        return {
            "WS TLS": self._build_trojan_link(user_dict, "ws")
        }

    def generate_ss_links(self, user_dict: dict) -> dict:
        return {
            "WS TLS": self._build_ss_link(user_dict, "tls"),
            "WS NTLS": self._build_ss_link(user_dict, "ntls")
        }

    def create_user(
        self,
        username: str,
        protocol: str,
        days: int = 30,
        ip_limit: int = 2,
        quota_gb: int = 0,
        trial_hours: int = 0
    ) -> dict:
        # 1. Check if user already exists
        if self.db.get_user(username):
            raise ValueError(f"User '{username}' already exists.")

        # 2. Calculate expiry
        if trial_hours > 0:
            expires_at = int(time.time()) + (trial_hours * 3600)
        else:
            expires_at = int(time.time()) + (days * 86400)
        
        credentials = {}
        
        # 3. Handle Legacy Protocols
        if protocol == "wireguard":
            from protocol_adapters.wireguard import WireguardAdapter
            wg = WireguardAdapter()
            client_priv, client_pub = wg.generate_keys()
            user_count = len([u for u in self.db.data["users"] if u["protocol"] == "wireguard"])
            client_ip = f"10.0.0.{user_count + 2}/32"
            credentials = {
                "private_key": client_priv,
                "public_key": client_pub,
                "ip": client_ip
            }
            if not os.environ.get("PROOT_TMPDIR"):
                try: wg.add_peer(client_pub, client_ip)
                except: pass

        elif protocol == "openvpn":
            try:
                import subprocess
                subprocess.run(["/usr/local/lib/vortex-x/scripts/openvpn_helper.sh", "add", username], check=False)
            except: pass

        # 4. Create User Object
        new_user = UserAccount(
            username=username,
            protocol=protocol,
            expires_at=expires_at,
            password=credentials.get("password", ""),
            ip_limit=ip_limit,
            quota_gb=quota_gb
        )
        new_user.credentials = credentials 

        # 5. Sync with Xray if needed
        if protocol in ["vless", "vmess", "trojan", "shadowsocks"]:
            self._add_to_xray(new_user)
        
        self.db.add_user(new_user)
        self.xray.save()
        
        # Restart Xray to apply changes
        if protocol in ["vless", "vmess", "trojan", "shadowsocks"]:
            import subprocess
            subprocess.run(["systemctl", "restart", "xray"], check=False)
            
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

    def sync_all_users(self):
        """Syncs all users from DB to Xray configuration and restarts service."""
        print("[INFO] Syncing all users to Xray...")
        for inbound in self.xray.config.get("inbounds", []):
            if "settings" in inbound and "clients" in inbound["settings"]:
                inbound["settings"]["clients"] = []
        
        for user_dict in self.db.data.get("users", []):
            user = UserAccount(
                username=user_dict["username"],
                protocol=user_dict["protocol"],
                uuid_str=user_dict.get("uuid")
            )
            self._add_to_xray(user)
        
        self.xray.save()
        import subprocess
        subprocess.run(["systemctl", "restart", "xray"], check=False)
        print("[SUCCESS] Sync complete.")

    def _add_to_xray(self, user: UserAccount) -> bool:
        self._ensure_inbounds(user.protocol)
        found_inbound = False
        for inbound in self.xray.config.get("inbounds", []):
            if inbound.get("protocol") == user.protocol:
                if user.protocol in ["vless", "vmess"]:
                    client = {"id": user.uuid, "email": user.username, "level": 0}
                    if "clients" not in inbound["settings"]:
                        inbound["settings"]["clients"] = []
                    inbound["settings"]["clients"].append(client)
                    found_inbound = True
                
                elif user.protocol == "trojan":
                    client = {"password": user.uuid, "email": user.username, "level": 0}
                    if "clients" not in inbound["settings"]:
                        inbound["settings"]["clients"] = []
                    inbound["settings"]["clients"].append(client)
                    found_inbound = True
                
                elif user.protocol == "shadowsocks":
                    settings = self._get_transport_settings()
                    client = {"password": user.uuid, "email": user.username}
                    if "clients" not in inbound["settings"]:
                        inbound["settings"]["clients"] = []
                    inbound["settings"]["method"] = settings["ss_method"]
                    inbound["settings"]["clients"].append(client)
                    found_inbound = True
        return found_inbound

    def _ensure_inbounds(self, protocol: str) -> None:
        settings = self._get_transport_settings()

        def _matches_ws(inbound: dict, path: str) -> bool:
            stream = inbound.get("streamSettings", {})
            return (
                stream.get("network") == "ws" and
                stream.get("wsSettings", {}).get("path") == path
            )

        def _matches_grpc(inbound: dict, service_name: str) -> bool:
            stream = inbound.get("streamSettings", {})
            return (
                stream.get("network") == "grpc" and
                stream.get("grpcSettings", {}).get("serviceName") == service_name
            )

        inbounds = self.xray.config.get("inbounds", [])
        if protocol == "vless":
            if not any(
                inbound.get("protocol") == "vless" and
                inbound.get("port") == 10001 and
                _matches_ws(inbound, settings["vless_path"])
                for inbound in inbounds
            ):
                self.xray.generate_vless_ws(10001, settings["vless_path"])
            if not any(
                inbound.get("protocol") == "vless" and
                inbound.get("port") == 10003 and
                _matches_grpc(inbound, settings["vless_grpc_service"])
                for inbound in inbounds
            ):
                self.xray.generate_vless_grpc(10003, service_name=settings["vless_grpc_service"])
        elif protocol == "vmess":
            if not any(
                inbound.get("protocol") == "vmess" and
                inbound.get("port") == 10002 and
                _matches_ws(inbound, settings["vmess_path"])
                for inbound in inbounds
            ):
                self.xray.generate_vmess_ws(10002, settings["vmess_path"])
        elif protocol == "trojan":
            if not any(
                inbound.get("protocol") == "trojan" and
                inbound.get("port") == 10004 and
                _matches_ws(inbound, settings["trojan_path"])
                for inbound in inbounds
            ):
                self.xray.generate_trojan_ws(10004, settings["trojan_path"])
        elif protocol == "shadowsocks":
            if not any(
                inbound.get("protocol") == "shadowsocks" and
                inbound.get("port") == 10005 and
                _matches_ws(inbound, settings["ss_path"])
                for inbound in inbounds
            ):
                self.xray.generate_ss_ws(10005, settings["ss_path"])

    def generate_vless_link(self, user_dict: dict) -> str:
        return self._build_vless_link(user_dict, "ws", True)

    def generate_vless_grpc_link(self, user_dict: dict) -> str:
        return self._build_vless_link(user_dict, "grpc", True)

    def generate_vmess_link(self, user_dict: dict) -> str:
        return self._build_vmess_link(user_dict, "ws", True)

    def generate_trojan_link(self, user_dict: dict) -> str:
        return self._build_trojan_link(user_dict, "ws")

    def generate_ss_link(self, user_dict: dict) -> str:
        return self._build_ss_link(user_dict, "tls")
