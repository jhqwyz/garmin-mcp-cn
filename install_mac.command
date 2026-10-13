#!/bin/bash
set -euo pipefail
GARMIN_PROJECT_DIR="$(cd -- "$(dirname -- "$0")" && pwd)"
cd "$GARMIN_PROJECT_DIR"
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "This launcher is for macOS. See README.md for Linux."
  exit 1
fi
if ! command -v uv >/dev/null 2>&1; then
  GARMIN_UV_INSTALLER="$(mktemp -t garmin-uv-install)"
  trap 'rm -f "$GARMIN_UV_INSTALLER"' EXIT
  curl --proto '=https' --tlsv1.2 -LsSf https://astral.sh/uv/install.sh -o "$GARMIN_UV_INSTALLER"
  sh "$GARMIN_UV_INSTALLER"
  export PATH="$HOME/.local/bin:$PATH"
fi
uv sync --locked --no-dev
uv run --no-dev python scripts/install_tunnel_client.py
uv run --no-dev garmin-mcp-auth --china
printf '\n在 OpenAI Platform 创建关联当前 ChatGPT 工作区的 MCP Tunnel。\n'
printf '官方说明：https://developers.openai.com/api/docs/guides/secure-mcp-tunnels\n'
read -r -p "Tunnel ID: " GARMIN_TUNNEL_ID
if [[ -z "$GARMIN_TUNNEL_ID" ]]; then
  echo "安装和佳明认证已完成。创建 Tunnel 后运行 start_web.command。"
  exit 0
fi
uv run --no-dev garmin-mcp-web setup --china --tunnel-id "$GARMIN_TUNNEL_ID" --tunnel-client "$GARMIN_PROJECT_DIR/.bin/tunnel-client"
