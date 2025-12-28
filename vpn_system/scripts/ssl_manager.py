import os
import subprocess
import logging

class SSLManager:
    def __init__(self, domain: str):
        self.domain = domain
        self.cert_path = f"/etc/letsencrypt/live/{domain}/fullchain.pem"
        self.key_path = f"/etc/letsencrypt/live/{domain}/privkey.pem"

    def issue_cert(self):
        print(f"[INFO] Issuing SSL Certificate for {self.domain}...")
        # Ensure Nginx is stopped to free port 80 for standalone certbot
        subprocess.run(["systemctl", "stop", "nginx"], check=False)
        
        cmd = [
            "certbot", "certonly", "--standalone",
            "--preferred-challenges", "http",
            "--agree-tos", "--email", f"admin@{self.domain}",
            "-d", self.domain, "--non-interactive"
        ]
        
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        
        if result.returncode == 0:
            print("[SUCCESS] SSL Certificate issued successfully.")
            self.apply_permissions()
            subprocess.run(["systemctl", "start", "nginx"], check=False)
            return True
        else:
            print(f"[ERROR] SSL Issuance failed: {result.stderr}")
            subprocess.run(["systemctl", "start", "nginx"], check=False)
            return False

    def apply_permissions(self):
        """
        Hardens permissions so non-root service user 'vortex-x' can read certs
        without giving access to the whole /etc/letsencrypt/archive.
        """
        print("[INFO] Hardening SSL permissions...")
        # 1. Allow traversal to the directory
        subprocess.run(["chmod", "755", "/etc/letsencrypt/live"], check=False)
        subprocess.run(["chmod", "755", "/etc/letsencrypt/archive"], check=False)
        
        # 2. Grant read access to the service user for specific domain certs
        if os.path.exists(self.cert_path):
            subprocess.run(["chown", "-R", "vortex-x:vortex-x", f"/etc/letsencrypt/live/{self.domain}"], check=False)
            subprocess.run(["chown", "-R", "vortex-x:vortex-x", f"/etc/letsencrypt/archive/{self.domain}"], check=False)
            subprocess.run(["chmod", "640", self.key_path], check=False)
            subprocess.run(["chmod", "644", self.cert_path], check=False)

    def check_expiry(self):
        if not os.path.exists(self.cert_path):
            return "Missing"
        
        # Get days left using openssl
        cmd = f"openssl x509 -enddate -noout -in {self.cert_path}"
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        if result.returncode == 0:
            # Simple parsing of date format 'notAfter=Mar 27 14:49:19 2026 GMT'
            return result.stdout.strip().split('=')[1]
        return "Unknown"
