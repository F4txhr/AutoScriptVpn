#!/bin/bash

# Vortex-x CLI Menu
# Author: F4txhr

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m'

LIB_PATH="/usr/local/lib/vortex-x"
if [ ! -d "$LIB_PATH" ]; then
    LIB_PATH="."
fi

show_header() {
    clear
    echo -e "${CYAN}  __      __         _                 __  "
    echo -e "  \\ \\    / /        | |                \\ \\ "
    echo -e "   \\ \\  / /__  _ __ | |_ _____  __      \\ \\ "
    echo -e "    \\ \\/ / _ \\| '__|| __/ _ \\ \\/ /_____  \\ \\ "
    echo -e "     \\  / (_) | |   | ||  __/>  <|_____| / / "
    echo -e "      \\/ \\___/|_|    \\__\\___/_/\\_\\      /_/  ${NC}"
    echo -e "      ${BLUE}VORTEX-X CENTRAL PANEL${NC}"
    echo -e "      ${BLUE}Author: F4txhr | Professional VPN Engine${NC}"
    echo -e "${BLUE}==================================================${NC}"

    # Call Python metrics engine
    METRICS=$(python3 "$LIB_PATH/monitoring/sys_metrics.py")
    
    HOSTNAME=$(echo $METRICS | jq -r '.hostname')
    UPTIME=$(echo $METRICS | jq -r '.uptime')
    CPU=$(echo $METRICS | jq -r '.cpu')
    RAM=$(echo $METRICS | jq -r '.ram')
    DISK=$(echo $METRICS | jq -r '.disk')
    RX=$(echo $METRICS | jq -r '.net_rx')
    TX=$(echo $METRICS | jq -r '.net_tx')
    USERS=$(echo $METRICS | jq -r '.total_users')
    SSL=$(echo $METRICS | jq -r '.ssl_expiry')

    echo -e "  Host: ${GREEN}$HOSTNAME${NC} | Uptime: ${GREEN}$UPTIME${NC} | Users: ${PURPLE}$USERS${NC}"
    echo -e "  CPU : ${YELLOW}$CPU${NC} | RAM: ${YELLOW}$RAM${NC} | Disk: ${YELLOW}$DISK${NC} | SSL: ${CYAN}$SSL${NC}"
    echo -e "  Net : RX: ${BLUE}$RX${NC} | TX: ${BLUE}$TX${NC}"
    echo -e "${BLUE}==================================================${NC}"
}

while true; do
    show_header
    echo -e "  ${PURPLE}[Core]${NC}"
    echo -e "  1. VPN Status & Monitoring"
    echo -e "  2. Manage Users"
    echo -e "  3. Protocol Manager"
    echo -e ""
    echo -e "  ${PURPLE}[System]${NC}"
    echo -e "  4. Network & Firewall"
    echo -e "  5. SSL & Domain"
    echo -e "  6. Backup & Restore"
    echo -e "  7. System Audit (Doctor)"
    echo -e "  8. System Info"
    echo -e "  0. Exit"
    echo -e "${BLUE}==================================================${NC}"
    read -p "  Select Option (0-8): " choice

    case $choice in
        1) 
            python3 "$LIB_PATH/monitoring/traffic_viewer.py"
            ;;
        2) 
            echo -e "\n--- User Management ---"
            echo "1. Add User"
            echo "2. Delete User (Manual)"
            echo "3. Clash Config"
            read -p "Select: " u_opt
            if [ "$u_opt" == "1" ]; then
                read -p "Username: " uname
                read -p "Protocol (vless/vmess/trojan/shadowsocks/wireguard/openvpn): " proto
                echo -e "\n${YELLOW}Bandwidth default (GB):${NC}"
                echo "  Trial (1 hour): 2 GB"
                echo "  3 days        : 64 GB"
                echo "  7 days        : 128 GB"
                echo "  14 days       : 256 GB"
                echo "  30 days       : 512 GB"
                read -p "Days (default 30, use 0 for trial): " days
                read -p "IP Limit (default 2): " ip_limit
                read -p "Bandwidth Quota GB (0 = unlimited): " quota_gb
                if [ -z "$days" ]; then
                    days=30
                fi
                if [ "$days" = "0" ]; then
                    read -p "Trial hours (default 1 for trial): " trial_hours
                    if [ -z "$trial_hours" ]; then
                        trial_hours=1
                    fi
                else
                    trial_hours=""
                fi
                if [ -z "$quota_gb" ]; then
                    if [ "$days" = "0" ]; then
                        quota_gb=2
                    elif [ "$days" = "3" ]; then
                        quota_gb=64
                    elif [ "$days" = "7" ]; then
                        quota_gb=128
                    elif [ "$days" = "14" ]; then
                        quota_gb=256
                    elif [ "$days" = "30" ]; then
                        quota_gb=512
                    fi
                fi
                host=$(python3 - <<'PY'
import os
import sys

lib_path = "/usr/local/lib/vortex-x"
if not os.path.exists(lib_path):
    lib_path = "."
sys.path.append(lib_path)

from core.models import VortexDB
db = VortexDB()
print(db.data.get("settings", {}).get("domain", ""))
PY
)
                extra_args=(--ntls-port 80)
                if [ -n "$host" ]; then
                    extra_args+=(--host "$host")
                fi
                if [ -n "$days" ]; then
                    extra_args+=(--days "$days")
                fi
                if [ -n "$trial_hours" ]; then
                    extra_args+=(--trial-hours "$trial_hours")
                fi
                if [ -n "$ip_limit" ]; then
                    extra_args+=(--ip-limit "$ip_limit")
                fi
                if [ -n "$quota_gb" ]; then
                    extra_args+=(--quota-gb "$quota_gb")
                fi
                python3 "$LIB_PATH/cli/vortex-x" user add -u "$uname" -p "$proto" "${extra_args[@]}"
            elif [ "$u_opt" == "3" ]; then
                 read -p "Username: " uname
                 python3 "$LIB_PATH/cli/vortex-x" user clash -u "$uname"
            else
                echo "Use CLI: vortex-x user [cmd]"
            fi
            read -p "Press Enter..."
            ;;
        3)
            echo -e "\n${BLUE}==================================================${NC}"
            echo -e "           VORTEX-X SERVICE STATUS                "
            echo -e "${BLUE}==================================================${NC}"
            
            services=("xray" "nginx" "crond" "firewalld")
            for svc in "${services[@]}"; do
                if systemctl is-active --quiet "$svc"; then
                    echo -e "  $svc : ${GREEN}RUNNING${NC}"
                else
                    echo -e "  $svc : ${RED}STOPPED / FAILED${NC}"
                fi
            done
            
            echo -e "${BLUE}--------------------------------------------------${NC}"
            echo -e "Press [L] for Detailed Logs or Enter to return."
            read -p "Option: " log_opt
            if [[ "$log_opt" =~ ^[Ll]$ ]]; then
                echo -e "\n--- Xray Logs (Last 20 lines) ---"
                tail -n 20 /var/log/xray/access.log 2>/dev/null || journalctl -u xray -n 20 --no-pager
                echo -e "\n--- Nginx Status ---"
                nginx -t
            fi
            read -p "Press Enter..."
            ;;
        4)
            echo -e "\n${BLUE}==================================================${NC}"
            echo -e "           VORTEX-X FIREWALL STATUS               "
            echo -e "${BLUE}==================================================${NC}"
            if command -v firewall-cmd &> /dev/null; then
                MASQ=$(firewall-cmd --query-masquerade)
                echo -e "  IP Masquerade (NAT) : $([[ "$MASQ" == "yes" ]] && echo -e "${GREEN}ENABLED${NC}" || echo -e "${RED}DISABLED (Critical for VPN)${NC}")"
                echo -e "  Allowed Services    : $(firewall-cmd --list-services)"
                echo -e "  Allowed Ports       : $(firewall-cmd --list-ports)"
                echo -e "${BLUE}--------------------------------------------------${NC}"
                echo -e "Detailed Firewalld Output:"
                firewall-cmd --list-all
            else
                ufw status verbose
            fi
            read -p "Press Enter..."
            ;;
        5)
            echo -e "\n--- SSL Manager ---"
            python3 "$LIB_PATH/scripts/ssl_manager.py" check
            read -p "Press Enter..."
            ;;
        6)
            echo -e "\n--- Backup Manager ---"
            echo "1. Create Backup"
            echo "2. Restore Backup"
            read -p "Select: " b_opt
            if [ "$b_opt" == "1" ]; then
                python3 "$LIB_PATH/cli/vortex-x" backup create
            elif [ "$b_opt" == "2" ]; then
                read -p "Backup Filename: " b_file
                python3 "$LIB_PATH/cli/vortex-x" backup restore -f "$b_file"
            fi
            read -p "Press Enter..."
            ;;
        7) python3 "$LIB_PATH/scripts/audit.py"; echo -e "\nPress Enter to return..."; read ;;
        8) neofetch || hostnamectl; read -p "Press Enter..." ;;
        0) exit 0 ;;
        *) echo -e "  ${RED}Invalid Option${NC}"; sleep 1 ;;
    esac
done
