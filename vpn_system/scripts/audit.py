import os
import subprocess
import shutil
import psutil
import json

class SystemAuditor:
    def __init__(self):
        self.issues = []
        self.warnings = []
        self.passed = []

    def check_permissions(self):
        checks = [
            ("/usr/local/etc/vortex-x/db.json", 0o600, "Database"),
            ("/usr/local/etc/xray/config.json", 0o644, "Xray Config"),
            ("/etc/letsencrypt/live", 0o755, "SSL Certificates")
        ]
        
        for path, max_mode, name in checks:
            if os.path.exists(path):
                mode = os.stat(path).st_mode & 0o777
                if mode > max_mode:
                    self.warnings.append(f"Permission too loose for {name}: {oct(mode)} (Should be <= {oct(max_mode)})")
                else:
                    self.passed.append(f"Permission OK: {name}")
            else:
                if "SSL" not in name: # SSL might not exist yet
                    self.issues.append(f"Missing File: {name} at {path}")

    def check_services(self):
        services = ["nginx", "xray", "fail2ban", "cron"] # Firewall checked separately
        for svc in services:
            res = subprocess.run(["systemctl", "is-active", svc], capture_output=True, text=True)
            if res.returncode == 0 and res.stdout.strip() == "active":
                self.passed.append(f"Service Active: {svc}")
            else:
                self.issues.append(f"Service Inactive/Missing: {svc}")

    def check_security(self):
        # SSH Hardening
        try:
            with open("/etc/ssh/sshd_config", "r") as f:
                config = f.read()
                if "PermitRootLogin yes" in config and not config.strip().startswith("#"):
                    self.warnings.append("SSH: Root login is enabled (PermitRootLogin yes)")
                if "PasswordAuthentication yes" in config:
                    self.warnings.append("SSH: Password auth is enabled (Consider keys only)")
        except:
            self.issues.append("Could not read SSH config")

        # Firewall (UFW or Firewalld)
        firewall_active = False
        
        # Check UFW
        try:
            res = subprocess.run(["ufw", "status"], capture_output=True, text=True)
            if "active" in res.stdout:
                self.passed.append("Firewall (UFW): Active")
                firewall_active = True
        except FileNotFoundError:
            pass

        # Check Firewalld
        if not firewall_active:
            try:
                res = subprocess.run(["firewall-cmd", "--state"], capture_output=True, text=True)
                if res.returncode == 0 and "running" in res.stdout:
                    self.passed.append("Firewall (Firewalld): Active")
                    firewall_active = True
            except FileNotFoundError:
                pass
        
        if not firewall_active:
            self.issues.append("Firewall: No active firewall detected (UFW/Firewalld)")

    def check_resources(self):
        # Disk
        disk = shutil.disk_usage("/")
        if disk.free < 1 * 1024 * 1024 * 1024: # 1GB
            self.issues.append(f"Low Disk Space: {disk.free / (1024**3):.2f} GB free")
        else:
            self.passed.append(f"Disk Space OK: {disk.free / (1024**3):.2f} GB free")

        # RAM
        ram = psutil.virtual_memory()
        if ram.percent > 90:
            self.warnings.append(f"High RAM Usage: {ram.percent}%")
        
        # Swap
        swap = psutil.swap_memory()
        if swap.total == 0:
            self.warnings.append("No Swap Memory detected (Recommended for stability)")

    def run(self):
        print("\n🔎 Vortex-x System Audit Starting...\n")
        
        self.check_permissions()
        self.check_services()
        self.check_security()
        self.check_resources()

        print("--- [ PASSED ] ---")
        for msg in self.passed:
            print(f"✅ {msg}")

        if self.warnings:
            print("\n--- [ WARNINGS ] ---")
            for msg in self.warnings:
                print(f"⚠️  {msg}")

        if self.issues:
            print("\n--- [ CRITICAL ISSUES ] ---")
            for msg in self.issues:
                print(f"❌ {msg}")
        
        print("\nAudit Complete.")

if __name__ == "__main__":
    auditor = SystemAuditor()
    auditor.run()