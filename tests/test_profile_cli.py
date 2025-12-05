from __future__ import annotations

from pathlib import Path

import yaml
from click.testing import CliRunner

from llmbox import cli


def test_profile_create_dash_creates_default(tmp_path: Path, monkeypatch) -> None:
    config_base = tmp_path / "config"
    state_base = tmp_path / "state"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_base))
    monkeypatch.setenv("XDG_STATE_HOME", str(state_base))

    runner = CliRunner()
    result = runner.invoke(cli.cli, ["profile", "create", "-"])
    assert result.exit_code == 0
    assert "Created profile default" in result.output

    profile_file = config_base / "llmbox" / "profiles" / "default.yaml"
    assert profile_file.exists()
    state = yaml.safe_load((state_base / "llmbox" / "state.yaml").read_text())
    assert state["default_profile"] == "default"


def test_profile_create_dash_errors_if_default_exists(tmp_path: Path, monkeypatch) -> None:
    config_base = tmp_path / "config"
    state_base = tmp_path / "state"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_base))
    monkeypatch.setenv("XDG_STATE_HOME", str(state_base))

    runner = CliRunner()
    runner.invoke(cli.cli, ["profile", "create", "default"])
    result = runner.invoke(cli.cli, ["profile", "create", "-"])
    assert result.exit_code != 0
    assert "already exists" in result.output


def test_profile_create_sets_default_and_prints(tmp_path: Path, monkeypatch) -> None:
    config_base = tmp_path / "config"
    state_base = tmp_path / "state"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_base))
    monkeypatch.setenv("XDG_STATE_HOME", str(state_base))

    runner = CliRunner()
    first = runner.invoke(cli.cli, ["profile", "create", "alpha"])
    assert first.exit_code == 0
    assert "Created profile alpha" in first.output
    second = runner.invoke(cli.cli, ["profile", "create", "beta"])
    assert second.exit_code == 0
    state = yaml.safe_load((state_base / "llmbox" / "state.yaml").read_text())
    assert state["default_profile"] == "beta"


def test_profile_delete_reassigns_default(tmp_path: Path, monkeypatch) -> None:
    config_base = tmp_path / "config"
    state_base = tmp_path / "state"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_base))
    monkeypatch.setenv("XDG_STATE_HOME", str(state_base))

    runner = CliRunner()
    for name in ("alpha", "beta", "default"):
        runner.invoke(cli.cli, ["profile", "create", name])

    delete_result = runner.invoke(cli.cli, ["profile", "delete", "default"])
    assert delete_result.exit_code == 0
    assert "new default profile is: alpha" in delete_result.output
    state = yaml.safe_load((state_base / "llmbox" / "state.yaml").read_text())
    assert state["default_profile"] == "alpha"


def test_profile_rename_preserves_default(tmp_path: Path, monkeypatch) -> None:
    config_base = tmp_path / "config"
    state_base = tmp_path / "state"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_base))
    monkeypatch.setenv("XDG_STATE_HOME", str(state_base))

    runner = CliRunner()
    runner.invoke(cli.cli, ["profile", "create", "alpha"])
    rename_result = runner.invoke(cli.cli, ["profile", "rename", "alpha", "beta"])
    assert rename_result.exit_code == 0
    state = yaml.safe_load((state_base / "llmbox" / "state.yaml").read_text())
    assert state["default_profile"] == "beta"


def test_profile_set_default_by_number(tmp_path: Path, monkeypatch) -> None:
    config_base = tmp_path / "config"
    state_base = tmp_path / "state"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_base))
    monkeypatch.setenv("XDG_STATE_HOME", str(state_base))

    runner = CliRunner()
    runner.invoke(cli.cli, ["profile", "create", "alpha"])
    runner.invoke(cli.cli, ["profile", "create", "beta"])

    result = runner.invoke(cli.cli, ["profile", "set-default", "2"])
    assert result.exit_code == 0
    assert "Default profile set to beta" in result.output
    state = yaml.safe_load((state_base / "llmbox" / "state.yaml").read_text())
    assert state["default_profile"] == "beta"
