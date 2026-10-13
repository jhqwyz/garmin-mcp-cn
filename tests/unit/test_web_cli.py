"""Tunnel secrets stay in the process environment and never enter argv/config."""
from unittest.mock import Mock
import pytest
from garmin_mcp import web_cli


def test_tunnel_environment_does_not_forward_garmin_password(monkeypatch):
    monkeypatch.setenv("CONTROL_PLANE_API_KEY", "synthetic-api-key")
    monkeypatch.setenv("GARMIN_PASSWORD", "synthetic-password")
    monkeypatch.setenv("GARMIN_PASSWORD_FILE", "/unused")
    env = web_cli.tunnel_environment()
    assert env["CONTROL_PLANE_API_KEY"] == "synthetic-api-key"
    assert "GARMIN_PASSWORD" not in env and "GARMIN_PASSWORD_FILE" not in env


def test_setup_configures_checks_then_runs_with_one_key(monkeypatch):
    monkeypatch.setenv("CONTROL_PLANE_API_KEY", "synthetic-api-key")
    monkeypatch.setattr("sys.argv", ["garmin-mcp-web", "setup", "--china", "--tunnel-id", "tunnel_test", "--tunnel-client", "/fake/tunnel-client"])
    monkeypatch.setattr(web_cli, "validate_tokens", lambda _: (True, ""))
    run = Mock(return_value=Mock(returncode=0))
    monkeypatch.setattr(web_cli.subprocess, "run", run)
    with pytest.raises(SystemExit) as exit_info:
        web_cli.main()
    assert exit_info.value.code == 0
    assert [call.args[0][1] for call in run.call_args_list] == ["init", "doctor", "run"]
    for call in run.call_args_list:
        assert "synthetic-api-key" not in " ".join(call.args[0])
        assert call.kwargs["env"]["CONTROL_PLANE_API_KEY"] == "synthetic-api-key"
    init_command = run.call_args_list[0].args[0]
    assert "--china" in init_command[init_command.index("--mcp-command") + 1]


def test_failed_diagnostic_does_not_start_the_tunnel(monkeypatch):
    monkeypatch.setenv("CONTROL_PLANE_API_KEY", "synthetic-api-key")
    monkeypatch.setattr("sys.argv", ["garmin-mcp-web", "setup", "--tunnel-id", "tunnel_test", "--tunnel-client", "/fake/client"])
    monkeypatch.setattr(web_cli, "validate_tokens", lambda _: (True, ""))
    run = Mock(side_effect=[Mock(returncode=0), Mock(returncode=1)])
    monkeypatch.setattr(web_cli.subprocess, "run", run)
    with pytest.raises(SystemExit) as exit_info:
        web_cli.main()
    assert exit_info.value.code == 1
    assert run.call_count == 2
