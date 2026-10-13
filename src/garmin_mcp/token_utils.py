"""Native garminconnect 0.3 session storage. Legacy tokens are never converted."""
import os
from pathlib import Path
from garminconnect import Garmin
from garmin_mcp.config import is_china, auth_error_message

TOKEN_FILENAME = "garmin_tokens.json"


def get_token_path() -> str:
    return os.getenv("GARMINTOKENS") or (
        "~/.garminconnect-cn" if is_china() else "~/.garminconnect"
    )


def token_file(token_path: str | None = None) -> Path:
    path = Path(token_path or get_token_path()).expanduser()
    return path if path.suffix.lower() == ".json" else path / TOKEN_FILENAME


def token_exists(token_path: str | None = None) -> bool:
    return token_file(token_path).is_file()


def has_legacy_tokens(token_path: str | None = None) -> bool:
    path = Path(token_path or get_token_path()).expanduser()
    return path.is_dir() and any(
        (path / name).is_file()
        for name in ("oauth1_token.json", "oauth2_token.json")
    )


def validate_tokens(token_path: str | None = None) -> tuple[bool, str]:
    path = token_path or get_token_path()
    if not token_exists(path):
        if has_legacy_tokens(path):
            return False, "Old Garth credentials are not supported. Sign in again with garmin-mcp-auth."
        return False, "Native credentials not found. Run garmin-mcp-auth first."
    try:
        # Region is not stored in native token JSON: always select it explicitly.
        garmin = Garmin(is_cn=is_china())
        garmin.login(path)
        garmin.get_full_name()
        return True, ""
    except Exception as error:
        return False, auth_error_message(error)


def remove_tokens(token_path: str | None = None) -> None:
    """Remove only this client's native token file, preserving unrelated files."""
    path = token_file(token_path)
    if path.is_symlink():
        raise ValueError("Refusing a symlinked credential file")
    path.unlink(missing_ok=True)


def get_token_info(token_path: str | None = None) -> dict:
    path = token_path or get_token_path()
    exists = token_exists(path)
    valid, error = validate_tokens(path) if exists else (False, "")
    return {
        "path": path,
        "expanded_path": os.path.expanduser(path),
        "exists": exists,
        "valid": valid,
        "error": error,
        "legacy": has_legacy_tokens(path),
        "region": "china" if is_china() else "global",
    }
