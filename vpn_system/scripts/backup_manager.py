import os
import tarfile
import time
import shutil
import subprocess
from datetime import datetime

class BackupManager:
    def __init__(self, backup_dir: str = "/var/backups/vortex-x"):
        self.backup_dir = backup_dir
        self.source_dirs = [
            "/usr/local/etc/vortex-x",
            "/usr/local/etc/xray",
            "/etc/nginx/conf.d",
            "/etc/letsencrypt/live",
            "/etc/wireguard",
            "/etc/openvpn/server"
        ]
        os.makedirs(self.backup_dir, exist_ok=True)

    def create_backup(self) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"vortex_backup_{timestamp}.tar.gz"
        backup_path = os.path.join(self.backup_dir, filename)

        print(f"[INFO] Starting backup to {backup_path}...")
        
        with tarfile.open(backup_path, "w:gz") as tar:
            for src in self.source_dirs:
                if os.path.exists(src):
                    print(f"  - Archiving {src}")
                    tar.add(src, arcname=os.path.relpath(src, "/"))
        
        # Set restrictive permissions
        os.chmod(backup_path, 0o600)
        print(f"[SUCCESS] Backup created: {filename}")
        
        self.cleanup_old_backups()
        return backup_path

    def cleanup_old_backups(self, keep: int = 5):
        try:
            files = sorted(
                [os.path.join(self.backup_dir, f) for f in os.listdir(self.backup_dir) if f.startswith("vortex_backup_")],
                key=os.path.getmtime
            )
            if len(files) > keep:
                for f in files[:-keep]:
                    print(f"[INFO] Removing old backup: {f}")
                    os.remove(f)
        except Exception as e:
            print(f"[WARN] Cleanup failed: {e}")

    def restore_backup(self, filename: str):
        backup_path = os.path.join(self.backup_dir, filename)
        if not os.path.exists(backup_path):
            print(f"[ERROR] Backup file {filename} not found.")
            return False

        print(f"[INFO] Restoring from {filename}...")
        try:
            with tarfile.open(backup_path, "r:gz") as tar:
                tar.extractall(path="/")
            print("[SUCCESS] Data restored. Restarting services...")
            self.restart_all_services()
            return True
        except Exception as e:
            print(f"[ERROR] Restore failed: {e}")
            return False

    def restart_all_services(self):
        services = ["nginx", "xray", "wg-quick@wg0", "openvpn-server@server"]
        for svc in services:
            subprocess.run(["systemctl", "restart", svc], check=False)

if __name__ == "__main__":
    import sys
    manager = BackupManager()
    if len(sys.argv) > 1 and sys.argv[1] == "restore":
        if len(sys.argv) > 2:
            manager.restore_backup(sys.argv[2])
        else:
            print("Usage: backup_manager.py restore <filename>")
    else:
        manager.create_backup()
