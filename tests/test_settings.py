from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from llmbox.settings import Settings


def test_settings_precedence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_root = tmp_path / "config"
    state_root = tmp_path / "state"
    config_dir = config_root / "llmbox"
    state_dir = state_root / "llmbox"
    config_dir.mkdir(parents=True)
    state_dir.mkdir(parents=True)

    (config_dir / "config.yaml").write_text("image_name: fromfile\n")

    monkeypatch.setenv("LLMBOX_IMAGE_NAME", "fromenv")

    settings = Settings(config_dir=config_dir, state_dir=state_dir)
    assert settings.image_name == "fromenv"

    settings_cli = Settings(config_dir=config_dir, state_dir=state_dir, image_name="fromcli")
    assert settings_cli.image_name == "fromcli"


def test_settings_reject_unknown_keys(tmp_path: Path) -> None:
    config_dir = tmp_path / "llmbox"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text("unexpected: value\n")

    with pytest.raises((ValidationError, ValueError)):
        Settings(config_dir=config_dir)
