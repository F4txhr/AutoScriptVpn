import os
import subprocess

class OpenVPNAdapter:
    def __init__(self, config_dir: str = "/etc/openvpn/server"):
        self.config_dir = config_dir

    def generate_client_config(self, username: str, domain: str):
        """Generates a standalone .ovpn file for the client."""
        # This is a simplified template, assuming PKI is already setup
        ca_cert = self._get_file_content("/etc/openvpn/server/ca.crt")
        client_cert = self._get_file_content(f"/etc/openvpn/server/easy-rsa/pki/issued/{username}.crt")
        client_key = self._get_file_content(f"/etc/openvpn/server/easy-rsa/pki/private/{username}.key")
        tls_auth = self._get_file_content("/etc/openvpn/server/ta.key")

        ovpn = f"""client
dev tun
proto tcp
remote {domain} 1194
resolv-retry infinite
nobind
persist-key
persist-tun
remote-cert-tls server
auth SHA256
cipher AES-256-GCM
data-ciphers AES-256-GCM:AES-256-CBC
data-ciphers-fallback AES-256-CBC
verb 3
<ca>
{ca_cert}
</ca>
<cert>
{client_cert}
</cert>
<key>
{client_key}
</key>
<tls-auth>
{tls_auth}
</tls-auth>
key-direction 1
"""
        return ovpn

    def _get_file_content(self, path):
        if os.path.exists(path):
            with open(path, 'r') as f:
                return f.read()
        return f"MISSING_{path}"
