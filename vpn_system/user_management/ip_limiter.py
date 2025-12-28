import os
import sys
import subprocess
import datetime

# Add parent directory to path so we can import core
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.models import VortexDB

# Configuration
ACCESS_LOG = "/var/log/xray/access.log"
LIMIT_LOG = "/var/log/vortex-x/limit_violations.log"
MAX_LOG_LINES = 1000

def log_violation(username, ip_count, limit, ips):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    msg = f"[{timestamp}] User '{username}' exceeded limit! Active IPs: {ip_count}/{limit} -> {list(ips)}"
    print(msg)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(LIMIT_LOG), exist_ok=True)
    
    with open(LIMIT_LOG, "a") as f:
        f.write(msg + "\n")

def limit_ip():
    db = VortexDB()
    
    if not os.path.exists(ACCESS_LOG):
        # logging.error(f"Access log not found at {ACCESS_LOG}")
        return

    # Dictionary to store user: {set of IPs}
    user_ips = {}

    try:
        # Read last N lines to get recent activity
        # We assume Xray logs are standard: "date time src_ip accepted protocol:email"
        # Example: 2023/12/27 14:49:19 192.168.1.1:54321 accepted vless:user1@vortex
        
        # We only care about lines from the last few minutes strictly speaking, 
        # but tailing the last 1000 lines gives a good approximation of "currently active"
        # if the server is busy. For a more precise "active" check, we'd need a real-time log parser or API stats.
        lines = subprocess.check_output(["tail", "-n", str(MAX_LOG_LINES), ACCESS_LOG]).decode().splitlines()
        
        for line in lines:
            if "accepted" not in line:
                continue
                
            parts = line.split()
            # Find the 'accepted' keyword index to locate email
            try:
                acc_idx = parts.index("accepted")
                # Source IP is usually before 'accepted'
                # Format: date time src_ip ...
                src_ip_port = parts[acc_idx - 1]
                src_ip = src_ip_port.split(':')[0]
                
                # Protocol and email are usually after 'accepted'
                # Format: protocol:email
                proto_email = parts[acc_idx + 1]
                if ":" in proto_email:
                    email = proto_email.split(':')[1]
                else:
                    continue # format might be different

                # Skip if email is empty or system internal
                if not email: 
                    continue

                if email not in user_ips:
                    user_ips[email] = set()
                
                user_ips[email].add(src_ip)

            except (ValueError, IndexError):
                continue
                
    except Exception as e:
        print(f"Error processing logs: {e}")
        return

    # Check against DB limits
    for email, ips in user_ips.items():
        user = db.get_user(email)
        if user:
            limit = user.get("ip_limit", 2) # Default limit 2
            if len(ips) > limit:
                log_violation(email, len(ips), limit, ips)
                # TODO: Implement Kick/Ban logic here
                # e.g. Add IP to iptables drop list for 5 minutes
                # subprocess.run(["ipset", "add", "banned_ips", ...])

if __name__ == "__main__":
    limit_ip()