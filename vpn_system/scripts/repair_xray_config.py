#!/usr/bin/env python3
import os

from protocol_adapters.xray import XrayAdapter


def main() -> None:
    config_path = "/usr/local/etc/xray/config.json"
    if not os.path.exists(config_path):
        return
    adapter = XrayAdapter(config_path=config_path)
    adapter.save()


if __name__ == "__main__":
    main()
