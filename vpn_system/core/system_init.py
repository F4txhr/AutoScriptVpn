import json
import os
import subprocess
import sys

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.models import Database, Host, Inbound
from protocol_adapters.vless import VlessAdapter
from protocol_adapters.vmess import VmessAdapter
from protocol_adapters.trojan import TrojanAdapter
from protocol_adapters.shadowsocks import ShadowsocksAdapter

XRAY_CONFIG_PATH = "/usr/local/etc/xray/config.json"

def init_system(domain: str, ip: str, hostname: str):
    db = Database()
    
    # 1. Create Host
    host = Host(
        hostname=hostname,
        domain=domain,
        ip=ip,
        location="Unknown",
        status="active",
        supported_protocols=["vless", "vmess", "trojan", "shadowsocks", "wireguard", "openvpn"]
    )
    db.add_host(host)
    
    # 2. Setup Global Inbounds for Xray
    # VLESS: 443 (WS TLS), 8443 (gRPC TLS)
    # VMess: 8444 (WS TLS), 8445 (gRPC TLS)
    # Trojan: 2087 (TCP TLS)
    # Shadowsocks: 2443 (TCP/UDP)

    inbounds_to_create = [
        {"protocol": "vless", "transport": "ws", "port": 10001, "tls": True},
        {"protocol": "vless", "transport": "grpc", "port": 8443, "tls": True},
        {"protocol": "vmess", "transport": "ws", "port": 8444, "tls": True},
        {"protocol": "vmess", "transport": "grpc", "port": 8445, "tls": True},
        {"protocol": "trojan", "transport": "tcp", "port": 2087, "tls": True},
        {"protocol": "shadowsocks", "transport": "tcp", "port": 2443, "tls": False},
    ]

    adapters = {
        "vless": VlessAdapter(XRAY_CONFIG_PATH),
        "vmess": VmessAdapter(XRAY_CONFIG_PATH),
        "trojan": TrojanAdapter(XRAY_CONFIG_PATH),
        "shadowsocks": ShadowsocksAdapter(XRAY_CONFIG_PATH)
    }

    # Reset Xray config inbounds
    for adapter in adapters.values():
        adapter.config["inbounds"] = []

    for ib_spec in inbounds_to_create:
        proto = ib_spec['protocol']
        adapter = adapters[proto]
        
        if proto == "shadowsocks":
             inbound_config = adapter.generate_inbound(ib_spec['port'])
        else:
             inbound_config = adapter.generate_inbound(ib_spec['port'], ib_spec['transport'], ib_spec['tls'], domain)
        
        # Merge into Xray config (they all share the same file)
        adapters["vless"].config["inbounds"].append(inbound_config)
        
        # Save to DB
        inbound = Inbound(
            protocol=proto,
            transport=ib_spec.get('transport', 'tcp'),
            port=ib_spec['port'],
            listen_address="0.0.0.0",
            status="active",
            bound_host=host.host_id,
            tag=inbound_config['tag']
        )
        db.add_inbound(inbound)

    # Save Xray config
    adapters["vless"]._save_config()
    
    print(f"System initialized with host {domain} and default inbounds.")

if __name__ == "__main__":
    import socket
    hostname = socket.gethostname()
    # Try to get public IP
    try:
        import urllib.request
        ip = urllib.request.urlopen('https://ident.me').read().decode('utf8')
    except:
        ip = "127.0.0.1"
    
    domain = sys.argv[1] if len(sys.argv) > 1 else ip
    init_system(domain, ip, hostname)
