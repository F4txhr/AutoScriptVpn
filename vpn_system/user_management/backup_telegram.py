import os
import json
import zipfile
import subprocess
from datetime import datetime

# --- CONFIGURATION ---
# Replace with your actual Telegram Bot Token and Chat ID
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"
CHAT_ID = "YOUR_CHAT_ID_HERE"
DB_PATH = "/usr/local/lib/vpn_system/configs/db.json"
XRAY_CONFIG = "/usr/local/etc/xray/config.json"
WG_CONFIG = "/etc/wireguard/wg0.conf"

def create_backup():
    filename = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
    with zipfile.ZipFile(filename, 'w') as zipf:
        if os.path.exists(DB_PATH): zipf.write(DB_PATH, arcname="db.json")
        if os.path.exists(XRAY_CONFIG): zipf.write(XRAY_CONFIG, arcname="xray_config.json")
        if os.path.exists(WG_CONFIG): zipf.write(WG_CONFIG, arcname="wg0.conf")
    return filename

def send_to_telegram(file_path):
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        print("Telegram Token not configured. Skipping upload.")
        return
    
    cmd = [
        "curl", "-v",
        "-F", f"chat_id={CHAT_ID}",
        "-F", f"document=@{file_path}",
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendDocument"
    ]
    subprocess.run(cmd, check=False)

def main():
    if not (BOT_TOKEN and CHAT_ID):
        return
    
    backup_file = create_backup()
    send_to_telegram(backup_file)
    os.remove(backup_file)

if __name__ == "__main__":
    main()
