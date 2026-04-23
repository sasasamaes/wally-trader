#!/usr/bin/env bash
# load_env.sh — source .claude/.env if present. Silent if missing.
ENV_FILE="$(dirname "$0")/../.env"
if [ -f "$ENV_FILE" ]; then
  set -a
  source "$ENV_FILE"
  set +a
fi
