#!/usr/bin/env python3
import json
import os
import pwd
import grp
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




def _build_ws_inbound(protocol: str, port: int, tag: str, path: str, settings: dict) -> dict:
    return {
        "protocol": protocol,
        "port": port,
        "listen": "127.0.0.1",
        "tag": tag,
        "settings": settings,
        "streamSettings": {
            "network": "ws",
            "wsSettings": {"path": path}
        },
        "sniffing": {"enabled": True, "destOverride": ["http", "tls"]}
    }


def _build_grpc_vless_inbound(port: int, service_name: str) -> dict:
    return {
        "protocol": "vless",
        "port": port,
        "listen": "127.0.0.1",
        "tag": f"vless-grpc-{port}",
        "settings": {"clients": [], "decryption": "none"},
        "streamSettings": {
            "network": "grpc",
            "grpcSettings": {"serviceName": service_name}
        },
        "sniffing": {"enabled": True, "destOverride": ["http", "tls"]}
    }



def _ensure_log_permissions(config: dict) -> None:
    log_cfg = config.get("log", {}) if isinstance(config, dict) else {}
    candidates = [log_cfg.get("access"), log_cfg.get("error")]
    uid = gid = None
    try:
        uid = pwd.getpwnam("vortex-x").pw_uid
        gid = grp.getgrnam("vortex-x").gr_gid
    except Exception:
        return

    for log_path in candidates:
        if not log_path:
            continue
        try:
            log_file = os.path.abspath(log_path)
            log_dir = os.path.dirname(log_file)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)
                os.chown(log_dir, uid, gid)
                os.chmod(log_dir, 0o750)
            if not os.path.exists(log_file):
                open(log_file, "a", encoding="utf-8").close()
            os.chown(log_file, uid, gid)
            os.chmod(log_file, 0o640)
        except Exception:
            continue


def _verify_managed_inbounds(config: dict) -> list:
    expected = {
        (10001, "vless"): "ws",
        (10002, "vmess"): "ws",
        (10003, "vless"): "grpc",
        (10004, "trojan"): "ws",
        (10005, "shadowsocks"): "ws",
    }
    actual = {}
    for inbound in config.get("inbounds", []):
        key = (inbound.get("port"), inbound.get("protocol"))
        network = inbound.get("streamSettings", {}).get("network")
        if key in expected:
            actual[key] = network

    errors = []
    for key, want in expected.items():
        got = actual.get(key)
        if got != want:
            errors.append(f"{key[1]}:{key[0]} expected={want} got={got}")
    return errors

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

    adapter.config["inbounds"].append(_build_ws_inbound(
        "vless", 10001, "vless-ws-10001", vless_path, {"clients": [], "decryption": "none"}
    ))
    adapter.config["inbounds"].append(_build_ws_inbound(
        "vmess", 10002, "vmess-ws-10002", vmess_path, {"clients": []}
    ))
    adapter.config["inbounds"].append(_build_grpc_vless_inbound(10003, vless_grpc_service))
    adapter.config["inbounds"].append(_build_ws_inbound(
        "trojan", 10004, "trojan-ws-10004", trojan_path, {"clients": []}
    ))
    adapter.config["inbounds"].append(_build_ws_inbound(
        "shadowsocks", 10005, "ss-ws-10005", ss_path, {"clients": [], "method": default_ss_method, "network": "tcp,udp"}
    ))
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

    with open(config_path, "r") as handle:
        written_config = json.load(handle)

    _ensure_log_permissions(written_config)

    verification_errors = _verify_managed_inbounds(written_config)
    if verification_errors:
        raise SystemExit(
            "[ERROR] managed inbound verification failed: " + "; ".join(verification_errors)
        )

    print(f"[OK] repaired managed inbounds in {config_path}")


if __name__ == "__main__":
    main()
