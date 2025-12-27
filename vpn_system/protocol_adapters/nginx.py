import os
import subprocess

class NginxAdapter:
    def __init__(self, conf_dir: str = "/etc/nginx/conf.d"):
        self.conf_dir = conf_dir

    def generate_vhost(self, domain: str, vless_port: int, vmess_port: int, trojan_port: int):
        vhost_content = f"""
server {{
    listen 80;
    listen [::]:80;
    server_name {domain};
    return 301 https://$host$request_uri;
}}

server {{
    listen 443 ssl http2;
    listen [::]:443 ssl http2;
    server_name {domain};

    ssl_certificate /etc/letsencrypt/live/{domain}/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/{domain}/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;

    # VLESS WebSocket
    location /vortex-vless {{
        if ($http_upgrade != "websocket") {{
            return 404;
        }}
        proxy_redirect off;
        proxy_pass http://127.0.0.1:{vless_port};
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }}

    # VMESS WebSocket
    location /vortex-vmess {{
        if ($http_upgrade != "websocket") {{
            return 404;
        }}
        proxy_redirect off;
        proxy_pass http://127.0.0.1:{vmess_port};
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
    }}

    # VLESS gRPC (Advanced Transport)
    location /vortex-grpc {{
        if ($request_method != "POST") {{
            return 404;
        }}
        client_max_body_size 0;
        client_body_timeout 1h;
        grpc_read_timeout 1h;
        grpc_send_timeout 1h;
        grpc_pass grpc://127.0.0.1:{trojan_port}; # Reuse/Specific port for gRPC
    }}

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
        
        # Reload nginx if possible
        subprocess.run(["nginx", "-t"], check=False)
        subprocess.run(["systemctl", "reload", "nginx"], check=False)
