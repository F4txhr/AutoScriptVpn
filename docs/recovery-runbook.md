# Vortex-x Recovery Runbook (Quick)

## 1) Sync runtime code from repository
```bash
bash vpn_system/installer/install.sh --sync-runtime
```

## 2) Restart Xray
```bash
systemctl restart xray
```

## 3) Validate Xray status
```bash
systemctl status xray --no-pager
```

## 4) Run one-shot doctor
```bash
vortex-x doctor
```

## 5) Optional JSON report
```bash
vortex-x doctor --json
```

## What doctor checks
- `systemctl is-active xray nginx`
- `/var/log/xray` permissions and ownership
- inbound transport mapping for ports `10001..10005`
- local listener ports `10001..10005`

## Scheduled routine checks
Installer cron now runs every 5 minutes:
```cron
*/5 * * * * root python3 /usr/local/lib/vortex-x/monitoring/health_check.py --quiet
```

Failed checks are written to:
- `/var/log/vortex-x/health_check.log`
