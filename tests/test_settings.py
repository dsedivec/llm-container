from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from llmbox.settings import GlobalConfig, Settings, load_config, save_config


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


def test_state_migrates_last_profile(tmp_path: Path) -> None:
    state_dir = tmp_path / "llmbox"
    state_dir.mkdir()
    state_file = state_dir / "state.yaml"
    state_file.write_text("last_profile: old\n")

    from llmbox.settings import load_state

    state = load_state(state_dir)
    assert state.default_profile == "old"


def test_global_config_with_volumes(tmp_path: Path) -> None:
    config_dir = tmp_path / "llmbox"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text(
        "image_name: llm\nvolumes:\n- ~/.claude:/home/llm/.claude\n"
    )
    config = load_config(config_dir)
    assert config.volumes == ["~/.claude:/home/llm/.claude"]


def test_save_and_load_config_roundtrip(tmp_path: Path) -> None:
    config_dir = tmp_path / "llmbox"
    config = GlobalConfig(
        image_name="custom",
        volumes=["/home/user/.claude:/home/llm/.claude"],
    )
    save_config(config_dir, config)
    loaded = load_config(config_dir)
    assert loaded.image_name == "custom"
    assert loaded.volumes == ["/home/user/.claude:/home/llm/.claude"]


def test_global_config_empty_volumes_default(tmp_path: Path) -> None:
    config_dir = tmp_path / "llmbox"
    config_dir.mkdir()
    (config_dir / "config.yaml").write_text("image_name: llm\n")
    config = load_config(config_dir)
    assert config.volumes == []
