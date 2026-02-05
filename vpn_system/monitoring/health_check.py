#!/usr/bin/env python3
import argparse
import json
import os
import pwd
import grp
import subprocess
import sys
from datetime import datetime
from typing import List, Tuple

XRAY_CONFIG_PATH = "/usr/local/etc/xray/config.json"
XRAY_LOG_DIR = "/var/log/xray"
XRAY_ACCESS_LOG = "/var/log/xray/access.log"
XRAY_ERROR_LOG = "/var/log/xray/error.log"

EXPECTED_INBOUNDS = {
    (10001, "vless"): "ws",
    (10002, "vmess"): "ws",
    (10003, "vless"): "grpc",
    (10004, "trojan"): "ws",
    (10005, "shadowsocks"): "ws",
}


def run_cmd(cmd: List[str]) -> Tuple[int, str, str]:
    try:
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True)
        return proc.returncode, proc.stdout.strip(), proc.stderr.strip()
    except FileNotFoundError as exc:
        return 127, "", str(exc)


def check_service_active(service_name: str) -> dict:
    code, out, err = run_cmd(["systemctl", "is-active", service_name])
    is_active = code == 0 and out == "active"
    return {
        "service": service_name,
        "active": is_active,
        "raw": out or err,
    }


def check_xray_log_permissions() -> dict:
    result = {"ok": True, "errors": []}

    try:
        uid = pwd.getpwnam("vortex-x").pw_uid
        gid = grp.getgrnam("vortex-x").gr_gid
    except Exception:
        uid = gid = None

    paths = [XRAY_LOG_DIR, XRAY_ACCESS_LOG, XRAY_ERROR_LOG]
    for path in paths:
        if not os.path.exists(path):
            result["ok"] = False
            result["errors"].append(f"missing:{path}")
            continue

    if os.path.isdir(XRAY_LOG_DIR):
        mode = oct(os.stat(XRAY_LOG_DIR).st_mode & 0o777)
        if mode != "0o750":
            result["ok"] = False
            result["errors"].append(f"mode:{XRAY_LOG_DIR}:{mode}!=0o750")

    for log_file in (XRAY_ACCESS_LOG, XRAY_ERROR_LOG):
        if os.path.isfile(log_file):
            mode = oct(os.stat(log_file).st_mode & 0o777)
            if mode != "0o640":
                result["ok"] = False
                result["errors"].append(f"mode:{log_file}:{mode}!=0o640")

    if uid is not None and gid is not None:
        for path in paths:
            if not os.path.exists(path):
                continue
            st = os.stat(path)
            if st.st_uid != uid or st.st_gid != gid:
                result["ok"] = False
                result["errors"].append(f"owner:{path}:uid={st.st_uid},gid={st.st_gid}!=vortex-x")

    return result


def check_inbound_transports(config_path: str = XRAY_CONFIG_PATH) -> dict:
    result = {"ok": True, "errors": [], "actual": {}}
    if not os.path.exists(config_path):
        result["ok"] = False
        result["errors"].append(f"missing:{config_path}")
        return result

    try:
        with open(config_path, "r", encoding="utf-8") as f:
            config = json.load(f)
    except Exception as exc:
        result["ok"] = False
        result["errors"].append(f"invalid_json:{exc}")
        return result

    for inbound in config.get("inbounds", []):
        key = (inbound.get("port"), inbound.get("protocol"))
        if key in EXPECTED_INBOUNDS:
            net = inbound.get("streamSettings", {}).get("network")
            result["actual"][f"{key[1]}:{key[0]}"] = net

    for key, expected_net in EXPECTED_INBOUNDS.items():
        got = result["actual"].get(f"{key[1]}:{key[0]}")
        if got != expected_net:
            result["ok"] = False
            result["errors"].append(f"{key[1]}:{key[0]} expected={expected_net} got={got}")

    return result


def check_port_binding() -> dict:
    result = {"ok": True, "errors": [], "listening": {}}
    code, out, _ = run_cmd(["ss", "-lnt"])
    if code != 0:
        result["ok"] = False
        result["errors"].append("unable_to_run_ss")
        return result

    ports = {10001, 10002, 10003, 10004, 10005}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) < 4:
            continue
        local = parts[3]
        if ":" not in local:
            continue
        try:
            port = int(local.rsplit(":", 1)[1])
        except ValueError:
            continue
        if port in ports:
            result["listening"][str(port)] = True

    for port in ports:
        if str(port) not in result["listening"]:
            result["ok"] = False
            result["errors"].append(f"port_not_listening:{port}")

    return result


def build_report() -> dict:
    services = {
        "xray": check_service_active("xray"),
        "nginx": check_service_active("nginx"),
    }
    logs = check_xray_log_permissions()
    transports = check_inbound_transports()
    ports = check_port_binding()

    ok = services["xray"]["active"] and services["nginx"]["active"] and logs["ok"] and transports["ok"] and ports["ok"]
    return {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "ok": ok,
        "services": services,
        "log_permissions": logs,
        "inbounds": transports,
        "ports": ports,
    }


def maybe_write_failure_log(report: dict) -> None:
    if report.get("ok"):
        return
    log_dir = "/var/log/vortex-x"
    log_file = os.path.join(log_dir, "health_check.log")
    os.makedirs(log_dir, exist_ok=True)
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(report) + "\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Vortex-x health check")
    parser.add_argument("--json", action="store_true", help="print JSON output")
    parser.add_argument("--quiet", action="store_true", help="suppress normal output (for cron)")
    args = parser.parse_args()

    report = build_report()
    maybe_write_failure_log(report)

    if args.json:
        print(json.dumps(report, indent=2))
    elif not args.quiet or not report["ok"]:
        status = "OK" if report["ok"] else "FAILED"
        print(f"[VORTEX-DOCTOR] {status}")
        print(json.dumps(report, indent=2))

    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
