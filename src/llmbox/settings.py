from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Callable, Mapping

import yaml
from pydantic import BaseModel, ConfigDict, Field
from pydantic_settings import BaseSettings, PydanticBaseSettingsSource, SettingsConfigDict

ConfigSource = Callable[[BaseSettings], Mapping[str, Any]]


def default_config_dir() -> Path:
    base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return base / "llmbox"


def default_state_dir() -> Path:
    base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
    return base / "llmbox"


def config_file_path(config_dir: Path) -> Path:
    return config_dir / "config.yaml"


def state_file_path(state_dir: Path) -> Path:
    return state_dir / "state.yaml"


class GlobalConfig(BaseModel):
    image_name: str = "llm"

    model_config = ConfigDict(extra="forbid")


class State(BaseModel):
    last_profile: str | None = None

    model_config = ConfigDict(extra="forbid")


class Settings(BaseSettings):
    image_name: str = "llm"
    config_dir: Path = Field(default_factory=default_config_dir)
    state_dir: Path = Field(default_factory=default_state_dir)

    model_config = SettingsConfigDict(env_prefix="LLMBOX_", extra="forbid")

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            ConfigFileSource(settings_cls, init_settings, env_settings),
            file_secret_settings,
        )


class ConfigFileSource(PydanticBaseSettingsSource):
    def __init__(
        self,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
    ) -> None:
        super().__init__(settings_cls)
        self.init_settings = init_settings
        self.env_settings = env_settings

    def __call__(self) -> dict[str, Any]:
        return self._load()

    def get_field_value(self, field: Any, field_name: str) -> tuple[Any | None, str, bool]:
        data = self._load()
        if field_name in data:
            return data[field_name], field_name, True
        return None, field_name, False

    def _load(self) -> dict[str, Any]:
        init_data = dict(self.init_settings())
        env_data = dict(self.env_settings())

        config_dir_value = init_data.get("config_dir") or env_data.get("config_dir")
        state_dir_value = init_data.get("state_dir") or env_data.get("state_dir")

        config_dir = Path(config_dir_value) if config_dir_value else default_config_dir()
        state_dir = Path(state_dir_value) if state_dir_value else default_state_dir()

        data: dict[str, Any] = {"config_dir": config_dir, "state_dir": state_dir}

        cfg_path = config_file_path(config_dir)
        if cfg_path.exists():
            loaded = yaml.safe_load(cfg_path.read_text()) or {}
            if not isinstance(loaded, dict):
                raise ValueError(f"Config file {cfg_path} must contain a mapping")
            config = GlobalConfig.model_validate(loaded)
            data.update(config.model_dump())

        return data


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def load_state(state_dir: Path) -> State:
    state_path = state_file_path(state_dir)
    if not state_path.exists():
        return State()

    loaded = yaml.safe_load(state_path.read_text()) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"State file {state_path} must contain a mapping")
    return State.model_validate(loaded)


def save_state(state_dir: Path, state: State) -> None:
    ensure_dir(state_dir)
    state_file = state_file_path(state_dir)
    state_file.write_text(yaml.safe_dump(state.model_dump(), sort_keys=True))
