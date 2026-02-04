import os
import subprocess

class NginxAdapter:
    def __init__(self, conf_dir: str = "/etc/nginx/conf.d"):
        self.conf_dir = conf_dir

    def cleanup_conflicts(self, domain: str = ""):
        """Removes default nginx configs and potentially conflicting domain configs."""
        defaults = [
            "/etc/nginx/conf.d/default.conf",
            "/etc/nginx/sites-enabled/default"
        ]
        for path in defaults:
            if os.path.exists(path):
                try: os.remove(path)
                except: pass
        
        # If a specific domain is provided, ensure no other file in conf.d has it
        if domain:
            try:
                conf_files = [f for f in os.listdir(self.conf_dir) if f.endswith(".conf")]
                for f in conf_files:
                    # If the file is not exactly {domain}.conf but contains the domain, it's a conflict
                    if f != f"{domain}.conf":
                        f_path = os.path.join(self.conf_dir, f)
                        with open(f_path, 'r') as content:
                            if domain in content.read():
                                os.remove(f_path)
            except:
                pass

    def generate_vhost(
        self,
        domain: str,
        vless_port: int,
        vmess_port: int,
        trojan_port: int,
        ss_port: int = 0,
        transport: str = "ws",
        enable_grpc: bool = False
    ):
        self.cleanup_conflicts(domain)

        def build_location(path: str, port: int) -> str:
            if transport == "ws":
                return f"""
    location {path} {{
        if ($http_upgrade != "websocket") {{ return 404; }}
        proxy_redirect off;
        proxy_pass http://127.0.0.1:{port};
        proxy_http_version 1.1;
        proxy_read_timeout 1h;
        proxy_send_timeout 1h;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }}"""
            return f"""
    location {path} {{
        proxy_redirect off;
        proxy_pass http://127.0.0.1:{port};
        proxy_http_version 1.1;
        proxy_read_timeout 1h;
        proxy_send_timeout 1h;
        proxy_set_header Host $host;
    }}"""

        # Location for Shadowsocks if port provided
        ss_location = ""
        if ss_port > 0:
            ss_location = build_location("/vortex-ss", ss_port)

        grpc_location = ""
        if enable_grpc:
            grpc_location = """
    # VLESS gRPC (Advanced Transport)
    location /vortex-grpc {
        if ($request_method != "POST") { return 404; }
        client_max_body_size 0;
        grpc_read_timeout 1h;
        grpc_send_timeout 1h;
        grpc_set_header Host $host;
        grpc_pass grpc://127.0.0.1:10003;
    }
"""

        vhost_content = f"""
server {{
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name {domain} _;

    # NTLS transport (no TLS termination)
    {build_location("/vortex-vless", vless_port)}
    {build_location("/vortex-vmess", vmess_port)}
    {build_location("/vortex-trojan", trojan_port)}
    {ss_location}

    location / {{
        return 301 https://$host$request_uri;
    }}
}}

server {{
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name {domain};

    ssl_certificate /etc/letsencrypt/live/{domain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{domain}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # Transport inbounds
    {build_location("/vortex-vless", vless_port)}
    {build_location("/vortex-vmess", vmess_port)}
    {build_location("/vortex-trojan", trojan_port)}
    {ss_location}

    {grpc_location}

    # Fallback / Fake Website
    location / {{
        root /var/www/html;
        index index.html;
    }}
}}
"""
        conf_path = os.path.join(self.conf_dir, f"{domain}.conf")
        with open(conf_path, "w") as f:
            f.write(vhost_content)
        
        # Validate and Reload/Restart Nginx
        if subprocess.run(["nginx", "-t"], check=False).returncode == 0:
            if subprocess.run(["systemctl", "reload", "nginx"], check=False).returncode != 0:
                subprocess.run(["systemctl", "restart", "nginx"], check=False)
        else:
            print("[ERROR] Nginx configuration test failed.")
