import os
import subprocess
from typing import Tuple

class WireguardAdapter:
    def __init__(self, config_path: str = "/etc/wireguard/wg0.conf"):
        self.config_path = config_path
        self.interface = "wg0"

    def generate_keys(self) -> Tuple[str, str]:
        """Generates a private and public key pair."""
        priv_key = subprocess.check_output(["wg", "genkey"]).decode().strip()
        pub_key = subprocess.check_output(["wg", "pubkey"], input=priv_key.encode()).decode().strip()
        return priv_key, pub_key

    def setup_server(self, port: int = 51820):
        """Initializes the WireGuard server configuration."""
        if os.path.exists(self.config_path):
            return # Already setup

        priv_key, pub_key = self.generate_keys()
        # Save server public key for reference
        with open(f"/usr/local/etc/vortex-x/server_wg_pub.key", "w") as f:
            f.write(pub_key)

        config = f"""[Interface]
Address = 10.0.0.1/24
SaveConfig = true
ListenPort = {port}
PrivateKey = {priv_key}
PostUp = iptables -A FORWARD -i {self.interface} -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
PostDown = iptables -D FORWARD -i {self.interface} -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE
"""
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w") as f:
            f.write(config)
        
        subprocess.run(["chmod", "600", self.config_path], check=False)

    def add_peer(self, client_pub_key: str, client_ip: str):
        """Adds a new peer to the running interface."""
        subprocess.run([
            "wg", "set", self.interface, 
            "peer", client_pub_key, 
            "allowed-ips", client_ip
        ], check=True)
        # Config is saved automatically because SaveConfig=true
