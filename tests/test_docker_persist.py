from __future__ import annotations

from pathlib import Path

from llmbox.docker import _resolve_persist_mount, build_run_command


def test_resolve_persist_mount_none_uses_xdg_data(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    expected = tmp_path / "data" / "llmbox" / "persist"
    result = _resolve_persist_mount(None)
    assert result == f"{expected}:/home/llm/.persist"
    assert expected.is_dir()


def test_resolve_persist_mount_host_dir(tmp_path: Path) -> None:
    host = tmp_path / "my_persist"
    result = _resolve_persist_mount(str(host))
    assert result == f"{host}:/home/llm/.persist"
    assert host.is_dir()


def test_resolve_persist_mount_tilde(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    result = _resolve_persist_mount("~/my_persist")
    expected = tmp_path / "my_persist"
    assert f"{expected}:/home/llm/.persist" == result
    assert expected.is_dir()


def test_build_run_command_default_persist(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    expected_host = tmp_path / "data" / "llmbox" / "persist"
    cmd, _ = build_run_command(
        image_name="llm",
        profile="test",
        global_volumes=[],
        volumes=[],
        extra_args=[],
        config_dir=tmp_path,
    )
    expected_spec = f"{expected_host}:/home/llm/.persist"
    assert expected_spec in cmd
    idx = cmd.index(expected_spec)
    assert cmd[idx - 1] == "-v"


def test_build_run_command_custom_persist(tmp_path: Path) -> None:
    persist = tmp_path / "custom"
    cmd, _ = build_run_command(
        image_name="llm",
        profile="test",
        global_volumes=[],
        volumes=[],
        extra_args=[],
        config_dir=tmp_path,
        persist_dir=str(persist),
    )
    expected_spec = f"{persist}:/home/llm/.persist"
    assert expected_spec in cmd
