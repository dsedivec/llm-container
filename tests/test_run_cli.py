from __future__ import annotations

from pathlib import Path

import yaml
from click.testing import CliRunner

from llmbox import cli


def test_run_creates_default_profile(tmp_path: Path, monkeypatch) -> None:
    config_base = tmp_path / "config"
    state_base = tmp_path / "state"
    env = {
        "XDG_CONFIG_HOME": str(config_base),
        "XDG_STATE_HOME": str(state_base),
    }

    runner = CliRunner()

    called = {}

    def fake_run(image_name, profile, volumes, extra_args, config_dir):
        called.update(
            {
                "image_name": image_name,
                "profile": profile,
                "volumes": volumes,
                "extra_args": extra_args,
                "config_dir": config_dir,
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
    assert state["last_profile"] == "default"
