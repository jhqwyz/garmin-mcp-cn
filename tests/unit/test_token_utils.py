"""Native token detection, legacy migration errors and narrow token removal."""
from unittest.mock import Mock
import pytest
from garmin_mcp import token_utils


@pytest.fixture(autouse=True)
def isolated_environment(monkeypatch):
    monkeypatch.delenv("GARMIN_IS_CN", raising=False)
    monkeypatch.delenv("GARMINTOKENS", raising=False)


def test_regions_use_separate_default_stores(monkeypatch):
    assert token_utils.get_token_path() == "~/.garminconnect"
    monkeypatch.setenv("GARMIN_IS_CN", "true")
    assert token_utils.get_token_path() == "~/.garminconnect-cn"
    monkeypatch.setenv("GARMINTOKENS", "/custom")
    assert token_utils.get_token_path() == "/custom"


def test_an_empty_directory_is_not_a_saved_session(tmp_path):
    assert not token_utils.token_exists(str(tmp_path))
    (tmp_path / "garmin_tokens.json").write_text("{}")
    assert token_utils.token_exists(str(tmp_path))


def test_explicit_json_file_is_supported(tmp_path):
    saved = tmp_path / "custom.json"
    saved.write_text("{}")
    assert token_utils.token_exists(str(saved))


def test_legacy_tokens_require_fresh_login(tmp_path):
    (tmp_path / "oauth1_token.json").write_text("{}")
    assert not token_utils.token_exists(str(tmp_path))
    valid, error = token_utils.validate_tokens(str(tmp_path))
    assert not valid
    assert "Garth" in error and "Sign in again" in error


def test_china_region_is_used_when_resuming_tokens(monkeypatch, tmp_path):
    (tmp_path / "garmin_tokens.json").write_text("{}")
    monkeypatch.setenv("GARMIN_IS_CN", "true")
    instance = Mock(spec=["login", "get_full_name"])
    constructor = Mock(return_value=instance)
    monkeypatch.setattr(token_utils, "Garmin", constructor)
    assert token_utils.validate_tokens(str(tmp_path)) == (True, "")
    constructor.assert_called_once_with(is_cn=True)
    instance.login.assert_called_once_with(str(tmp_path))


def test_remove_tokens_preserves_other_files(tmp_path):
    (tmp_path / "garmin_tokens.json").write_text("{}")
    notes = tmp_path / "notes.txt"
    notes.write_text("keep this")
    token_utils.remove_tokens(str(tmp_path))
    assert notes.read_text() == "keep this"
    assert not (tmp_path / "garmin_tokens.json").exists()


def test_remove_tokens_refuses_symlinks(tmp_path):
    outside = tmp_path / "outside.json"
    outside.write_text("keep this")
    saved = tmp_path / "garmin_tokens.json"
    saved.symlink_to(outside)
    with pytest.raises(ValueError, match="symlink"):
        token_utils.remove_tokens(str(tmp_path))
    assert outside.read_text() == "keep this"
