from __future__ import annotations

import re
from pathlib import Path
from typing import Iterable, Sequence

import yaml
from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

from .settings import State
from .volumes import VolumeMount, parse_mount_spec

PROFILE_PATTERN = re.compile(r"^[A-Za-z0-9._-]+$")


class ProfileData(BaseModel):
    volumes: list[VolumeMount] = Field(default_factory=list)

    model_config = ConfigDict(extra="forbid")

    @field_validator("volumes", mode="before")
    @classmethod
    def _parse_volumes(cls, value: object) -> list[VolumeMount]:
        if value is None:
            return []
        if not isinstance(value, list):
            raise TypeError("volumes must be a list")

        parsed: list[VolumeMount] = []
        for item in value:
            if isinstance(item, VolumeMount):
                parsed.append(item)
            elif isinstance(item, str):
                parsed.append(parse_mount_spec(item, cwd=Path("/"), allow_missing=True))
            else:
                raise TypeError("volume entries must be strings")
        return parsed

    @field_serializer("volumes")
    def _serialize_volumes(self, volumes: list[VolumeMount]) -> list[str]:
        return [volume.spec() for volume in volumes]


def validate_profile_name(name: str) -> str:
    if not PROFILE_PATTERN.fullmatch(name):
        raise ValueError("Profile names must match [A-Za-z0-9._-]+")
    if name.isdigit():
        raise ValueError("Profile names must contain at least one non-digit character")
    return name


class ProfileManager:
    def __init__(self, config_dir: Path):
        self.config_dir = config_dir
        self.profiles_dir = config_dir / "profiles"

    def _profile_path(self, profile: str) -> Path:
        validate_profile_name(profile)
        return self.profiles_dir / f"{profile}.yaml"

    def list_profiles(self) -> list[str]:
        if not self.profiles_dir.exists():
            return []
        profiles = [path.stem for path in self.profiles_dir.glob("*.yaml") if path.is_file()]
        return sorted(profiles)

    def exists(self, profile: str) -> bool:
        return self._profile_path(profile).exists()

    def load(self, profile: str) -> ProfileData:
        path = self._profile_path(profile)
        if not path.exists():
            raise FileNotFoundError(f"Profile {profile} does not exist")

        loaded = yaml.safe_load(path.read_text()) or {}
        if not isinstance(loaded, dict):
            raise ValueError(f"Profile file {path} must contain a mapping")
        return ProfileData.model_validate(loaded)

    def save(self, profile: str, data: ProfileData) -> None:
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        path = self._profile_path(profile)
        path.write_text(yaml.safe_dump(data.model_dump(), sort_keys=True))

    def create(self, profile: str) -> ProfileData:
        path = self._profile_path(profile)
        if path.exists():
            raise FileExistsError(f"Profile {profile} already exists")

        data = ProfileData()
        self.profiles_dir.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(data.model_dump(), sort_keys=True))
        return data

    def ensure(self, profile: str) -> tuple[ProfileData, bool]:
        if self.exists(profile):
            return self.load(profile), False
        return self.create(profile), True

    def delete(self, profiles: Iterable[str]) -> None:
        for profile in profiles:
            path = self._profile_path(profile)
            if not path.exists():
                raise FileNotFoundError(f"Profile {profile} does not exist")
            path.unlink()

    def rename(self, old: str, new: str) -> None:
        old_path = self._profile_path(old)
        if not old_path.exists():
            raise FileNotFoundError(f"Profile {old} does not exist")

        new_path = self._profile_path(new)
        if new_path.exists():
            raise FileExistsError(f"Profile {new} already exists")

        self.config_dir.mkdir(parents=True, exist_ok=True)
        old_path.rename(new_path)

    def copy(self, source: str, destination: str) -> None:
        if source == destination:
            raise ValueError("Source and destination profiles must differ")

        data = self.load(source)
        dest_path = self._profile_path(destination)
        if dest_path.exists():
            raise FileExistsError(f"Profile {destination} already exists")

        self.save(destination, data)


def choose_existing_default(profiles: Sequence[str], last_profile: str | None) -> str | None:
    if last_profile and last_profile in profiles:
        return last_profile
    if len(profiles) == 1:
        return profiles[0]
    return None


def resolve_profile_for_run(
    manager: ProfileManager, state: State, requested: str | None
) -> tuple[str, bool]:
    if requested:
        profile = validate_profile_name(requested)
        if not manager.exists(profile):
            raise FileNotFoundError(f"Profile {profile} does not exist")
        return profile, False

    profiles = manager.list_profiles()
    chosen = choose_existing_default(profiles, state.last_profile)
    if chosen:
        return chosen, False

    if not profiles:
        manager.create("default")
        return "default", True

    if len(profiles) == 1:
        return profiles[0], False

    if "default" not in profiles:
        manager.create("default")
        return "default", True

    return "default", False
