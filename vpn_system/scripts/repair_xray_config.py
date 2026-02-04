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
    for inbound in config.get("inbounds", []):
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

    if changed:
        with open(config_path, "w") as handle:
            json.dump(config, handle, indent=4)


if __name__ == "__main__":
    main()
