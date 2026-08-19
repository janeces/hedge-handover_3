#!/bin/sh
set -eu

# Wait until system clock appears sane so TLS-based services can connect.
MIN_VALID_YEAR="${MIN_VALID_YEAR:-2024}"
MAX_WAIT_SECONDS="${MAX_WAIT_SECONDS:-300}"
SLEEP_SECONDS="${SLEEP_SECONDS:-5}"

elapsed=0

current_year() {
  date -u +%Y 2>/dev/null || echo 1970
}

is_time_valid() {
  y="$(current_year)"
  [ "$y" -ge "$MIN_VALID_YEAR" ]
}

if is_time_valid; then
  printf "[time-guard] Time already valid (UTC: %s).\n" "$(date -u '+%Y-%m-%d %H:%M:%S')"
  exit 0
fi

printf "[time-guard] Waiting for valid UTC time (year >= %s), timeout=%ss.\n" "$MIN_VALID_YEAR" "$MAX_WAIT_SECONDS"

while [ "$elapsed" -lt "$MAX_WAIT_SECONDS" ]; do
  if is_time_valid; then
    printf "[time-guard] Time became valid (UTC: %s).\n" "$(date -u '+%Y-%m-%d %H:%M:%S')"
    exit 0
  fi
  sleep "$SLEEP_SECONDS"
  elapsed=$((elapsed + SLEEP_SECONDS))
done

printf "[time-guard] Timeout reached; current UTC is still %s.\n" "$(date -u '+%Y-%m-%d %H:%M:%S')"
exit 1
