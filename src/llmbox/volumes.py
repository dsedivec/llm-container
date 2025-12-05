from __future__ import annotations

import os.path
from dataclasses import dataclass
from pathlib import Path

WORKSPACE_ROOT = Path("/home/llm/workspace")


class VolumeError(ValueError):
    """Invalid volume specification."""


@dataclass(frozen=True)
class VolumeMount:
    host: Path
    container: Path

    def spec(self) -> str:
        return f"{self.host}:{self.container}"


def normalize_host_path(path: str, *, cwd: Path) -> Path:
    host_path = Path(path).expanduser()
    if not host_path.is_absolute():
        host_path = cwd / host_path
    return host_path.resolve(strict=False)


def normalize_container_path(path: str | None, host: Path) -> Path:
    if not path:
        target = WORKSPACE_ROOT / host.name
    else:
        container = Path(path)
        target = container if container.is_absolute() else WORKSPACE_ROOT / container
    return Path(os.path.normpath(target))


def parse_mount_spec(spec: str, *, cwd: Path, allow_missing: bool) -> VolumeMount:
    host_part, _, container_part = spec.partition(":")
    if not host_part:
        raise VolumeError("Volume must include a host path")

    host = normalize_host_path(host_part, cwd=cwd)
    if not allow_missing and not host.exists():
        raise FileNotFoundError(f"Host path does not exist: {host}")

    container = normalize_container_path(container_part or None, host)
    return VolumeMount(host=host, container=container)
