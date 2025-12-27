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
    echo -e "  7. System Info"
    echo -e "  0. Exit"
    echo -e "${BLUE}--------------------------------------------------${NC}"
    read -p "  Select Option: " choice

    case $option in
        # Placeholder logic
        0) exit 0 ;;
        *) echo -e "  ${RED}Feature coming soon!${NC}"; sleep 1 ;;
    esac
done
