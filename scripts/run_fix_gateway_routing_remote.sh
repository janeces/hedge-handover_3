#!/bin/sh
set -eu

SCRIPT_DIR="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

# Allow passing credentials as positional arguments: <uname> <host> <pwd>
# Falls back to config/env.conf if any argument is omitted.
if [ $# -lt 3 ]; then
  source "$SCRIPT_DIR/../config/env.conf"
fi

HOST_UNAME="${1:-$HOST_UNAME}"
HOST_NAME="${2:-$HOST_NAME}"
HOST_PWD="${3:-$HOST_PWD}"

SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null"

printf "[+] Running remote gateway routing fix on %s@%s\n" "$HOST_UNAME" "$HOST_NAME"

if [ ! -f "$SCRIPT_DIR/fix_gateway_routing.sh" ]; then
	printf "[!] Could not find local script: %s\n" "$SCRIPT_DIR/fix_gateway_routing.sh"
	exit 1
fi

sshpass -p "$HOST_PWD" ssh $SSH_OPTS "$HOST_UNAME@$HOST_NAME" "sh -s" < "$SCRIPT_DIR/fix_gateway_routing.sh"
