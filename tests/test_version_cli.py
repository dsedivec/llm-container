from __future__ import annotations

import subprocess

from click.testing import CliRunner

from llmbox import __version__, cli


def test_version_option_outputs_version() -> None:
    runner = CliRunner()
    result = runner.invoke(cli.cli, ["--version"])
    assert result.exit_code == 0
    commit = _expected_commit()
    assert __version__ in result.output
    if commit:
        assert commit in result.output


def test_version_command_outputs_version() -> None:
    runner = CliRunner()
    result = runner.invoke(cli.cli, ["version"])
    assert result.exit_code == 0
    commit = _expected_commit()
    if commit:
        assert result.output.strip() == f"{__version__} ({commit})"
    else:
        assert result.output.strip() == __version__


def _expected_commit() -> str | None:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout.strip() or None
    except (FileNotFoundError, subprocess.CalledProcessError):
        return None
