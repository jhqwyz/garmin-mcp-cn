"""Read-only MCP server with native Garmin authentication."""
import argparse
import os
import sys
from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations
from garminconnect import Garmin
from garmin_mcp.config import is_china, read_secret, auth_error_message
from garmin_mcp.token_utils import get_token_path
from garmin_mcp.read_only import READ_ONLY_TOOLS
from garmin_mcp import (
    activity_management, health_wellness, user_profile, devices,
    gear_management, weight_management, challenges, training,
    workouts, workout_templates, data_management, womens_health,
)

MODULES = (
    activity_management, health_wellness, user_profile, devices,
    gear_management, weight_management, challenges, training,
    workouts, data_management, womens_health,
)


class ReadOnlyRegistrar:
    """Expose only reviewed read tools, without modifying inherited modules."""
    def __init__(self, app: FastMCP):
        self.app = app

    def tool(self, *args, **kwargs):
        def register(function):
            if function.__name__ not in READ_ONLY_TOOLS:
                return function
            options = dict(kwargs)
            # Existing tools return JSON text; do not wrap it in a second schema.
            options.setdefault("structured_output", False)
            options["annotations"] = ToolAnnotations(
                readOnlyHint=True, destructiveHint=False,
                idempotentHint=True, openWorldHint=True,
            )
            return self.app.tool(*args, **options)(function)
        return register


def get_mfa() -> str:
    raise RuntimeError("Run garmin-mcp-auth interactively before starting the server")


def init_api(email=None, password=None, token_path: str | None = None):
    try:
        client = Garmin(
            email=email, password=password, is_cn=is_china(), prompt_mfa=get_mfa,
        )
        client.login(token_path or get_token_path())
        return client
    except Exception as error:
        print(auth_error_message(error), file=sys.stderr)
        print("Run garmin-mcp-auth --china for a China account.", file=sys.stderr)
        return None


def create_app(client, *, host="127.0.0.1", port=8000) -> FastMCP:
    app = FastMCP(
        "Garmin Connect China (read-only)",
        instructions=(
            "Read-only Garmin data access. First identify the requested dates and metrics. "
            "Prefer summary tools for trends, and detailed data when needed. Missing records "
            "and failed queries are unavailable data, not zero. Sleep timestamps ending GMT "
            "are UTC; convert to the user's timezone, usually Asia/Shanghai for China accounts. "
            "Separate recorded measurements, Garmin estimates and your own inferences. "
            "Read data only for the dates and purposes requested by the user."
        ),
        host=host, port=port, stateless_http=True, json_response=True,
    )
    registrar = ReadOnlyRegistrar(app)
    for module in MODULES:
        module.configure(client)
        module.register_tools(registrar)
    workout_templates.register_resources(app)
    return app


def main():
    parser = argparse.ArgumentParser(description="Read-only Garmin MCP server")
    parser.add_argument("--transport", choices=("stdio", "streamable-http"), default="stdio")
    parser.add_argument("--host", choices=("127.0.0.1", "::1"), default="127.0.0.1", help="Loopback only; use Secure MCP Tunnel for ChatGPT web")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--token-path")
    region = parser.add_mutually_exclusive_group()
    region.add_argument("--china", action="store_true")
    region.add_argument("--global", dest="global_region", action="store_true")
    args = parser.parse_args()
    if args.china:
        os.environ["GARMIN_IS_CN"] = "true"
    elif args.global_region:
        os.environ["GARMIN_IS_CN"] = "false"
    if not 1 <= args.port <= 65535:
        parser.error("Port must be between 1 and 65535")
    client = init_api(
        read_secret("GARMIN_EMAIL"), read_secret("GARMIN_PASSWORD"), args.token_path,
    )
    if client is None:
        raise SystemExit(1)
    app = create_app(client, host=args.host, port=args.port)
    app.run(transport=args.transport)
