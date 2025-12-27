import subprocess
import os
from typing import Dict, Tuple

class WireguardAdapter:
    """
    Adapter for managing WireGuard configurations.
    """

    def __init__(self, config_path: str = "/etc/wireguard/wg0.conf"):
        self.config_path = config_path

    def _run_command(self, command: str) -> str:
        """Runs a shell command and returns its output."""
        try:
            result = subprocess.run(command, shell=True, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
            return result.stdout.strip()
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Command '{command}' failed: {e.stderr.strip()}")

    def generate_keys(self) -> Tuple[str, str]:
        """Generates a new WireGuard private and public key pair."""
        private_key = self._run_command("wg genkey")
        public_key = self._run_command(f"echo '{private_key}' | wg pubkey")
        return private_key, public_key

    def get_server_config(self, private_key: str, address: str, port: int) -> str:
        """
        Generates the [Interface] block for the server configuration.
        """
        config = f"[Interface]\n"
        config += f"Address = {address}\n"
        config += f"ListenPort = {port}\n"
        config += f"PrivateKey = {private_key}\n"
        config += "PostUp = iptables -A FORWARD -i %i -j ACCEPT; iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE\n"
        config += "PostDown = iptables -D FORWARD -i %i -j ACCEPT; iptables -t nat -D POSTROUTING -o eth0 -j MASQUERADE\n"
        return config

    def get_peer_config(self, public_key: str, allowed_ips: str) -> str:
        """
        Generates a [Peer] block for the server configuration.
        """
        config = f"\n[Peer]\n"
        config += f"PublicKey = {public_key}\n"
        config += f"AllowedIPs = {allowed_ips}\n"
        return config

    def add_peer_to_config(self, peer_config: str):
        """Appends a peer configuration to the main WireGuard config file safely."""
        try:
            os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
            with open(self.config_path, "a") as f:
                f.write(peer_config)
        except (IOError, OSError) as e:
            raise RuntimeError(f"Failed to append peer to WireGuard config {self.config_path}: {e}")

    def remove_peer(self, public_key: str):
        """
        Removes a peer block from the WireGuard config file based on PublicKey.
        Note: This is a basic text-based implementation.
        """
        if not os.path.exists(self.config_path):
            return

        try:
            with open(self.config_path, "r") as f:
                lines = f.readlines()

            new_lines = []
            skip = False
            for line in lines:
                if line.strip() == "[Peer]":
                    skip = False # Start of a new peer, provisional add (check key later)
                    # We need to peek ahead or buffer. 
                    # Simpler approach: Read file, split by [Peer], filter.
                    pass 
            
            # Re-reading with a block-based approach
            content = "".join(lines)
            blocks = content.split("[Peer]")
            
            # header is blocks[0]
            final_blocks = [blocks[0]]
            
            for block in blocks[1:]:
                if f"PublicKey = {public_key}" not in block:
                    final_blocks.append(block)
            
            new_content = "[Peer]".join(final_blocks)
            
            # Atomic write
            import tempfile
            dir_name = os.path.dirname(self.config_path)
            with tempfile.NamedTemporaryFile('w', dir=dir_name, delete=False) as tf:
                tf.write(new_content)
                temp_name = tf.name
            os.replace(temp_name, self.config_path)

        except (IOError, OSError) as e:
            raise RuntimeError(f"Failed to remove peer from WireGuard config: {e}")

    def generate_client_config(self, private_key: str, client_address: str, server_public_key: str, server_endpoint: str) -> str:
        """
        Generates a complete configuration for a WireGuard client.
        """
        config = "[Interface]\n"
        config += f"PrivateKey = {private_key}\n"
        config += f"Address = {client_address}\n"
        config += "DNS = 1.1.1.1\n\n"

        config += "[Peer]\n"
        config += f"PublicKey = {server_public_key}\n"
        config += f"Endpoint = {server_endpoint}\n"
        config += "AllowedIPs = 0.0.0.0/0\n"
        config += "PersistentKeepalive = 25\n"

        return config

if __name__ == '__main__':
    # Example Usage (for testing)
    adapter = WireguardAdapter(config_path="./wg0.conf")

    # 1. Server Setup
    server_private_key, server_public_key = adapter.generate_keys()
    server_config = adapter.get_server_config(server_private_key, "10.0.0.1/24", 51820)

    # Create the initial server config file
    with open(adapter.config_path, "w") as f:
        f.write(server_config)

    print("--- Server Config (wg0.conf) ---")
    print(server_config)

    # 2. Add a Peer (Client)
    client_private_key, client_public_key = adapter.generate_keys()
    peer_config = adapter.get_peer_config(client_public_key, "10.0.0.2/32")
    adapter.add_peer_to_config(peer_config)

    print("\\n--- Added to Server Config ---")
    print(peer_config)

    # 3. Generate Client Config File
    client_config = adapter.generate_client_config(
        private_key=client_private_key,
        client_address="10.0.0.2/24",
        server_public_key=server_public_key,
        server_endpoint="your.server.ip:51820" # Replace with actual server IP
    )

    client_config_path = "./client1.conf"
    with open(client_config_path, "w") as f:
        f.write(client_config)

    print(f"\\n--- Client Config (saved to {client_config_path}) ---")
    print(client_config)
