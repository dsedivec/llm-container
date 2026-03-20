from __future__ import annotations

from pathlib import Path

import yaml
from click.testing import CliRunner

from llmbox import cli
from llmbox.settings import config_file_path


def test_run_creates_default_profile(tmp_path: Path, monkeypatch) -> None:
    config_base = tmp_path / "config"
    state_base = tmp_path / "state"
    env = {
        "XDG_CONFIG_HOME": str(config_base),
        "XDG_STATE_HOME": str(state_base),
    }

    runner = CliRunner()

    called = {}

    def fake_run(
        image_name, profile, global_volumes, volumes, extra_args, config_dir, persist_dir=None
    ):
        called.update(
            {
                "image_name": image_name,
                "profile": profile,
                "volumes": volumes,
                "extra_args": extra_args,
                "config_dir": config_dir,
                "persist_dir": persist_dir,
            }
        )
        return "container", []

    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_base))
    monkeypatch.setenv("XDG_STATE_HOME", str(state_base))
    monkeypatch.setattr(cli, "run_container", fake_run)

    result = runner.invoke(cli.cli, ["run"], env=env)
    assert result.exit_code == 0
    assert "Creating profile default" in result.output
    assert "Using profile default" in result.output
    assert "Warning: profile has no volumes" in result.output
    assert called["profile"] == "default"

    state_file = state_base / "llmbox" / "state.yaml"
    assert state_file.exists()
    state = yaml.safe_load(state_file.read_text())
    assert state["default_profile"] == "default"


def test_run_reassigns_missing_default(tmp_path: Path, monkeypatch) -> None:
    config_base = tmp_path / "config"
    state_base = tmp_path / "state"
    env = {
        "XDG_CONFIG_HOME": str(config_base),
        "XDG_STATE_HOME": str(state_base),
    }

    runner = CliRunner()

    # Pre-create profiles without setting default in state
    (config_base / "config").mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_base))
    monkeypatch.setenv("XDG_STATE_HOME", str(state_base))

    runner.invoke(cli.cli, ["profile", "create", "alpha"], env=env)
    runner.invoke(cli.cli, ["profile", "create", "beta"], env=env)

    called = {}

    def fake_run(
        image_name, profile, global_volumes, volumes, extra_args, config_dir, persist_dir=None
    ):
        called["profile"] = profile
        return "container", []

    monkeypatch.setattr(cli, "run_container", fake_run)

    # Delete state to simulate missing default
    state_file = state_base / "llmbox" / "state.yaml"
    if state_file.exists():
        state_file.unlink()

    result = runner.invoke(cli.cli, ["run"], env=env)
    assert result.exit_code == 0
    assert "switching default to alpha" in result.output
    assert called["profile"] == "alpha"
    state = yaml.safe_load(state_file.read_text())
    assert state["default_profile"] == "alpha"


def test_run_does_not_change_default_when_running_other_profile(
    tmp_path: Path, monkeypatch
) -> None:
    config_base = tmp_path / "config"
    state_base = tmp_path / "state"
    env = {
        "XDG_CONFIG_HOME": str(config_base),
        "XDG_STATE_HOME": str(state_base),
    }

    runner = CliRunner()
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_base))
    monkeypatch.setenv("XDG_STATE_HOME", str(state_base))

    runner.invoke(cli.cli, ["profile", "create", "alpha"], env=env)
    runner.invoke(cli.cli, ["profile", "create", "beta"], env=env)
    # Default set to beta after creation

    monkeypatch.setattr(
        cli,
        "run_container",
        lambda image_name, profile, global_volumes, volumes, extra_args, config_dir, persist_dir=None: (
            "container",
            [],
        ),
    )

    result = runner.invoke(cli.cli, ["run", "alpha"], env=env)
    assert result.exit_code == 0

    state_file = state_base / "llmbox" / "state.yaml"
    state = yaml.safe_load(state_file.read_text())
    assert state["default_profile"] == "beta"


def test_run_includes_global_volumes(tmp_path: Path, monkeypatch) -> None:
    config_base = tmp_path / "config"
    state_base = tmp_path / "state"
    env = {
        "XDG_CONFIG_HOME": str(config_base),
        "XDG_STATE_HOME": str(state_base),
    }
    monkeypatch.setenv("XDG_CONFIG_HOME", str(config_base))
    monkeypatch.setenv("XDG_STATE_HOME", str(state_base))

    runner = CliRunner()

    # Create a profile first
    runner.invoke(cli.cli, ["profile", "create", "dev"], env=env)

    # Write global config with a volume
    host_dir = tmp_path / "dotclaude"
    host_dir.mkdir()
    config_dir = config_base / "llmbox"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file_path(config_dir).write_text(
        f"image_name: llm\nvolumes:\n- {host_dir}:/home/llm/.claude\n"
    )

    called = {}

    def fake_run(
        image_name, profile, global_volumes, volumes, extra_args, config_dir, persist_dir=None
    ):
        called["global_volumes"] = global_volumes
        called["volumes"] = volumes
        return "container", []

    monkeypatch.setattr(cli, "run_container", fake_run)

    result = runner.invoke(cli.cli, ["run", "dev"], env=env)
    assert result.exit_code == 0
    assert "Global volumes:" in result.output
    assert len(called["global_volumes"]) == 1
    assert called["global_volumes"][0].host == host_dir
    assert str(called["global_volumes"][0].container) == "/home/llm/.claude"


def test_run_passes_persist_dir_from_profile(tmp_path: Path, monkeypatch) -> None:
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

    # Set persist_dir on the profile
    persist = tmp_path / "my_persist"
    runner.invoke(cli.cli, ["config", "persist-dir", "dev", str(persist)], env=env)

    called = {}

    def fake_run(
        image_name, profile, global_volumes, volumes, extra_args, config_dir, persist_dir=None
    ):
        called["persist_dir"] = persist_dir
        return "container", []

    monkeypatch.setattr(cli, "run_container", fake_run)
    result = runner.invoke(cli.cli, ["run", "dev"], env=env)
    assert result.exit_code == 0
    assert called["persist_dir"] == str(persist)


def test_run_persist_dir_defaults_to_none(tmp_path: Path, monkeypatch) -> None:
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

    called = {}

    def fake_run(
        image_name, profile, global_volumes, volumes, extra_args, config_dir, persist_dir=None
    ):
        called["persist_dir"] = persist_dir
        return "container", []

    monkeypatch.setattr(cli, "run_container", fake_run)
    result = runner.invoke(cli.cli, ["run", "dev"], env=env)
    assert result.exit_code == 0
    assert called["persist_dir"] is None
