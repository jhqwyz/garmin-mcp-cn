"""Connect a private Garmin stdio server through OpenAI's official tunnel client."""
import argparse
import getpass
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
from garmin_mcp.config import is_china
from garmin_mcp.token_utils import get_token_path, validate_tokens


def server_command(token_path: str, china: bool) -> str:
    return shlex.join([
        sys.executable, "-m", "garmin_mcp",
        "--china" if china else "--global",
        "--token-path", str(Path(token_path).expanduser()),
    ])


def tunnel_environment() -> dict[str, str]:
    env = os.environ.copy()
    key = env.get("CONTROL_PLANE_API_KEY") or env.get("OPENAI_API_KEY")
    if not key:
        key = getpass.getpass("OpenAI API key for the MCP tunnel (hidden): ").strip()
    if not key:
        raise ValueError("An OpenAI tunnel API key is required")
    env["CONTROL_PLANE_API_KEY"] = key
    # Garmin authentication is complete; the tunnel's MCP child uses saved tokens.
    for name in ("GARMIN_PASSWORD", "GARMIN_PASSWORD_FILE", "GARMIN_EMAIL", "GARMIN_EMAIL_FILE"):
        env.pop(name, None)
    return env


def main():
    parser = argparse.ArgumentParser(description="Use a private Garmin MCP server in ChatGPT web")
    parser.add_argument("command", choices=("setup", "configure", "run", "doctor"), nargs="?", default="run")
    parser.add_argument("--profile", default="garmin-cn")
    parser.add_argument("--tunnel-id", help="A tunnel associated with your ChatGPT workspace")
    parser.add_argument("--tunnel-client", help="Path to the official OpenAI tunnel-client binary")
    parser.add_argument("--token-path")
    region = parser.add_mutually_exclusive_group()
    region.add_argument("--china", action="store_true")
    region.add_argument("--global", dest="global_region", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", args.profile):
        parser.error("Profile must contain only letters, digits, dots, underscores and dashes")
    if args.command in {"setup", "configure"} and not args.tunnel_id:
        parser.error("setup/configure requires --tunnel-id")
    if args.china:
        os.environ["GARMIN_IS_CN"] = "true"
    elif args.global_region:
        os.environ["GARMIN_IS_CN"] = "false"
    else:
        os.environ.setdefault("GARMIN_IS_CN", "true")
    token_path = args.token_path or get_token_path()
    valid, error = validate_tokens(token_path)
    if not valid:
        print(error, file=sys.stderr)
        raise SystemExit(1)
    binary = args.tunnel_client or shutil.which("tunnel-client")
    if not binary:
        parser.error("Install the official openai/tunnel-client binary first; see README.md")
    try:
        env = tunnel_environment()
        if args.command in {"setup", "configure"}:
            command = [
                binary, "init", "--sample", "sample_mcp_stdio_local",
                "--profile", args.profile, "--tunnel-id", args.tunnel_id,
                "--health-listen-addr", "127.0.0.1:0",
                "--mcp-command", server_command(token_path, is_china()),
            ]
        elif args.command == "doctor":
            command = [binary, "doctor", "--profile", args.profile, "--explain"]
        else:
            command = [binary, "run", "--profile", args.profile]
        # The API key is passed only through the child environment, never argv/config.
        result = subprocess.run(command, env=env, check=False)
        if result.returncode or args.command != "setup":
            raise SystemExit(result.returncode)
        result = subprocess.run([binary, "doctor", "--profile", args.profile, "--explain"], env=env, check=False)
        if result.returncode:
            raise SystemExit(result.returncode)
        print("Keep this terminal and computer running while ChatGPT web uses Garmin.")
        result = subprocess.run([binary, "run", "--profile", args.profile], env=env, check=False)
        raise SystemExit(result.returncode)
    except (EOFError, KeyboardInterrupt):
        raise SystemExit(130)
    except (OSError, ValueError):
        print("Could not start the tunnel client. Check its path, API key and configuration.", file=sys.stderr)
        raise SystemExit(1)
