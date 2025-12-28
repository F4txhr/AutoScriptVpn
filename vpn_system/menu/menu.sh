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
    echo -e "  \ \    / /        | |                \ \ "
    echo -e "   \ \  / /__  _ __ | |_ _____  __      \ \ "
    echo -e "    \ \/ / _ \| '__|| __/ _ \ \/ /_____  \ \ "
    echo -e "     \  / (_) | |   | ||  __/>  <|_____| / / "
    echo -e "      \/ \___/|_|    \__\___/_/\_\      /_/  ${NC}"
    echo -e "      ${BLUE}Author: F4txhr | Professional VPN Engine${NC}"
    echo -e "${BLUE}--------------------------------------------------${NC}"

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

    echo -e "  Host: ${GREEN}$HOSTNAME${NC} | Uptime: ${GREEN}$UPTIME${NC}"
    echo -e "  CPU : ${YELLOW}$CPU${NC} | RAM: ${YELLOW}$RAM${NC} | Disk: ${YELLOW}$DISK${NC}"
    echo -e "  Net : RX: ${BLUE}$RX${NC} | TX: ${BLUE}$TX${NC} | Users: ${PURPLE}$USERS${NC}"
    echo -e "  SSL : ${CYAN}Expires: $SSL${NC}"
    echo -e "${BLUE}--------------------------------------------------${NC}"
}

while true; do
    show_header
    echo -e "  1. VPN Status & Monitoring"
    echo -e "  2. Manage Users"
    echo -e "  3. Protocol Manager"
    echo -e "  4. Network & Firewall"
    echo -e "  5. SSL & Domain"
    echo -e "  6. Backup & Restore"
    echo -e "  7. System Audit (Doctor)"
    echo -e "  8. System Info"
    echo -e "  0. Exit"
    echo -e "${BLUE}--------------------------------------------------${NC}"
    read -p "  Select Option: " choice

    case $choice in
        1) 
            clear
            python3 "$LIB_PATH/monitoring/traffic_monitor.py" # Or detailed status
            echo -e "Feature: Real-time Traffic Monitor (Check log: /var/log/vortex-x)"
            read -p "Press Enter..." 
            ;;
        2) 
            echo -e "\n--- User Management ---"
            echo "1. Add User"
            echo "2. Delete User (Manual)"
            echo "3. Clash Config"
            read -p "Select: " u_opt
            if [ "$u_opt" == "1" ]; then
                read -p "Username: " uname
                read -p "Protocol (vless/vmess/trojan/ssh): " proto
                python3 "$LIB_PATH/cli/vortex-x" user add -u "$uname" -p "$proto"
            elif [ "$u_opt" == "3" ]; then
                 read -p "Username: " uname
                 python3 "$LIB_PATH/cli/vortex-x" user clash -u "$uname"
            else
                echo "Use CLI: vortex-x user [cmd]"
            fi
            read -p "Press Enter..."
            ;;
        3)
            echo -e "\n--- Protocol Status ---"
            systemctl status xray --no-pager
            systemctl status nginx --no-pager
            read -p "Press Enter..."
            ;;
        4)
            echo -e "\n--- Firewall Status ---"
            if command -v firewall-cmd &> /dev/null; then
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
