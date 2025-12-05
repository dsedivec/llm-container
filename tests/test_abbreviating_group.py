from __future__ import annotations

import click
from click.testing import CliRunner

from llmbox.cli import AbbreviatingGroup


@click.group(cls=AbbreviatingGroup)
def sample_cli() -> None:
    """Sample CLI for testing abbreviation."""


@sample_cli.group(cls=AbbreviatingGroup)
def volume() -> None:
    """Volume commands."""


@sample_cli.group(cls=AbbreviatingGroup)
def profile() -> None:
    """Profile commands."""


@sample_cli.group(cls=AbbreviatingGroup)
def proxy() -> None:
    """Proxy commands."""


@sample_cli.command()
def run() -> None:
    """Run command."""
    click.echo("run executed")


@volume.command("list")
def volume_list() -> None:
    click.echo("volume list executed")


@volume.command("add")
def volume_add() -> None:
    click.echo("volume add executed")


@profile.command("list")
def profile_list() -> None:
    click.echo("profile list executed")


@profile.command("create")
def profile_create() -> None:
    click.echo("profile create executed")


def test_exact_match() -> None:
    runner = CliRunner()
    result = runner.invoke(sample_cli, ["volume", "list"])
    assert result.exit_code == 0
    assert "volume list executed" in result.output


def test_unique_prefix_single_char() -> None:
    runner = CliRunner()
    # 'v' uniquely matches 'volume'
    result = runner.invoke(sample_cli, ["v", "l"])
    assert result.exit_code == 0
    assert "volume list executed" in result.output


def test_unique_prefix_multiple_chars() -> None:
    runner = CliRunner()
    result = runner.invoke(sample_cli, ["vol", "lis"])
    assert result.exit_code == 0
    assert "volume list executed" in result.output


def test_ambiguous_prefix_top_level() -> None:
    runner = CliRunner()
    # 'pro' matches both 'profile' and 'proxy'
    result = runner.invoke(sample_cli, ["pro", "list"])
    assert result.exit_code != 0
    assert "Ambiguous command 'pro'" in result.output
    assert "profile" in result.output
    assert "proxy" in result.output


def test_ambiguous_prefix_single_char() -> None:
    runner = CliRunner()
    # 'p' matches both 'profile' and 'proxy'
    result = runner.invoke(sample_cli, ["p", "list"])
    assert result.exit_code != 0
    assert "Ambiguous command 'p'" in result.output


def test_unique_prefix_disambiguates() -> None:
    runner = CliRunner()
    # 'prof' uniquely matches 'profile'
    result = runner.invoke(sample_cli, ["prof", "l"])
    assert result.exit_code == 0
    assert "profile list executed" in result.output


def test_unique_prefix_other_disambiguation() -> None:
    runner = CliRunner()
    # 'prox' uniquely matches 'proxy', invoking with --help shows it resolved
    result = runner.invoke(sample_cli, ["prox", "--help"])
    assert result.exit_code == 0
    assert "Proxy commands" in result.output


def test_run_single_char() -> None:
    runner = CliRunner()
    # 'r' uniquely matches 'run'
    result = runner.invoke(sample_cli, ["r"])
    assert result.exit_code == 0
    assert "run executed" in result.output


def test_unknown_command() -> None:
    runner = CliRunner()
    result = runner.invoke(sample_cli, ["xyz"])
    assert result.exit_code != 0
    assert "No such command" in result.output


def test_subcommand_abbreviation() -> None:
    runner = CliRunner()
    # Test that subcommands also support abbreviation
    result = runner.invoke(sample_cli, ["profile", "c"])
    assert result.exit_code == 0
    assert "profile create executed" in result.output


def test_ambiguous_subcommand() -> None:
    runner = CliRunner()
    # In volume group, 'l' matches 'list' but 'a' matches 'add'
    # Both 'list' and 'add' don't share a prefix, so 'l' is unique
    result = runner.invoke(sample_cli, ["volume", "a"])
    assert result.exit_code == 0
    assert "volume add executed" in result.output
