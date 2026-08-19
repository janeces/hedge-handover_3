#!/bin/sh
set -eu

SCRIPT_PATH="${SCRIPT_PATH:-/usr/local/hedge_device_io}"
OVERRIDE_DIR="/etc/systemd/system/tailscaled.service.d"
OVERRIDE_FILE="$OVERRIDE_DIR/10-wait-valid-time.conf"
TS_STATE_DIR="/var/lib/tailscale"

if ! systemctl list-unit-files | awk '{print $1}' | grep -q '^tailscaled.service$'; then
  printf "[tailscale-time-guard] tailscaled.service not found. Skipping override.\n"
  exit 0
fi

mkdir -p "$OVERRIDE_DIR"

exec_line="$(systemctl cat tailscaled 2>/dev/null | awk '/^ExecStart=/{sub(/^ExecStart=/, "", $0); print; exit}' || true)"
if [ -n "$exec_line" ]; then
  state_path="$(printf "%s\n" "$exec_line" | awk '
    {
      for (i = 1; i <= NF; i++) {
        if ($i == "--state" && i < NF) { print $(i + 1); exit }
        if ($i ~ /^--state=/) { sub(/^--state=/, "", $i); print $i; exit }
      }
    }
  ')"

  state_dir="$(printf "%s\n" "$exec_line" | awk '
    {
      for (i = 1; i <= NF; i++) {
        if ($i == "--statedir" && i < NF) { print $(i + 1); exit }
        if ($i ~ /^--statedir=/) { sub(/^--statedir=/, "", $i); print $i; exit }
      }
    }
  ')"

  if [ -n "$state_dir" ]; then
    TS_STATE_DIR="$state_dir"
  elif [ -n "$state_path" ]; then
    case "$state_path" in
      mem:*)
        # In-memory state has no persistent directory to prepare.
        ;;
      */*)
        TS_STATE_DIR="${state_path%/*}"
        ;;
    esac
  fi
fi

if [ -n "$TS_STATE_DIR" ] && [ "$TS_STATE_DIR" != "mem:" ]; then
  mkdir -p "$TS_STATE_DIR"
  chmod 700 "$TS_STATE_DIR" || true
fi

cat > "$OVERRIDE_FILE" <<EOF
[Unit]
After=network-online.target time-sync.target
Wants=network-online.target time-sync.target

[Service]
ExecStartPre=$SCRIPT_PATH/wait_for_valid_time.sh
ExecStartPre=/bin/mkdir -p $TS_STATE_DIR
ExecStartPre=/bin/chmod 700 $TS_STATE_DIR
EOF

systemctl daemon-reload

if systemctl is-enabled tailscaled >/dev/null 2>&1; then
  systemctl restart tailscaled || true
else
  systemctl enable tailscaled || true
  systemctl start tailscaled || true
fi

printf "[tailscale-time-guard] Installed override at %s\n" "$OVERRIDE_FILE"
printf "[tailscale-time-guard] Ensured tailscaled state directory: %s\n" "$TS_STATE_DIR"
