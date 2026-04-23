#!/usr/bin/env bash
# .claude/scripts/profile.sh
# Usage:
#   profile.sh show        — prints current profile
#   profile.sh get         — prints just the profile name (no timestamp)
#   profile.sh set <name>  — switches to <name> (retail|ftmo)
#   profile.sh stale       — exits 0 if stale >12h, exits 1 otherwise
#   profile.sh validate    — checks profile exists in profiles/ dir

set -euo pipefail

FLAG_FILE="$(dirname "$0")/../active_profile"
PROFILES_DIR="$(dirname "$0")/../profiles"

cmd="${1:-show}"

case "$cmd" in
  show)
    if [[ -f "$FLAG_FILE" ]]; then
      cat "$FLAG_FILE"
    else
      echo "no profile set"
      exit 1
    fi
    ;;
  get)
    if [[ -f "$FLAG_FILE" ]]; then
      cut -d'|' -f1 "$FLAG_FILE" | tr -d ' '
    else
      echo ""
      exit 1
    fi
    ;;
  set)
    name="${2:-}"
    if [[ -z "$name" ]]; then
      echo "ERROR: profile name required" >&2
      exit 2
    fi
    if [[ ! -d "$PROFILES_DIR/$name" ]]; then
      echo "ERROR: profile '$name' not found in $PROFILES_DIR" >&2
      exit 3
    fi
    ts="$(date -u +%Y-%m-%dT%H:%M:%S)"
    echo "$name | $ts" > "$FLAG_FILE"
    echo "switched to: $name | $ts"
    ;;
  stale)
    if [[ ! -f "$FLAG_FILE" ]]; then
      exit 0  # stale = prompt needed
    fi
    ts="$(cut -d'|' -f2 "$FLAG_FILE" | tr -d ' ')"
    # Convert ISO to epoch, compare to now
    now="$(date +%s)"
    if flag_epoch="$(date -j -f "%Y-%m-%dT%H:%M:%S" "$ts" +%s 2>/dev/null)"; then
      age=$((now - flag_epoch))
      if [[ $age -gt 43200 ]]; then  # 12 hours
        exit 0  # stale
      fi
    else
      exit 0  # parse fail = stale
    fi
    exit 1  # fresh
    ;;
  validate)
    name="$(bash "$0" get)"
    if [[ -z "$name" || ! -d "$PROFILES_DIR/$name" ]]; then
      echo "INVALID: profile '$name' not in $PROFILES_DIR" >&2
      exit 1
    fi
    echo "OK: $name"
    ;;
  *)
    echo "Usage: profile.sh {show|get|set <name>|stale|validate}" >&2
    exit 2
    ;;
esac
