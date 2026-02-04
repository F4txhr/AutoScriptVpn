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

    # Paths from settings or defaults
    vless_path = settings.get("vless_path", "/vortex-vless")
    vmess_path = settings.get("vmess_path", "/vortex-vmess")
    trojan_path = settings.get("trojan_path", "/vortex-trojan")
    ss_path = settings.get("ss_path", "/vortex-ss")
    upgrade_path = settings.get("upgrade_path")
    http_path = settings.get("http_path")

    # gRPC services from settings or defaults
    vless_grpc = settings.get("vless_grpc_service", "vortex-vless-grpc")
    vmess_grpc = settings.get("vmess_grpc_service", "vortex-vmess-grpc")
    trojan_grpc = settings.get("trojan_grpc_service", "vortex-trojan-grpc")

    adapter = XrayAdapter(config_path=config_path)
    adapter.config = config
    inbounds = adapter.config.setdefault("inbounds", [])

    # VLESS Inbounds
    if not any(inbound.get("protocol") == "vless" and inbound.get("port") == 10001 for inbound in inbounds):
        adapter.generate_vless_ws(10001, vless_path)
        changed = True
    if not any(inbound.get("protocol") == "vless" and inbound.get("port") == 10003 for inbound in inbounds):
        adapter.generate_vless_grpc(10003, service_name=vless_grpc)
        changed = True
    if not any(inbound.get("protocol") == "vless" and inbound.get("port") == 10006 for inbound in inbounds):
        path = upgrade_path or "/vortex-vless-upgrade"
        adapter.generate_vless_httpupgrade(10006, path=path)
        changed = True
    if not any(inbound.get("protocol") == "vless" and inbound.get("port") == 10007 for inbound in inbounds):
        path = http_path or "/vortex-vless-http"
        adapter.generate_vless_http(10007, path=path)
        changed = True

    # VMESS Inbounds
    if not any(inbound.get("protocol") == "vmess" and inbound.get("port") == 10002 for inbound in inbounds):
        adapter.generate_vmess_ws(10002, vmess_path)
        changed = True
    if not any(inbound.get("protocol") == "vmess" and inbound.get("port") == 10008 for inbound in inbounds):
        adapter.generate_vmess_grpc(10008, service_name=vmess_grpc)
        changed = True
    if not any(inbound.get("protocol") == "vmess" and inbound.get("port") == 10009 for inbound in inbounds):
        path = upgrade_path or "/vortex-vmess-upgrade"
        adapter.generate_vmess_httpupgrade(10009, path=path)
        changed = True

    # Trojan Inbounds
    if not any(inbound.get("protocol") == "trojan" and inbound.get("port") == 10004 for inbound in inbounds):
        adapter.generate_trojan_ws(10004, trojan_path)
        changed = True
    if not any(inbound.get("protocol") == "trojan" and inbound.get("port") == 10010 for inbound in inbounds):
        adapter.generate_trojan_grpc(10010, service_name=trojan_grpc)
        changed = True
    if not any(inbound.get("protocol") == "trojan" and inbound.get("port") == 10011 for inbound in inbounds):
        path = upgrade_path or "/vortex-trojan-upgrade"
        adapter.generate_trojan_httpupgrade(10011, path=path)
        changed = True

    # SS Inbound
    if not any(inbound.get("protocol") == "shadowsocks" and inbound.get("port") == 10005 for inbound in inbounds):
        adapter.generate_ss_ws(10005, ss_path)
        changed = True

    for inbound in adapter.config.get("inbounds", []):
        if "settings" in inbound and "clients" in inbound["settings"]:
            inbound["settings"]["clients"] = []

    for inbound in adapter.config.get("inbounds", []):
        if inbound.get("protocol") != "shadowsocks":
            continue
        settings_obj = inbound.setdefault("settings", {})
        normalized_method = normalize_shadowsocks_method(settings_obj.get("method"))
        if settings_obj.get("method") != normalized_method:
            settings_obj["method"] = normalized_method
            changed = True
        for client in settings_obj.get("clients", []):
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
