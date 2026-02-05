#!/usr/bin/env python3
import json
import os
import re
import sys

LIB_PATH = "/usr/local/lib/vortex-x"
if not os.path.exists(LIB_PATH):
    LIB_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(LIB_PATH)

from protocol_adapters.xray import XrayAdapter
from core.models import VortexDB




def normalize_shadowsocks_method(method: str) -> str:
    if not method:
        return "aes-256-gcm"
    method = method.strip().lower()
    if method not in XrayAdapter.SUPPORTED_SS_METHODS:
        return "aes-256-gcm"
    return method


def main() -> None:
    config_path = "/usr/local/etc/xray/config.json"
    if not os.path.exists(config_path):
        adapter = XrayAdapter(config_path=config_path)
        adapter.save()
        return
    with open(config_path, "r") as handle:
        raw_config = handle.read()

    try:
        config = json.loads(raw_config)
    except json.JSONDecodeError:
        def normalize_match(match: re.Match) -> str:
            prefix = match.group(1)
            method = match.group(2)
            normalized = normalize_shadowsocks_method(method)
            return f'{prefix}"{normalized}"'

        normalized = re.sub(
            r'("method"\s*:\s*)"([^"]*)"',
            normalize_match,
            raw_config,
            flags=re.IGNORECASE,
        )
        if normalized != raw_config:
            with open(config_path, "w") as handle:
                handle.write(normalized)
            return
        adapter = XrayAdapter(config_path=config_path)
        adapter.save()
        return

    changed = False
    db = VortexDB()
    settings = db.data.get("settings", {})
    default_ss_method = normalize_shadowsocks_method(settings.get("ss_method"))
    vless_path = settings.get("vless_path", "/vortex-vless")
    vmess_path = settings.get("vmess_path", "/vortex-vmess")
    trojan_path = settings.get("trojan_path", "/vortex-trojan")
    ss_path = settings.get("ss_path", "/vortex-ss")
    vless_grpc_service = settings.get("vless_grpc_service", "vortex-grpc")
    adapter = XrayAdapter(config_path=config_path)
    adapter.config = config

    # Force deterministic rebuild for all managed inbounds.
    # This guarantees stale transports (e.g. xhttp on managed ports)
    # are removed and replaced with expected WS/gRPC definitions.
    managed_ports = {10001, 10002, 10003, 10004, 10005}
    filtered_inbounds = []
    for inbound in adapter.config.setdefault("inbounds", []):
        if inbound.get("port") in managed_ports:
            changed = True
            continue
        filtered_inbounds.append(inbound)
    adapter.config["inbounds"] = filtered_inbounds

    adapter.generate_vless_ws(10001, vless_path)
    adapter.generate_vmess_ws(10002, vmess_path)
    adapter.generate_vless_grpc(10003, service_name=vless_grpc_service)
    adapter.generate_trojan_ws(10004, trojan_path)
    adapter.generate_ss_ws(10005, ss_path)
    changed = True

    for inbound in adapter.config.get("inbounds", []):
        if "settings" in inbound and "clients" in inbound["settings"]:
            inbound["settings"]["clients"] = []

    for inbound in adapter.config.get("inbounds", []):
        if inbound.get("protocol") != "shadowsocks":
            continue
        settings = inbound.setdefault("settings", {})
        normalized_method = normalize_shadowsocks_method(settings.get("method"))
        if settings.get("method") != normalized_method:
            settings["method"] = normalized_method
            changed = True
        for client in settings.get("clients", []):
            normalized_client_method = normalize_shadowsocks_method(client.get("method"))
            if client.get("method") != normalized_client_method:
                client["method"] = normalized_client_method
                changed = True

    for user in db.data.get("users", []):
        protocol = user.get("protocol")
        if protocol not in {"vless", "vmess", "trojan", "shadowsocks"}:
            continue
        for inbound in adapter.config.get("inbounds", []):
            if inbound.get("protocol") != protocol:
                continue
            inbound_settings = inbound.setdefault("settings", {})
            clients = inbound_settings.setdefault("clients", [])
            if protocol in {"vless", "vmess"}:
                client = {"id": user.get("uuid"), "email": user.get("username"), "level": 0}
            elif protocol == "trojan":
                client = {"password": user.get("uuid"), "email": user.get("username"), "level": 0}
            else:
                client = {
                    "password": user.get("uuid"),
                    "email": user.get("username"),
                    "method": default_ss_method,
                }
                inbound_settings["method"] = default_ss_method
            clients.append(client)
            changed = True

    if changed:
        with open(config_path, "w") as handle:
            json.dump(adapter.config, handle, indent=4)


if __name__ == "__main__":
    main()
