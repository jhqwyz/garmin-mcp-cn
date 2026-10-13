#!/bin/bash
set -euo pipefail
GARMIN_PROJECT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
cd "$GARMIN_PROJECT_DIR"
export PATH="$HOME/.local/bin:$PATH"
uv run --no-dev garmin-mcp-web run --china --tunnel-client "$GARMIN_PROJECT_DIR/.bin/tunnel-client"
