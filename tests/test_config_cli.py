from __future__ import annotations

from pathlib import Path

import yaml
from click.testing import CliRunner

from llmbox import cli


def test_config_persist_dir_set_global(tmp_path: Path, monkeypatch) -> None:
    config_base = tmp_path / "config"
    state_base = tmp_path / "state"
    env = {
        "XDG_CONFIG_HOME": str(config_base),
        "XDG_STATE_HOME": str(state_base),
    }
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_base))
    monkeypatch.setenv("XDG_STATE_HOME", str(state_base))

    runner = CliRunner()
    result = runner.invoke(cli.cli, ["config", "persist-dir", "--global", "~/my_persist"], env=env)
    assert result.exit_code == 0
    assert "Global persist-dir set to ~/my_persist" in result.output

    # Verify it was saved
    cfg = yaml.safe_load((config_base / "llmbox" / "config.yaml").read_text())
    assert cfg["persist_dir"] == "~/my_persist"


def test_config_persist_dir_show_global(tmp_path: Path, monkeypatch) -> None:
    config_base = tmp_path / "config"
    state_base = tmp_path / "state"
    env = {
        "XDG_CONFIG_HOME": str(config_base),
        "XDG_STATE_HOME": str(state_base),
    }
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_base))
    monkeypatch.setenv("XDG_STATE_HOME", str(state_base))

    runner = CliRunner()
    # Show when not set
    result = runner.invoke(cli.cli, ["config", "persist-dir", "--global"], env=env)
    assert result.exit_code == 0
    assert "(not set)" in result.output

    # Set and show
    runner.invoke(cli.cli, ["config", "persist-dir", "--global", "/tmp/p"], env=env)
    result = runner.invoke(cli.cli, ["config", "persist-dir", "--global"], env=env)
    assert result.exit_code == 0
    assert "/tmp/p" in result.output


def test_config_persist_dir_clear_global(tmp_path: Path, monkeypatch) -> None:
    config_base = tmp_path / "config"
    state_base = tmp_path / "state"
    env = {
        "XDG_CONFIG_HOME": str(config_base),
        "XDG_STATE_HOME": str(state_base),
    }
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_base))
    monkeypatch.setenv("XDG_STATE_HOME", str(state_base))

    runner = CliRunner()
    runner.invoke(cli.cli, ["config", "persist-dir", "--global", "/tmp/p"], env=env)
    result = runner.invoke(cli.cli, ["config", "persist-dir", "--global", "--clear"], env=env)
    assert result.exit_code == 0
    assert "Cleared global persist-dir" in result.output

    cfg = yaml.safe_load((config_base / "llmbox" / "config.yaml").read_text())
    assert cfg["persist_dir"] is None


def test_config_persist_dir_set_profile(tmp_path: Path, monkeypatch) -> None:
    config_base = tmp_path / "config"
    state_base = tmp_path / "state"
    env = {
        "XDG_CONFIG_HOME": str(config_base),
        "XDG_STATE_HOME": str(state_base),
    }
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_base))
    monkeypatch.setenv("XDG_STATE_HOME", str(state_base))

    runner = CliRunner()
    runner.invoke(cli.cli, ["profile", "create", "dev"], env=env)

    result = runner.invoke(cli.cli, ["config", "persist-dir", "dev", "~/persist_dev"], env=env)
    assert result.exit_code == 0
    assert "persist-dir for profile dev set to ~/persist_dev" in result.output

    # Show
    result = runner.invoke(cli.cli, ["config", "persist-dir", "dev"], env=env)
    assert result.exit_code == 0
    assert "~/persist_dev" in result.output


def test_config_persist_dir_clear_profile(tmp_path: Path, monkeypatch) -> None:
    config_base = tmp_path / "config"
    state_base = tmp_path / "state"
    env = {
        "XDG_CONFIG_HOME": str(config_base),
        "XDG_STATE_HOME": str(state_base),
    }
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_base))
    monkeypatch.setenv("XDG_STATE_HOME", str(state_base))

    runner = CliRunner()
    runner.invoke(cli.cli, ["profile", "create", "dev"], env=env)
    runner.invoke(cli.cli, ["config", "persist-dir", "dev", "/tmp/x"], env=env)

    result = runner.invoke(cli.cli, ["config", "persist-dir", "dev", "--clear"], env=env)
    assert result.exit_code == 0
    assert "Cleared persist-dir for profile dev" in result.output

    result = runner.invoke(cli.cli, ["config", "persist-dir", "dev"], env=env)
    assert "(not set)" in result.output


def test_config_persist_dir_missing_profile_arg(tmp_path: Path, monkeypatch) -> None:
    config_base = tmp_path / "config"
    state_base = tmp_path / "state"
    env = {
        "XDG_CONFIG_HOME": str(config_base),
        "XDG_STATE_HOME": str(state_base),
    }
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_base))
    monkeypatch.setenv("XDG_STATE_HOME", str(state_base))

    runner = CliRunner()
    result = runner.invoke(cli.cli, ["config", "persist-dir"], env=env)
    assert result.exit_code != 0
    assert "Missing argument" in result.output
