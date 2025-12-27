#!/bin/bash

# Define colors
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

VPN_CTL="/usr/local/bin/vpn-ctl"

check_root() {
    if [ "$(id -u)" -ne 0 ]; then
        echo -e "${RED}Please run as root!${NC}"
        exit 1
    fi
}

show_header() {
    clear
    echo -e "${BLUE}======================================${NC}"
    echo -e "${BLUE}           Vortex-x Vpn               ${NC}"
    echo -e "${BLUE}======================================${NC}"
    
    # Show Registered Domain
    DB_FILE="/usr/local/lib/vpn_system/db.json"
    if [ -f "$DB_FILE" ]; then
        DOMAIN=$(python3 -c "import json; data=json.load(open('$DB_FILE')); print(data['hosts'][0]['domain'] if data['hosts'] else 'Not Set')" 2>/dev/null)
        SERVER_IP=$(python3 -c "import json; data=json.load(open('$DB_FILE')); print(data['hosts'][0]['ip'] if data['hosts'] else 'N/A')" 2>/dev/null)
        echo -e "  Domain : ${GREEN}$DOMAIN${NC}"
        echo -e "  IP     : ${GREEN}$SERVER_IP${NC}"
        echo -e "${BLUE}======================================${NC}"
    fi
}

wait_enter() {
    echo -e ""
    read -p "Press Enter to continue..."
}

menu() {
    check_root
    while true; do
        show_header
        # Show monitor directly on main menu
        $VPN_CTL monitor
        echo -e "${BLUE}======================================${NC}"
        echo -e "1. Initialize System (Set Domain)"
        echo -e "2. Create VPN Account"
        echo -e "3. Show User Config"
        echo -e "4. Check/Run Auto-Expiry"
        echo -e "5. Exit"
        echo -e "${BLUE}======================================${NC}"
        read -p "Select Option [1-5]: " option

        case $option in
            1)
                read -p "Enter Domain for this server: " domain
                if [[ -z "$domain" ]]; then
                    echo -e "${RED}Domain cannot be empty!${NC}"
                else
                    $VPN_CTL init -d "$domain"
                fi
                wait_enter
                ;;
            2)
                echo -e "\n${BLUE}--- Select Protocol ---${NC}"
                echo "1. VLESS (Xray)"
                echo "2. VMess (Xray)"
                echo "3. Trojan (Xray)"
                echo "4. Shadowsocks (Xray)"
                echo "5. WireGuard"
                echo "6. OpenVPN"
                echo "0. Cancel"
                read -p "Protocol Choice [1-6]: " p_choice
                
                case $p_choice in
                    1) proto="vless" ;;
                    2) proto="vmess" ;;
                    3) proto="trojan" ;;
                    4) proto="shadowsocks" ;;
                    5) proto="wireguard" ;;
                    6) proto="openvpn" ;;
                    0) continue ;;
                    *) echo -e "${RED}Invalid protocol!${NC}"; sleep 1; continue ;;
                esac

                echo -e "\n${BLUE}--- User Details ---${NC}"
                read -p "Enter Username: " user
                
                if [[ -z "$user" ]]; then
                    echo -e "${RED}Username cannot be empty!${NC}"
                    sleep 1
                    continue
                fi

                echo -e "Creating $proto account for $user..."
                $VPN_CTL user add -u "$user" -p "$proto"
                wait_enter
                ;;
            3)
                read -p "Enter Username: " user
                echo -e "Select Protocol: [vless/vmess/trojan/shadowsocks/wireguard/openvpn]"
                read -p "Protocol: " proto
                $VPN_CTL user show -u "$user" -p "$proto"
                wait_enter
                ;;
            4)
                echo "Running expiry monitor manually..."
                python3 /usr/local/lib/vpn_system/user_management/expiry_monitor.py
                wait_enter
                ;;
            5)
                echo "Exiting..."
                exit 0
                ;;
            *)
                echo -e "${RED}Invalid option!${NC}"
                sleep 1
                ;;
        esac
    done
}

menu