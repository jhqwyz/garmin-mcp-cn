"""Credential-free process fixture used only by MCP transport tests."""
import argparse
from unittest.mock import Mock
from garmin_mcp.server import create_app


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--transport", default="stdio")
    args = parser.parse_args()
    client = Mock()
    client.get_sleep_data.return_value = {"dailySleepDTO": {"sleepTimeSeconds": 28800}}
    create_app(client).run(transport=args.transport)


if __name__ == "__main__":
    main()
