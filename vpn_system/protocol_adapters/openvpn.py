import subprocess
import os
import shutil

class OpenVpnAdapter:
    """
    Adapter for managing OpenVPN via EasyRSA.
    Uses a simple setup: Single Server Config, Client Cert Generation.
    """
    EASYRSA_PATH = "/etc/openvpn/easy-rsa"
    OPENVPN_DIR = "/etc/openvpn"
    
    def __init__(self):
        self.verify_installation()

    def verify_installation(self):
        if not os.path.exists(self.EASYRSA_PATH):
            # This would trigger on first run if not initialized
            pass

    def initialize_pki(self):
        """Initializes PKI if not exists."""
        if os.path.exists(os.path.join(self.EASYRSA_PATH, "pki")):
            return

        # Setup EasyRSA directory
        shutil.rmtree(self.EASYRSA_PATH, ignore_errors=True)
        subprocess.run(["make-cadir", self.EASYRSA_PATH], check=True)
        
        # Init PKI
        subprocess.run(["./easyrsa", "init-pki"], cwd=self.EASYRSA_PATH, check=True)
        
        # Build CA (Batch mode, nopass)
        env = os.environ.copy()
        env["EASYRSA_BATCH"] = "1"
        env["EASYRSA_REQ_CN"] = "VortexVPN_CA"
        subprocess.run(["./easyrsa", "build-ca", "nopass"], cwd=self.EASYRSA_PATH, env=env, check=True)
        
        # Build Server Cert
        subprocess.run(["./easyrsa", "build-server-full", "server", "nopass"], cwd=self.EASYRSA_PATH, env=env, check=True)
        
        # Gen DH
        subprocess.run(["./easyrsa", "gen-dh"], cwd=self.EASYRSA_PATH, check=True)
        
        # Copy to OpenVPN dir
        pki = os.path.join(self.EASYRSA_PATH, "pki")
        shutil.copy(f"{pki}/ca.crt", self.OPENVPN_DIR)
        shutil.copy(f"{pki}/issued/server.crt", self.OPENVPN_DIR)
        shutil.copy(f"{pki}/private/server.key", self.OPENVPN_DIR)
        shutil.copy(f"{pki}/dh.pem", self.OPENVPN_DIR)

        # Write Server Config
        self.write_server_config()

    def write_server_config(self):
        conf = """
port 1194
proto udp
dev tun
ca ca.crt
cert server.crt
key server.key
dh dh.pem
server 10.8.0.0 255.255.255.0
push "redirect-gateway def1 bypass-dhcp"
push "dhcp-option DNS 8.8.8.8"
keepalive 10 120
cipher AES-256-CBC
user nobody
group nogroup
persist-key
persist-tun
status openvpn-status.log
verb 3
"""
        with open(os.path.join(self.OPENVPN_DIR, "server.conf"), "w") as f:
            f.write(conf)

    def add_user(self, username: str) -> str:
        """Generates a client certificate and returns the OVPN file content."""
        if not os.path.exists(os.path.join(self.EASYRSA_PATH, "pki")):
            self.initialize_pki()

        env = os.environ.copy()
        env["EASYRSA_BATCH"] = "1"
        subprocess.run(["./easyrsa", "build-client-full", username, "nopass"], cwd=self.EASYRSA_PATH, env=env, check=True)

        return self.generate_ovpn(username)

    def generate_ovpn(self, username: str) -> str:
        # Read keys
        pki = os.path.join(self.EASYRSA_PATH, "pki")
        with open(f"{self.OPENVPN_DIR}/ca.crt") as f: ca = f.read()
        with open(f"{pki}/issued/{username}.crt") as f: cert = f.read()
        with open(f"{pki}/private/{username}.key") as f: key = f.read()
        
        # Note: In production, you need the public IP here
        # We will use a placeholder that the caller can replace
        ovpn = f"""
client
dev tun
proto udp
remote REPLACE_MY_IP 1194
resolv-retry infinite
nobind
persist-key
persist-tun
cipher AES-256-CBC
verb 3
<ca>
{ca}
</ca>
<cert>
{cert}
</cert>
<key>
{key}
</key>
"""
        return ovpn
