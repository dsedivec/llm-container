from __future__ import annotations

from pathlib import Path

from click.testing import CliRunner

from llmbox import cli


def test_proxy_reload_warns_when_no_containers(tmp_path: Path, monkeypatch) -> None:
    config_base = tmp_path / "config"
    state_base = tmp_path / "state"
    env = {
        "XDG_CONFIG_HOME": str(config_base),
        "XDG_STATE_HOME": str(state_base),
    }
    runner = CliRunner()

    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_base))
    monkeypatch.setenv("XDG_STATE_HOME", str(state_base))
    monkeypatch.setattr(cli, "reload_proxy", lambda profile: ([], []))

    result = runner.invoke(cli.cli, ["proxy", "reload", "dev"], env=env)
    assert result.exit_code == 0
    assert "Warning: no running containers" in result.output
