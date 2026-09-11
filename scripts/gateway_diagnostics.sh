#!/bin/sh
set -u

# One-shot diagnostics for clock sync, networking, DNS, and Tailscale.

PASS=0
WARN=0
FAIL=0

report() {
  level="$1"
  msg="$2"
  case "$level" in
    PASS) PASS=$((PASS + 1)); prefix="[PASS]" ;;
    WARN) WARN=$((WARN + 1)); prefix="[WARN]" ;;
    FAIL) FAIL=$((FAIL + 1)); prefix="[FAIL]" ;;
    *) prefix="[INFO]" ;;
  esac
  printf "%s %s\n" "$prefix" "$msg"
}

has_cmd() {
  command -v "$1" >/dev/null 2>&1
}

tailscale_cmd() {
  if has_cmd tailscale; then
    printf "tailscale"
  elif [ -x /opt/bin/tailscale ]; then
    printf "/opt/bin/tailscale"
  else
    printf ""
  fi
}

section() {
  printf "\n=== %s ===\n" "$1"
}

show_or_warn() {
  if [ -n "$2" ]; then
    printf "%s\n" "$2"
  else
    report WARN "$1"
  fi
}

section "Clock"
if has_cmd date; then
  utc_now="$(date -u '+%Y-%m-%d %H:%M:%S UTC' 2>/dev/null || true)"
  show_or_warn "Unable to read UTC time." "$utc_now"
  year="$(date -u +%Y 2>/dev/null || echo 1970)"
  if [ "$year" -ge 2024 ]; then
    report PASS "Clock year looks sane: $year"
  else
    report FAIL "Clock year looks invalid: $year"
  fi
else
  report FAIL "date command not available."
fi

if has_cmd timedatectl; then
  td_out="$(timedatectl status 2>/dev/null || true)"
  show_or_warn "timedatectl returned no output." "$td_out"
  if printf "%s" "$td_out" | grep -qi "System clock synchronized: yes"; then
    report PASS "timedatectl reports synchronized clock."
  else
    report WARN "timedatectl does not confirm synchronized clock."
  fi
else
  report "INFO" "timedatectl not available; trying alternative NTP checks."
  if has_cmd chronyc; then
    ch_out="$(chronyc tracking 2>/dev/null || true)"
    if [ -n "$ch_out" ]; then
      printf "%s\n" "$ch_out"
      if printf "%s" "$ch_out" | grep -qi "Leap status[[:space:]]*:[[:space:]]*Normal"; then
        report PASS "chronyc indicates normal sync state."
      else
        report WARN "chronyc does not report a normal leap status."
      fi
    else
      report WARN "chronyc is present but returned no tracking data."
    fi
  elif has_cmd ntpq; then
    ntp_out="$(ntpq -pn 2>/dev/null || true)"
    if [ -n "$ntp_out" ]; then
      printf "%s\n" "$ntp_out"
      if printf "%s" "$ntp_out" | grep -q '^\*'; then
        report PASS "ntpq indicates an active sync peer (*)."
      else
        report WARN "ntpq does not show an active sync peer."
      fi
    else
      report WARN "ntpq is present but returned no peer data."
    fi
  else
    report WARN "No alternative NTP client found (chronyc/ntpq)."
  fi
fi

if has_cmd hwclock; then
  hw="$(hwclock -r 2>/dev/null || true)"
  if [ -n "$hw" ]; then
    printf "%s\n" "$hw"
    report PASS "RTC read succeeded."
  else
    report WARN "RTC read failed or no hardware RTC."
  fi
else
  report WARN "hwclock not available."
fi

section "Time Sync Service"
if has_cmd systemctl; then
  found_ts=0
  active_ts=0
  for unit in systemd-timesyncd.service chronyd.service ntpd.service; do
    if systemctl list-unit-files | awk '{print $1}' | grep -q "^$unit$"; then
      found_ts=1
      st="$(systemctl is-active "$unit" 2>/dev/null || true)"
      printf "%s: %s\n" "$unit" "$st"
      if [ "$st" = "active" ]; then
        active_ts=1
      fi
    fi
  done

  if [ "$found_ts" -eq 0 ]; then
    report WARN "No known time-sync systemd unit found (systemd-timesyncd/chronyd/ntpd)."
  elif [ "$active_ts" -eq 1 ]; then
    report PASS "At least one time-sync service is active."
  else
    report WARN "Known time-sync services found, but none is active."
  fi
else
  report WARN "systemctl not available."
fi

section "Routing"
if has_cmd ip; then
  routes="$(ip route 2>/dev/null || true)"
  show_or_warn "Could not read route table." "$routes"
  default_count="$(printf "%s\n" "$routes" | awk '/^default /{c++} END{print c+0}')"
  if [ "$default_count" -eq 1 ]; then
    report PASS "Exactly one default route exists."
  elif [ "$default_count" -gt 1 ]; then
    unique_defaults="$(printf "%s\n" "$routes" | awk '/^default /{print}' | sort -u | wc -l | tr -d ' ')"
    if [ "$unique_defaults" -eq 1 ]; then
      report PASS "Multiple default rows are identical ($default_count entries); effective route is stable."
    else
      report WARN "Multiple different default routes detected ($default_count); route preference may be unstable."
    fi
  else
    report FAIL "No default route present."
  fi
else
  report FAIL "ip command not available."
fi

section "DNS"
if [ -f /etc/resolv.conf ]; then
  ns_lines="$(grep -E '^[[:space:]]*nameserver[[:space:]]+' /etc/resolv.conf 2>/dev/null || true)"
  show_or_warn "No nameserver lines found in /etc/resolv.conf." "$ns_lines"
  if [ -n "$ns_lines" ]; then
    report PASS "Nameserver entries found in /etc/resolv.conf."
  else
    report FAIL "Missing nameserver entries in /etc/resolv.conf."
  fi
else
  report FAIL "/etc/resolv.conf not found."
fi

if has_cmd nslookup; then
  if nslookup pypi.org >/dev/null 2>&1; then
    report PASS "DNS lookup for pypi.org succeeded."
  else
    report FAIL "DNS lookup for pypi.org failed."
  fi
else
  report WARN "nslookup not available."
fi

section "Internet Reachability"
if has_cmd ping; then
  if ping -c 2 -W 2 8.8.8.8 >/dev/null 2>&1; then
    report PASS "Ping to 8.8.8.8 succeeded."
  else
    report FAIL "Ping to 8.8.8.8 failed."
  fi
else
  report WARN "ping not available."
fi

section "Tailscale"
if has_cmd systemctl && systemctl list-unit-files | awk '{print $1}' | grep -q '^tailscaled.service$'; then
  tailscaled_state="$(systemctl is-active tailscaled 2>/dev/null || true)"
  printf "tailscaled: %s\n" "$tailscaled_state"
  if [ "$tailscaled_state" = "active" ]; then
    report PASS "tailscaled service is active."
  else
    report FAIL "tailscaled service is not active."
  fi

  unit_text="$(systemctl cat tailscaled 2>/dev/null || true)"
  if [ -n "$unit_text" ]; then
    exec_line="$(printf "%s\n" "$unit_text" | awk '/^ExecStart=/{sub(/^ExecStart=/, "", $0); print; exit}')"
    if [ -n "$exec_line" ]; then
      printf "tailscaled ExecStart: %s\n" "$exec_line"

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

      state_path_ok=0
      if [ -n "$state_path" ]; then
        case "$state_path" in
          mem:*)
            report WARN "tailscaled uses in-memory state ($state_path); identity may not persist across reboot."
            ;;
          *)
            state_parent="${state_path%/*}"
            if [ -z "$state_parent" ] || [ "$state_parent" = "$state_path" ]; then
              state_parent="."
            fi
            if [ -d "$state_parent" ] && [ -w "$state_parent" ]; then
              state_path_ok=1
              report PASS "tailscaled state path is writable ($state_path)."
            elif [ -d "$state_parent" ]; then
              report WARN "tailscaled state directory exists but may not be writable ($state_parent)."
            else
              report WARN "tailscaled state directory missing ($state_parent)."
            fi
            ;;
        esac
      elif [ -n "$state_dir" ]; then
        if [ -d "$state_dir" ] && [ -w "$state_dir" ]; then
          state_path_ok=1
          report PASS "tailscaled statedir is writable ($state_dir)."
        elif [ -d "$state_dir" ]; then
          report WARN "tailscaled statedir exists but may not be writable ($state_dir)."
        else
          report WARN "tailscaled statedir is missing ($state_dir)."
        fi
      else
        if [ -d /var/lib/tailscale ] && [ -w /var/lib/tailscale ]; then
          report PASS "No explicit state flag; default /var/lib/tailscale exists and is writable."
        elif [ -d /var/lib/tailscale ]; then
          report WARN "No explicit state flag; /var/lib/tailscale exists but may not be writable."
        else
          report WARN "No explicit state flag and /var/lib/tailscale is missing; verify package defaults."
        fi
      fi

      ts_no_state_log="$(journalctl -u tailscaled -b --no-pager -n 120 2>/dev/null | grep -i 'no state directory' | tail -n1 || true)"
      if [ -n "$ts_no_state_log" ]; then
        if [ "$state_path_ok" -eq 1 ]; then
          report PASS "tailscaled logs 'no state directory' (likely network-lock related); configured state path looks healthy."
        else
          report WARN "tailscaled logs 'no state directory'; verify state path and permissions."
        fi
      fi
    else
      report WARN "Could not parse tailscaled ExecStart line from systemd unit."
    fi
  else
    report WARN "systemctl cat tailscaled returned no unit details."
  fi
else
  report WARN "tailscaled service not found."
fi

ts_cmd="$(tailscale_cmd)"
if [ -n "$ts_cmd" ]; then
  ts_connected=0
  ts_status="$($ts_cmd status 2>/dev/null || true)"
  if [ -n "$ts_status" ]; then
    printf "%s\n" "$ts_status"
    if printf "%s\n" "$ts_status" | awk 'NF > 0 && $NF != "offline" {found=1} END{exit(found?0:1)}'; then
      ts_connected=1
    fi
    if printf "%s" "$ts_status" | grep -qi "logged out\|stopped\|not connected\|error"; then
      report WARN "tailscale status indicates not fully connected."
    else
      report PASS "tailscale status returned peers/state."
    fi
  else
    report WARN "tailscale status produced no output."
  fi

  ts_json="$($ts_cmd status --json 2>/dev/null || true)"
  if [ -n "$ts_json" ]; then
    if printf "%s" "$ts_json" | grep -q '"BackendState":"Running"'; then
      report PASS "tailscale backend state is Running."
    else
      if [ "$ts_connected" -eq 1 ]; then
        report "INFO" "tailscale JSON backend state is not Running, but textual status shows active connectivity."
      else
        report WARN "tailscale backend not Running (see JSON output with tailscale status --json)."
      fi
    fi
  fi
else
  if has_cmd systemctl && systemctl is-active tailscaled >/dev/null 2>&1; then
    report WARN "tailscale CLI not available, but tailscaled is active (limited diagnostics)."
  else
    report WARN "tailscale CLI not available."
  fi
fi

section "Recent Logs"
if has_cmd journalctl && has_cmd systemctl; then
  if systemctl list-unit-files | awk '{print $1}' | grep -q '^tailscaled.service$'; then
    printf "-- tailscaled (last 30 lines) --\n"
    journalctl -u tailscaled -b --no-pager -n 30 2>/dev/null || true
  fi
  if systemctl list-unit-files | awk '{print $1}' | grep -q '^systemd-timesyncd.service$'; then
    printf "-- systemd-timesyncd (last 20 lines) --\n"
    journalctl -u systemd-timesyncd -b --no-pager -n 20 2>/dev/null || true
  fi
else
  report WARN "journalctl/systemctl not available for log capture."
fi

section "Summary"
printf "PASS=%s WARN=%s FAIL=%s\n" "$PASS" "$WARN" "$FAIL"

if [ "$FAIL" -gt 0 ]; then
  exit 2
fi

if [ "$WARN" -gt 0 ]; then
  exit 1
fi

exit 0
