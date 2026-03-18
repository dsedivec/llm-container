from __future__ import annotations

import os
from pathlib import Path

import yaml
from click.testing import CliRunner

from llmbox.cli import cli
from llmbox.settings import config_file_path


def test_volume_add_creates_profile(tmp_path: Path, monkeypatch) -> None:
    config_base = tmp_path / "config"
    state_base = tmp_path / "state"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_base))
    monkeypatch.setenv("XDG_STATE_HOME", str(state_base))

    host_path = tmp_path / "repo"
    host_path.mkdir()

    runner = CliRunner()
    result = runner.invoke(cli, ["volume", "add", "dev", str(host_path)])
    assert result.exit_code == 0
    assert "Creating profile dev" in result.output

    profile_file = config_base / "llmbox" / "profiles" / "dev.yaml"
    assert profile_file.exists()
    saved = yaml.safe_load(profile_file.read_text())
    assert saved["volumes"][0].startswith(str(host_path))

    list_result = runner.invoke(cli, ["volume", "list", "dev"])
    assert list_result.exit_code == 0
    assert str(host_path) in list_result.output


def test_volume_remove_by_number_keeps_original_order(tmp_path: Path, monkeypatch) -> None:
    config_base = tmp_path / "config"
    state_base = tmp_path / "state"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_base))
    monkeypatch.setenv("XDG_STATE_HOME", str(state_base))

    first = tmp_path / "first"
    second = tmp_path / "second"
    third = tmp_path / "third"
    for path in (first, second, third):
        path.mkdir()

    runner = CliRunner()
    runner.invoke(cli, ["volume", "add", "dev", str(first), str(second), str(third)])
    delete_result = runner.invoke(cli, ["volume", "remove", "dev", "1", "3"])
    assert delete_result.exit_code == 0

    list_result = runner.invoke(cli, ["volume", "list", "dev"])
    assert list_result.exit_code == 0
    output = list_result.output.strip().splitlines()
    assert len(output) == 1
    assert str(second) in output[0]


def test_volume_add_preserves_symlinks_in_container_path(tmp_path: Path, monkeypatch) -> None:
    config_base = tmp_path / "config"
    state_base = tmp_path / "state"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_base))
    monkeypatch.setenv("XDG_STATE_HOME", str(state_base))

    # Create a symlink structure to simulate the Mac environment
    real_home = tmp_path / "real_home"
    real_home.mkdir()

    link_home = tmp_path / "link_home"
    os.symlink(real_home, link_home)

    workspace_root = link_home / "workspace"

    # Monkeypatch WORKSPACE_ROOT in llmbox.volumes
    monkeypatch.setattr("llmbox.volumes.WORKSPACE_ROOT", workspace_root)

    host_path = tmp_path / "repo"
    host_path.mkdir()

    runner = CliRunner()
    # Add volume without explicit container path
    result = runner.invoke(cli, ["volume", "add", "dev", str(host_path)])
    assert result.exit_code == 0

    # Check the saved profile
    profile_file = config_base / "llmbox" / "profiles" / "dev.yaml"
    assert profile_file.exists()
    saved = yaml.safe_load(profile_file.read_text())
    volume_spec = saved["volumes"][0]
    host_part, container_part = volume_spec.split(":")

    # The container part should start with the symlinked path (link_home)
    # If the bug was present, it would resolve to real_home
    assert container_part.startswith(str(link_home))
    assert not container_part.startswith(str(real_home))


def test_global_volume_add_and_list(tmp_path: Path, monkeypatch) -> None:
    config_base = tmp_path / "config"
    state_base = tmp_path / "state"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_base))
    monkeypatch.setenv("XDG_STATE_HOME", str(state_base))

    host_path = tmp_path / "dotclaude"
    host_path.mkdir()

    runner = CliRunner()
    result = runner.invoke(cli, ["volume", "add", "--global", f"{host_path}:/home/llm/.claude"])
    assert result.exit_code == 0

    list_result = runner.invoke(cli, ["volume", "list", "--global"])
    assert list_result.exit_code == 0
    assert str(host_path) in list_result.output
    assert "/home/llm/.claude" in list_result.output

    # Verify config.yaml on disk
    cfg = yaml.safe_load(config_file_path(config_base / "llmbox").read_text())
    assert len(cfg["volumes"]) == 1


def test_global_volume_remove(tmp_path: Path, monkeypatch) -> None:
    config_base = tmp_path / "config"
    state_base = tmp_path / "state"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_base))
    monkeypatch.setenv("XDG_STATE_HOME", str(state_base))

    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()

    runner = CliRunner()
    runner.invoke(
        cli,
        ["volume", "add", "--global", f"{first}:/home/llm/.first", f"{second}:/home/llm/.second"],
    )

    # Remove first by spec
    result = runner.invoke(cli, ["volume", "remove", "--global", f"{first}:/home/llm/.first"])
    assert result.exit_code == 0

    list_result = runner.invoke(cli, ["volume", "list", "--global"])
    assert str(first) not in list_result.output
    assert str(second) in list_result.output


def test_global_volume_remove_by_number(tmp_path: Path, monkeypatch) -> None:
    config_base = tmp_path / "config"
    state_base = tmp_path / "state"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_base))
    monkeypatch.setenv("XDG_STATE_HOME", str(state_base))

    host = tmp_path / "repo"
    host.mkdir()

    runner = CliRunner()
    runner.invoke(cli, ["volume", "add", "--global", f"{host}:/home/llm/.repo"])

    result = runner.invoke(cli, ["volume", "remove", "--global", "1"])
    assert result.exit_code == 0

    list_result = runner.invoke(cli, ["volume", "list", "--global"])
    assert list_result.output.strip() == ""


def test_volume_add_tilde_in_container_path(tmp_path: Path, monkeypatch) -> None:
    config_base = tmp_path / "config"
    state_base = tmp_path / "state"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_base))
    monkeypatch.setenv("XDG_STATE_HOME", str(state_base))

    host_path = tmp_path / ".claude"
    host_path.mkdir()

    runner = CliRunner()
    result = runner.invoke(cli, ["volume", "add", "dev", f"{host_path}:~/.claude"])
    assert result.exit_code == 0

    profile_file = config_base / "llmbox" / "profiles" / "dev.yaml"
    saved = yaml.safe_load(profile_file.read_text())
    volume_spec = saved["volumes"][0]
    _, container_part = volume_spec.split(":")
    assert container_part == "/home/llm/.claude"


def test_global_flag_without_profile(tmp_path: Path, monkeypatch) -> None:
    config_base = tmp_path / "config"
    state_base = tmp_path / "state"
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_base))
    monkeypatch.setenv("XDG_STATE_HOME", str(state_base))

    runner = CliRunner()
    # list --global works without any profile argument
    result = runner.invoke(cli, ["volume", "list", "--global"])
    assert result.exit_code == 0
