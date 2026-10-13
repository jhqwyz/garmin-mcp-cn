"""Interactive native Garmin login, independent of ChatGPT and its credentials."""
import argparse
import getpass
import os
import sys
import tempfile
from garminconnect import Garmin
from garmin_mcp.config import is_china, read_secret, auth_error_message
from garmin_mcp.token_utils import (
    get_token_path, token_exists, validate_tokens, has_legacy_tokens,
)


def get_mfa() -> str:
    print("Garmin requires a verification code. Check the method configured on your account.")
    return getpass.getpass("Verification code: ")


def get_credentials() -> tuple[str, str]:
    email = read_secret("GARMIN_EMAIL")
    password = read_secret("GARMIN_PASSWORD")
    if not email:
        email = input("Garmin account email: ").strip()
    if not email:
        raise ValueError("Email is required")
    if not password:
        password = getpass.getpass("Garmin password: ")
    if not password:
        raise ValueError("Password is required")
    return email, password


def authenticate(token_path: str, force_reauth: bool = False) -> bool:
    if not force_reauth and token_exists(token_path):
        valid, _ = validate_tokens(token_path)
        if valid:
            print("Saved credentials are valid; no new login needed.")
            return True
    if has_legacy_tokens(token_path):
        print("Old Garth credentials cannot be migrated; a fresh login is required.")
    try:
        email, password = get_credentials()
        garmin = Garmin(
            email=email, password=password, is_cn=is_china(), prompt_mfa=get_mfa,
        )
        # Authenticate against an empty store even when GARMINTOKENS is set.
        # Keep any working old session intact until the new login succeeds.
        with tempfile.TemporaryDirectory(prefix="garmin-mcp-auth-") as temporary_store:
            garmin.login(temporary_store)
            garmin.get_full_name()
            garmin.client.dump(token_path)
        print(f"Signed in to Garmin {'China' if is_china() else 'Global'}.")
        print(f"Credentials saved to {os.path.expanduser(token_path)} (native format).")
        return True
    except (EOFError, KeyboardInterrupt):
        print("Sign-in cancelled.", file=sys.stderr)
        return False
    except ValueError:
        print("Check the account email, password and credential settings.", file=sys.stderr)
        return False
    except Exception as error:
        print(auth_error_message(error), file=sys.stderr)
        return False


def verify_tokens(token_path: str) -> bool:
    valid, error = validate_tokens(token_path)
    print("Saved credentials are valid." if valid else error)
    return valid


def main():
    parser = argparse.ArgumentParser(description="Sign in locally to Garmin and save native credentials")
    parser.add_argument("--token-path", help="Native credential directory or JSON file")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--force-reauth", action="store_true")
    region = parser.add_mutually_exclusive_group()
    region.add_argument("--china", action="store_true", help="Use the garmin.cn account region")
    region.add_argument("--global", dest="global_region", action="store_true")
    args = parser.parse_args()
    if args.china:
        os.environ["GARMIN_IS_CN"] = "true"
    elif args.global_region:
        os.environ["GARMIN_IS_CN"] = "false"
    path = args.token_path or get_token_path()
    success = verify_tokens(path) if args.verify else authenticate(path, args.force_reauth)
    raise SystemExit(0 if success else 1)


if __name__ == "__main__":
    main()
