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
    settings = dict(db.data.get("settings", {}))
    default_ss_method = normalize_shadowsocks_method(settings.get("ss_method"))
    transport = settings.get("transport", "xhttp")
    enable_grpc = settings.get("enable_grpc", False)
    settings_changed = False
    if transport in {"ws", "grpc"}:
        transport = "xhttp"
        settings["transport"] = transport
        settings_changed = True
    if enable_grpc:
        enable_grpc = False
        settings["enable_grpc"] = enable_grpc
        settings_changed = True
    if settings_changed:
        db.data["settings"] = settings
        db.save()
    vless_path = settings.get("vless_path", "/vortex-vless")
    vmess_path = settings.get("vmess_path", "/vortex-vmess")
    trojan_path = settings.get("trojan_path", "/vortex-trojan")
    ss_path = settings.get("ss_path", "/vortex-ss")
    vless_grpc_service = settings.get("vless_grpc_service", "vortex-grpc")
    adapter = XrayAdapter(config_path=config_path)
    adapter.config = config
    inbounds = adapter.config.setdefault("inbounds", [])
    def inbound_matches(protocol: str, port: int, network: str) -> bool:
        for inbound in inbounds:
            if inbound.get("protocol") != protocol or inbound.get("port") != port:
                continue
            stream = inbound.get("streamSettings", {})
            if stream.get("network") == network:
                return True
        return False

    def replace_inbound(protocol: str, port: int, build_fn) -> None:
        nonlocal inbounds
        adapter.config["inbounds"] = [
            inbound for inbound in adapter.config.get("inbounds", [])
            if not (inbound.get("protocol") == protocol and inbound.get("port") == port)
        ]
        inbounds = adapter.config["inbounds"]
        build_fn()

    if not inbound_matches("vless", 10001, transport):
        def build_vless():
            adapter.generate_vless(10001, transport=transport, path=vless_path)
        replace_inbound("vless", 10001, build_vless)
        changed = True
    if enable_grpc:
        if not inbound_matches("vless", 10003, "grpc"):
            def build_vless_grpc():
                adapter.generate_vless(10003, transport="grpc", service_name=vless_grpc_service)
            replace_inbound("vless", 10003, build_vless_grpc)
            changed = True
    if not inbound_matches("vmess", 10002, transport):
        def build_vmess():
            adapter.generate_vmess(10002, transport=transport, path=vmess_path)
        replace_inbound("vmess", 10002, build_vmess)
        changed = True
    if not inbound_matches("trojan", 10004, transport):
        def build_trojan():
            adapter.generate_trojan(10004, transport=transport, path=trojan_path)
        replace_inbound("trojan", 10004, build_trojan)
        changed = True
    if not inbound_matches("shadowsocks", 10005, transport):
        def build_ss():
            adapter.generate_ss(10005, transport=transport, path=ss_path)
        replace_inbound("shadowsocks", 10005, build_ss)
        changed = True

    if not enable_grpc:
        adapter.config["inbounds"] = [
            inbound for inbound in adapter.config.get("inbounds", [])
            if not (inbound.get("protocol") == "vless" and inbound.get("port") == 10003)
        ]
        inbounds = adapter.config["inbounds"]

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
