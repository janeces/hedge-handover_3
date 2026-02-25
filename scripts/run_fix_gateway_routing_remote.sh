#!/bin/sh
set -eu

source config/env.conf

SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

printf "[+] Running remote gateway routing fix on %s@%s\n" "$HOST_UNAME" "$HOST_NAME"
SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

if [ ! -f "$SCRIPT_DIR/fix_gateway_routing.sh" ]; then
	printf "[!] Could not find local script: %s\n" "$SCRIPT_DIR/fix_gateway_routing.sh"
	exit 1
fi

sshpass -p "$HOST_PWD" ssh $SSH_OPTS "$HOST_UNAME@$HOST_NAME" "sh -s" < "$SCRIPT_DIR/fix_gateway_routing.sh"
