#!/usr/bin/env bash
# Refresh usage-stats.json and push it into the running open-webui container.
# Use this instead of a writable bind mount if you prefer.
set -euo pipefail
cd "$(dirname "$0")/.."

python3 collector/usage-collector.py

if docker ps --format '{{.Names}}' | grep -qx open-webui; then
  docker cp stats/usage-stats.json open-webui:/app/backend/open_webui/static/usage/usage-stats.json
fi
