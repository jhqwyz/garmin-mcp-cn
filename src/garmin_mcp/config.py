"""Shared region and credential handling; never log secret values."""
import os
from pathlib import Path


def is_china() -> bool:
    value = os.getenv("GARMIN_IS_CN", "false").strip().lower()
    if value not in {"true", "1", "yes", "false", "0", "no", ""}:
        raise ValueError("GARMIN_IS_CN must be true or false")
    return value in {"true", "1", "yes"}


def read_secret(name: str) -> str | None:
    value = os.getenv(name)
    filename = os.getenv(f"{name}_FILE")
    if value and filename:
        raise ValueError(f"Must only provide one of {name} and {name}_FILE")
    if filename:
        return Path(filename).expanduser().read_text().rstrip()
    return value or None


def auth_error_message(error: Exception) -> str:
    """Map errors to actionable text without copying response bodies or tokens."""
    from garminconnect import (
        GarminConnectAuthenticationError,
        GarminConnectConnectionError,
        GarminConnectTooManyRequestsError,
    )
    if isinstance(error, GarminConnectTooManyRequestsError):
        return "Garmin rejected the login request (429). Stop retrying and try later."
    if isinstance(error, GarminConnectAuthenticationError):
        return "Garmin authentication failed. Check the account region, credentials and verification code."
    if isinstance(error, FileNotFoundError):
        return "Saved credentials were not found. Run garmin-mcp-auth first."
    if isinstance(error, GarminConnectConnectionError):
        return "Could not connect or authenticate to Garmin. Check connectivity, region and saved credentials."
    return "Authentication failed. Run garmin-mcp-auth interactively to sign in again."
