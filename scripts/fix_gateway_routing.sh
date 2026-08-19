#!/bin/sh
set -eu

ETH_DEV="${ETH_DEV:-}"
WWAN_DEV="${WWAN_DEV:-}"
ETH_GW="${ETH_GW:-10.1.1.1}"
WWAN_GW="${WWAN_GW:-}"
GSM_CTRL_DEV="${GSM_CTRL_DEV:-}"

if [ -z "$WWAN_DEV" ]; then
  GSM_CTRL_DEV="$(nmcli -t -f DEVICE,TYPE,STATE device status | awk -F: '$2=="gsm" && $1!="" && $1!="--" {print $1; exit}')"
  if [ -n "$GSM_CTRL_DEV" ]; then
    WWAN_DEV="$(nmcli -g GENERAL.IP-IFACE device show "$GSM_CTRL_DEV" | sed '/^$/d' | head -n1)"
  fi
fi

if [ -z "$GSM_CTRL_DEV" ]; then
  GSM_CTRL_DEV="$(nmcli -t -f DEVICE,TYPE,STATE device status | awk -F: '$2=="gsm" && $1!="" && $1!="--" {print $1; exit}')"
fi

if [ -z "$WWAN_DEV" ]; then
  WWAN_DEV="$(ip -o link show | awk -F': ' '/(^| )wwan[0-9]+/ {print $2; exit}')"
fi

if [ -z "$ETH_DEV" ]; then
  ETH_DEV="$(nmcli -t -f DEVICE,TYPE,STATE device status | awk -F: '$2=="ethernet" && $1!="" && $1!="--" {print $1; exit}')"
fi

if [ -z "$WWAN_DEV" ]; then
  printf "[!] No active GSM/WWAN device detected on this host.\n"
  printf "[!] Run this script on the gateway (for example: ssh root@10.1.1.111).\n"
  exit 1
fi

if [ -z "$ETH_DEV" ]; then
  printf "[!] No active ethernet device detected on this host.\n"
  printf "[!] Set ETH_DEV manually if needed.\n"
  exit 1
fi

printf "[+] Using interfaces: ETH_DEV=%s, WWAN_DEV=%s\n" "$ETH_DEV" "$WWAN_DEV"

printf "[+] Applying temporary default route fix\n"

# Remove any ethernet defaults so internet egress prefers WWAN.
while ip route show default dev "$ETH_DEV" | grep -q '^default '; do
  ip route del default dev "$ETH_DEV" 2>/dev/null || true
done

if [ -z "$WWAN_GW" ]; then
  WWAN_GW="$(ip route show dev "$WWAN_DEV" | awk '/default/ {print $3; exit}')"
fi
if [ -z "$WWAN_GW" ]; then
  WWAN_GW="$(ip route show dev "$WWAN_DEV" | awk 'NR==1 {print $1; exit}' | cut -d/ -f1 | awk -F. '{print $1"."$2"."$3".1"}')"
fi
if [ -z "$WWAN_GW" ]; then
  printf "[!] Could not determine WWAN gateway. Set WWAN_GW manually.\n"
  exit 1
fi
printf "[+] Using WWAN gateway: %s\n" "$WWAN_GW"

# Remove duplicate WWAN defaults and keep a single preferred default route.
while ip route show default dev "$WWAN_DEV" | grep -q '^default '; do
  ip route del default dev "$WWAN_DEV" 2>/dev/null || true
done
ip route replace default via "$WWAN_GW" dev "$WWAN_DEV" metric 50

printf "[+] Verifying internet reachability\n"
ping -c 4 8.8.8.8
if nslookup pypi.org > /dev/null 2>&1; then
  ping -c 4 pypi.org
else
  printf "[!] DNS resolution not working yet (nslookup pypi.org failed). Continuing anyway.\n"
fi

printf "[+] Detecting active NetworkManager profiles\n"
LAN_NAME="$(nmcli -t -f NAME,TYPE,DEVICE connection show --active | awk -F: '$2=="ethernet" && $3!="" {print $1; exit}')"
CELL_NAME="$(nmcli -t -f NAME,TYPE,DEVICE connection show --active | awk -F: '$2=="gsm" && $3!="" {print $1; exit}')"

if [ -z "$LAN_NAME" ]; then
  LAN_NAME="$(nmcli -t -f NAME,TYPE,DEVICE connection show | awk -F: -v dev="$ETH_DEV" '$2=="ethernet" && $3==dev {print $1; exit}')"
fi

if [ -z "$LAN_NAME" ]; then
  LAN_NAME="$(nmcli -t -f NAME,TYPE connection show | awk -F: '$2=="ethernet" {print $1; exit}')"
fi

if [ -z "$LAN_NAME" ]; then
  LAN_NAME="$(nmcli -t -f NAME,TYPE,DEVICE connection show --active | awk -F: -v dev="$ETH_DEV" '$3==dev {print $1; exit}')"
fi

if [ -z "$LAN_NAME" ]; then
  LAN_NAME="$(nmcli -t -f NAME,TYPE,DEVICE connection show | awk -F: -v dev="$ETH_DEV" '$3==dev {print $1; exit}')"
fi

if [ -z "$CELL_NAME" ] && [ -n "$GSM_CTRL_DEV" ]; then
  CELL_NAME="$(nmcli -t -f NAME,TYPE,DEVICE connection show | awk -F: -v dev="$GSM_CTRL_DEV" '$2=="gsm" && $3==dev {print $1; exit}')"
fi

if [ -z "$CELL_NAME" ]; then
  CELL_NAME="$(nmcli -t -f NAME,TYPE connection show | awk -F: '$2=="gsm" {print $1; exit}')"
fi

if [ -z "$LAN_NAME" ]; then
  printf "[!] Could not detect ethernet profile. Available connections:\n"
  nmcli -t -f NAME,TYPE,DEVICE connection show
  printf "[!] Set LAN_NAME manually, e.g.: LAN_NAME=<name> %s\n" "$0"
  exit 1
fi

if [ -z "$CELL_NAME" ]; then
  printf "[!] Could not detect active gsm profile. Set CELL_NAME manually.\n"
  exit 1
fi

printf "[+] Using LAN profile: %s\n" "$LAN_NAME"
printf "[+] Using CELL profile: %s\n" "$CELL_NAME"

printf "[+] Making route preference persistent via NetworkManager\n"
nmcli con mod "$LAN_NAME" ipv4.never-default yes ipv4.route-metric 300 ipv4.gateway ""
nmcli con mod "$CELL_NAME" ipv4.never-default no ipv4.route-metric 50 ipv4.dns "8.8.8.8 8.8.4.4" ipv4.ignore-auto-dns no
nmcli con up "$CELL_NAME"
nmcli con up "$LAN_NAME"

printf "[+] Re-applying default route cleanup after profile updates\n"
while ip route show default dev "$ETH_DEV" | grep -q '^default '; do
  ip route del default dev "$ETH_DEV" 2>/dev/null || true
done

# Keep at most one WWAN default route. Delete extras if present.
wwan_defaults="$(ip route show default dev "$WWAN_DEV" || true)"
if [ -n "$wwan_defaults" ]; then
  idx=0
  printf "%s\n" "$wwan_defaults" | while IFS= read -r line; do
    [ -z "$line" ] && continue
    idx=$((idx + 1))
    if [ "$idx" -gt 1 ]; then
      ip route del $line 2>/dev/null || true
    fi
  done
fi

# Ensure there is one preferred default route via WWAN.
ip route replace default via "$WWAN_GW" dev "$WWAN_DEV" metric 50

printf "[+] Verifying DNS\n"
if nslookup sumo.operato.eu > /dev/null 2>&1; then
  printf "[+] DNS resolution working.\n"
else
  printf "[!] DNS still not working. Forcing resolv.conf fallback.\n"
  printf "nameserver 8.8.8.8\nnameserver 8.8.4.4\n" > /etc/resolv.conf
  printf "[+] /etc/resolv.conf updated.\n"
fi

printf "[+] Final route table\n"
ip route

default_count="$(ip route | awk '/^default /{c++} END{print c+0}')"
if [ "$default_count" -eq 1 ]; then
  printf "[+] Exactly one default route is configured.\n"
else
  printf "[!] Expected one default route, found %s.\n" "$default_count"
fi

printf "[+] Done\n"