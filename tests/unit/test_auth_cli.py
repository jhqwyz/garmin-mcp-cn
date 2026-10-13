"""Native authentication, region selection and safe credential persistence."""
from pathlib import Path
from unittest.mock import Mock
import pytest
from garminconnect import GarminConnectAuthenticationError
from garmin_mcp import auth_cli


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    for key in ("GARMIN_EMAIL", "GARMIN_EMAIL_FILE", "GARMIN_PASSWORD", "GARMIN_PASSWORD_FILE", "GARMIN_IS_CN", "GARMINTOKENS"):
        monkeypatch.delenv(key, raising=False)


def native_client(monkeypatch):
    instance = Mock(spec=["login", "get_full_name", "client"])
    instance.client = Mock(spec=["dump"])
    constructor = Mock(return_value=instance)
    monkeypatch.setattr(auth_cli, "Garmin", constructor)
    monkeypatch.setattr(auth_cli, "get_credentials", lambda: ("test@example.com", "synthetic-password"))
    return instance, constructor


def test_authenticate_uses_native_store_and_china_region(monkeypatch, tmp_path):
    monkeypatch.setenv("GARMIN_IS_CN", "true")
    monkeypatch.setenv("GARMINTOKENS", str(tmp_path))
    instance, constructor = native_client(monkeypatch)
    assert auth_cli.authenticate(str(tmp_path), force_reauth=True)
    assert constructor.call_args.kwargs["is_cn"] is True
    login_path = instance.login.call_args.args[0]
    assert login_path != str(tmp_path)
    assert not Path(login_path).exists()
    instance.client.dump.assert_called_once_with(str(tmp_path))
    instance.get_full_name.assert_called_once()


def test_failed_reauthentication_preserves_current_tokens(monkeypatch, tmp_path, capsys):
    saved = tmp_path / "garmin_tokens.json"
    saved.write_text("existing synthetic token")
    instance, _ = native_client(monkeypatch)
    instance.login.side_effect = GarminConnectAuthenticationError("synthetic-sensitive-value")
    assert not auth_cli.authenticate(str(tmp_path), force_reauth=True)
    assert saved.read_text() == "existing synthetic token"
    instance.client.dump.assert_not_called()
    captured = capsys.readouterr()
    assert "synthetic-sensitive-value" not in captured.out + captured.err


def test_valid_session_avoids_credential_prompt(monkeypatch, tmp_path):
    monkeypatch.setattr(auth_cli, "token_exists", lambda _: True)
    monkeypatch.setattr(auth_cli, "validate_tokens", lambda _: (True, ""))
    credentials = Mock()
    monkeypatch.setattr(auth_cli, "get_credentials", credentials)
    assert auth_cli.authenticate(str(tmp_path))
    credentials.assert_not_called()


def test_profile_failure_does_not_save_a_partial_session(monkeypatch, tmp_path):
    instance, _ = native_client(monkeypatch)
    instance.get_full_name.side_effect = RuntimeError("synthetic profile failure")
    assert not auth_cli.authenticate(str(tmp_path))
    instance.client.dump.assert_not_called()


def test_credentials_are_collected_interactively(monkeypatch):
    monkeypatch.setattr("builtins.input", lambda _: "test@example.com")
    monkeypatch.setattr(auth_cli.getpass, "getpass", lambda _: "synthetic-password")
    assert auth_cli.get_credentials() == ("test@example.com", "synthetic-password")


def test_conflicting_credential_sources_are_rejected(monkeypatch):
    monkeypatch.setenv("GARMIN_EMAIL", "test@example.com")
    monkeypatch.setenv("GARMIN_EMAIL_FILE", "/unused")
    with pytest.raises(ValueError, match="Must only provide one"):
        auth_cli.get_credentials()


def test_china_cli_selects_region_before_authentication(monkeypatch, tmp_path):
    monkeypatch.setattr("sys.argv", ["garmin-mcp-auth", "--china", "--token-path", str(tmp_path)])
    authenticate = Mock(return_value=True)
    monkeypatch.setattr(auth_cli, "authenticate", authenticate)
    with pytest.raises(SystemExit) as exit_info:
        auth_cli.main()
    assert exit_info.value.code == 0
    assert auth_cli.is_china()
    authenticate.assert_called_once_with(str(tmp_path), False)
