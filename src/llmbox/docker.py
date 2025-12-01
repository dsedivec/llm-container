from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from .volumes import VolumeMount

BASE_RUN_ARGS = [
    "docker",
    "run",
    "--rm",
    "-it",
    "--cap-drop",
    "ALL",
    "--cap-add",
    "NET_ADMIN",
    "--cap-add",
    "SETPCAP",
    "--cap-add",
    "SETUID",
    "--cap-add",
    "SETGID",
    "--cap-add",
    "AUDIT_WRITE",
    "--cap-add",
    "DAC_OVERRIDE",
    "--cap-add",
    "CHOWN",
    "--dns",
    "1.1.1.1",
    "--dns",
    "9.9.9.9",
    "-e",
    "HTTP_PROXY=http://127.0.0.1:8888",
    "-e",
    "HTTPS_PROXY=http://127.0.0.1:8888",
    "-e",
    "NO_PROXY=localhost,127.0.0.1",
    "-e",
    "CLAUDE_CONFIG_DIR=/home/llm/.persist/claude",
    "-e",
    "CODEX_HOME=/home/llm/.persist/codex",
    "-v",
    "llm_persist:/home/llm/.persist",
]


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")


def build_run_command(
    image_name: str,
    profile: str,
    volumes: Sequence[VolumeMount],
    extra_args: Sequence[str],
    config_dir: Path,
) -> tuple[list[str], str]:
    name = f"llmbox-{profile}-{_timestamp()}"
    blocklist_path = config_dir / "proxy_blocklist"
    blocklist_path.parent.mkdir(parents=True, exist_ok=True)
    blocklist_path.touch(exist_ok=True)

    command: list[str] = [
        *BASE_RUN_ARGS,
        "--name",
        name,
        "--label",
        "llmbox.managed=true",
        "--label",
        f"llmbox.profile={profile}",
    ]

    for volume in volumes:
        command.extend(["-v", volume.spec()])

    command.extend(["-v", f"{blocklist_path}:/etc/tinyproxy/blocklist:ro"])
    command.extend(extra_args)
    command.append(image_name)
    return command, name


def run_container(
    image_name: str,
    profile: str,
    volumes: Sequence[VolumeMount],
    extra_args: Sequence[str],
    config_dir: Path,
    runner=subprocess.run,
) -> tuple[str, list[str]]:
    command, name = build_run_command(image_name, profile, volumes, extra_args, config_dir)
    runner(command, check=True)
    return name, command


def list_profile_containers(profile: str, runner=subprocess.run) -> list[str]:
    ps_command = [
        "docker",
        "ps",
        "--filter",
        f"label=llmbox.profile={profile}",
        "--format",
        "{{.ID}}",
    ]
    result = runner(ps_command, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Failed to list containers")
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def reload_proxy(profile: str, runner=subprocess.run) -> tuple[list[str], list[tuple[str, str]]]:
    containers = list_profile_containers(profile, runner=runner)
    if not containers:
        return [], []

    failures: list[tuple[str, str]] = []
    for container in containers:
        exec_command = [
            "docker",
            "exec",
            container,
            "sh",
            "-c",
            'pid="$(cat /run/tinyproxy.pid)" && runuser -u tinyproxy -- kill -USR1 "$pid"',
        ]
        result = runner(exec_command, check=False, capture_output=True, text=True)
        if result.returncode != 0:
            detail = (result.stderr or result.stdout or "").strip()
            failures.append((container, detail))

    return containers, failures
