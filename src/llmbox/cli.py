from __future__ import annotations

import time
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import click
from pydantic import ValidationError

from . import version_with_commit
from .docker import reload_proxy, run_container
from .profiles import (
    ProfileManager,
    choose_existing_default,
    resolve_default_profile,
    resolve_profile_for_run,
    validate_profile_name,
)
from .settings import Settings, State, load_state, save_state
from .volumes import VolumeMount, normalize_host_path, parse_mount_spec


class AbbreviatingGroup(click.Group):
    """A Click group that allows commands to be abbreviated to unique prefixes.

    For example, if a group has commands 'volume' and 'run', then 'vol' or 'v'
    will resolve to 'volume', but 'r' will resolve to 'run'. If a prefix is
    ambiguous (matches multiple commands), an error is raised.
    """

    def resolve_command(
        self, ctx: click.Context, args: list[str]
    ) -> tuple[str | None, click.Command | None, list[str]]:
        cmd_name = args[0] if args else None
        if cmd_name is None:
            return None, None, args

        # Try exact match first
        cmd = self.get_command(ctx, cmd_name)
        if cmd is not None:
            return cmd_name, cmd, args[1:]

        # Try prefix matching
        matches = [name for name in self.list_commands(ctx) if name.startswith(cmd_name)]

        if len(matches) == 1:
            return matches[0], self.get_command(ctx, matches[0]), args[1:]
        elif len(matches) > 1:
            ctx.fail(f"Ambiguous command '{cmd_name}': could be {', '.join(sorted(matches))}")

        return super().resolve_command(ctx, args)


def _load_settings(overrides: Mapping[str, Any]) -> Settings:
    try:
        return Settings(**overrides)
    except ValidationError as exc:
        raise click.ClickException(str(exc)) from exc


def _parse_profile(name: str) -> str:
    try:
        return validate_profile_name(name)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


def _resolve_profile_arg(name: str, manager: ProfileManager, state: State) -> str:
    """Resolve a profile argument, handling '-' as a shortcut for the default profile."""
    if name == "-":
        try:
            return resolve_default_profile(manager, state)
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc
    return _parse_profile(name)


def _delete_targets_from_volumes(
    volumes: Sequence[VolumeMount], targets: Iterable[str], cwd: Path
) -> list[VolumeMount]:
    remaining = list(volumes)
    matches: set[int] = set()

    for target in targets:
        if target.isdigit():
            index = int(target) - 1
            if index < 0 or index >= len(volumes):
                raise click.ClickException(f"Volume number {target} is out of range")
            matches.add(index)
            continue

        if ":" in target:
            mount = parse_mount_spec(target, cwd=cwd, allow_missing=True)
            indices = [
                idx
                for idx, volume in enumerate(volumes)
                if volume.host == mount.host and volume.container == mount.container
            ]
        else:
            host = normalize_host_path(target, cwd=cwd)
            indices = [idx for idx, volume in enumerate(volumes) if volume.host == host]

        if not indices:
            raise click.ClickException(f"Volume {target} not found")
        matches.update(indices)

    return [volume for idx, volume in enumerate(remaining) if idx not in matches]


@click.group(cls=AbbreviatingGroup)
@click.version_option(version=version_with_commit(), package_name="llmbox")
def cli() -> None:
    """Manage llm sandbox containers."""


@cli.command()
def version() -> None:
    """Show the llmbox version."""
    click.echo(version_with_commit())


@cli.group(cls=AbbreviatingGroup)
def volume() -> None:
    """Manage profile volumes."""


@volume.command("add")
@click.argument("profile")
@click.argument("mount", nargs=-1, required=True)
@click.option("--force", is_flag=True, help="Allow host paths that do not exist yet.")
def volume_add(profile: str, mount: tuple[str, ...], force: bool) -> None:
    settings = _load_settings({})
    manager = ProfileManager(settings.config_dir)
    state = load_state(settings.state_dir)
    profile_name = _resolve_profile_arg(profile, manager, state)
    try:
        data, created = manager.ensure(profile_name)
    except (ValueError, FileExistsError) as exc:
        raise click.ClickException(str(exc)) from exc
    if created:
        click.echo(f"Creating profile {profile_name}")
        save_state(settings.state_dir, State(default_profile=profile_name))

    cwd = Path.cwd()
    try:
        for spec in mount:
            volume_mount = parse_mount_spec(spec, cwd=cwd, allow_missing=force)
            data.volumes.append(volume_mount)
    except (FileNotFoundError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc

    manager.save(profile_name, data)


@volume.command("list")
@click.argument("profile")
def volume_list(profile: str) -> None:
    settings = _load_settings({})
    manager = ProfileManager(settings.config_dir)
    state = load_state(settings.state_dir)
    profile_name = _resolve_profile_arg(profile, manager, state)
    try:
        data = manager.load(profile_name)
    except (FileNotFoundError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc

    for idx, volume in enumerate(data.volumes, start=1):
        click.echo(f"{idx}. {volume.spec()}")


@volume.command("remove")
@click.argument("profile")
@click.argument("mount", nargs=-1, required=True)
def volume_remove(profile: str, mount: tuple[str, ...]) -> None:
    settings = _load_settings({})
    manager = ProfileManager(settings.config_dir)
    state = load_state(settings.state_dir)
    profile_name = _resolve_profile_arg(profile, manager, state)
    try:
        data = manager.load(profile_name)
    except (FileNotFoundError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc

    cwd = Path.cwd()
    updated_volumes = _delete_targets_from_volumes(data.volumes, mount, cwd)
    data.volumes = updated_volumes
    manager.save(profile_name, data)


@cli.group(cls=AbbreviatingGroup)
def profile() -> None:
    """Manage profiles."""


@profile.command("list")
def profile_list() -> None:
    settings = _load_settings({})
    manager = ProfileManager(settings.config_dir)
    state = load_state(settings.state_dir)
    profiles = manager.list_profiles()
    default_profile = choose_existing_default(profiles, state.default_profile)

    for idx, name in enumerate(profiles, start=1):
        marker = " *" if name == default_profile else ""
        click.echo(f"{idx}. {name}{marker}")


@profile.command("create")
@click.argument("profile", required=False)
def profile_create(profile: str | None) -> None:
    settings = _load_settings({})
    manager = ProfileManager(settings.config_dir)

    if profile is None:
        # Let Click surface usage by raising an error
        raise click.UsageError("Missing argument 'PROFILE'.")

    if profile == "-":
        profile_name = "default"
    else:
        profile_name = _parse_profile(profile)

    if profile_name == "default" and manager.exists("default") and profile == "-":
        raise click.ClickException("Profile default already exists")

    try:
        manager.create(profile_name)
    except FileExistsError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"Created profile {profile_name}")
    save_state(settings.state_dir, State(default_profile=profile_name))


@profile.command("remove")
@click.argument("profile", nargs=-1, required=True)
def profile_remove(profile: tuple[str, ...]) -> None:
    settings = _load_settings({})
    manager = ProfileManager(settings.config_dir)
    state = load_state(settings.state_dir)
    profiles = manager.list_profiles()

    def resolve(name: str) -> str:
        if name == "-":
            return _resolve_profile_arg(name, manager, state)
        if name.isdigit():
            index = int(name) - 1
            if index < 0 or index >= len(profiles):
                raise click.ClickException(f"Profile number {name} is out of range")
            return profiles[index]
        return _parse_profile(name)

    targets = [resolve(item) for item in profile]
    try:
        manager.delete(targets)
    except FileNotFoundError as exc:
        raise click.ClickException(str(exc)) from exc

    remaining = manager.list_profiles()
    new_default = state.default_profile
    if state.default_profile in targets:
        if remaining:
            new_default = "default" if "default" in remaining else sorted(remaining)[0]
            click.echo(f"Default profile removed, new default profile is: {new_default}")
        else:
            new_default = None
            click.echo("Default profile removed; no profiles remain, clearing default")
        save_state(settings.state_dir, State(default_profile=new_default))


@profile.command("rename")
@click.argument("old")
@click.argument("new")
def profile_rename(old: str, new: str) -> None:
    settings = _load_settings({})
    manager = ProfileManager(settings.config_dir)
    state = load_state(settings.state_dir)
    old_name = _resolve_profile_arg(old, manager, state)
    new_name = _parse_profile(new)
    try:
        manager.rename(old_name, new_name)
    except (FileNotFoundError, FileExistsError) as exc:
        raise click.ClickException(str(exc)) from exc

    if state.default_profile == old_name:
        save_state(settings.state_dir, State(default_profile=new_name))


@profile.command("copy")
@click.argument("source")
@click.argument("destination")
def profile_copy(source: str, destination: str) -> None:
    settings = _load_settings({})
    manager = ProfileManager(settings.config_dir)
    state = load_state(settings.state_dir)
    src = _resolve_profile_arg(source, manager, state)
    dest = _parse_profile(destination)
    try:
        manager.copy(src, dest)
    except (FileNotFoundError, FileExistsError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc


@profile.command("set-default")
@click.argument("profile")
def profile_set_default(profile: str) -> None:
    settings = _load_settings({})
    manager = ProfileManager(settings.config_dir)
    profiles = manager.list_profiles()

    if profile == "-":
        raise click.ClickException("Use an explicit profile name to set default")

    resolved = None
    if profile.isdigit():
        index = int(profile) - 1
        if index < 0 or index >= len(profiles):
            raise click.ClickException(f"Profile number {profile} is out of range")
        resolved = profiles[index]
    else:
        resolved = _parse_profile(profile)
        if not manager.exists(resolved):
            raise click.ClickException(f"Profile {resolved} does not exist")

    save_state(settings.state_dir, State(default_profile=resolved))
    click.echo(f"Default profile set to {resolved}")


@cli.group(cls=AbbreviatingGroup)
def proxy() -> None:
    """Manage proxy settings."""


@proxy.command("reload")
@click.argument("profile")
def proxy_reload(profile: str) -> None:
    settings = _load_settings({})
    manager = ProfileManager(settings.config_dir)
    state = load_state(settings.state_dir)
    profile_name = _resolve_profile_arg(profile, manager, state)
    containers, failures = reload_proxy(profile_name)
    if not containers:
        click.echo("Warning: no running containers for this profile")
        return

    if failures:
        for container, detail in failures:
            message = f"Error: failed to reload proxy in container {container}"
            if detail:
                message += f": {detail}"
            click.echo(message)
        raise click.ClickException("Proxy reload failed")


@cli.command()
@click.option("-i", "--image", "image_name", help="Container image to run.")
@click.option("-n", "--dry-run", is_flag=True, help="Print docker command without running it.")
@click.argument("profile", required=False)
@click.argument("args", nargs=-1)
def run(image_name: str | None, dry_run: bool, profile: str | None, args: tuple[str, ...]) -> None:
    overrides: dict[str, object] = {}
    if image_name:
        overrides["image_name"] = image_name

    settings = _load_settings(overrides)
    manager = ProfileManager(settings.config_dir)
    state = load_state(settings.state_dir)

    requested_profile = None if profile in (None, "-") else profile
    try:
        name, created, new_default, reassigned = resolve_profile_for_run(
            manager, state, requested_profile
        )
    except (FileNotFoundError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    if created:
        click.echo(f"Creating profile {name}")
    if reassigned and not created and new_default:
        click.echo(f"Default profile missing; switching default to {new_default}")

    try:
        data = manager.load(name)
    except (FileNotFoundError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"Using profile {click.style(name, bold=True)}")
    if data.volumes:
        for vol in data.volumes:
            host = click.style(str(vol.host), fg="cyan")
            container = click.style(str(vol.container), fg="green")
            click.echo(f"  {host} -> {container}")
    else:
        click.echo(click.style("Warning: profile has no volumes", fg="yellow", bold=True))
        time.sleep(1)

    from .docker import build_run_command

    command_line, _ = build_run_command(
        settings.image_name,
        name,
        data.volumes,
        list(args),
        settings.config_dir,
    )

    if dry_run:
        click.echo(" ".join(str(part) for part in command_line))
        return

    run_container(
        settings.image_name,
        name,
        data.volumes,
        list(args),
        settings.config_dir,
    )
    if new_default:
        save_state(settings.state_dir, State(default_profile=new_default))
