I want a script that will help me start up one or more of the `llm`
containers.

The script will be called `llmbox`.

# Project Layout

We'll write the script in Python using Click for the CLI and pytest for
testing.

## Dependencies

The project uses `uv` for dependency management, virtual environment creation,
and running development tools.  The build backend is `hatchling`.

Runtime dependencies:
- click

Development dependencies:
- pytest
- black (code formatting)
- ruff (linting)
- basedpyright (type checking)

Use `uv sync` to install dependencies and set up the virtual environment.  Use
`uv run` to run commands within the virtual environment (e.g., `uv run pytest`,
`uv run black .`).

## Code Quality

All code must:
- Be formatted with Black
- Pass linting with ruff
- Pass type checking with basedpyright

Tests should be developed alongside each piece of functionality.  When
implementing a new feature, write tests for it before moving on to the next
feature.

## Testing the `run` Command

Tests cannot actually run `docker compose`.  To support testing, the `run`
command should check for an environment variable `LLMBOX_DOCKER_COMMAND`.  If
set, this specifies an alternative command to run instead of `docker compose`.
Tests can set this to a script or command that captures the arguments and
verifies they are correct, without actually starting a container.

## Directory Structure

The project will live in a subdirectory alongside the container
infrastructure:

```
claude-container/              # repository root
├── docker-compose.yaml
├── llm/
│   └── ...
├── tinyproxy/
│   └── ...
├── specs/
│   └── ...
└── llmbox/                    # Python project
    ├── pyproject.toml
    ├── src/
    │   └── llmbox/
    │       ├── __init__.py
    │       ├── cli.py         # Click CLI setup, entry point
    │       ├── config.py      # XDG paths, profile storage
    │       └── mounts.py      # mount parsing/resolution
    └── tests/
        ├── conftest.py        # fixtures (temp XDG dirs, etc.)
        ├── test_config.py
        └── test_mounts.py
```

# Profiles

The script is going to have the concept of "profiles".  Each profile will
have its own set of volumes that will be added onto the container.

Right now I run the container like:

```
docker compose run -it --rm \
                   -v ../claude-container:/home/llm/workspace/claude-container llm
```

That's mounting one repository into the `/home/llm/workspace` directory.  I
want each profile to have multiple such mounts possible.

# Commands

## `mount`

```
llmbox mount add <profile> <mount>...
```

`<profile>` is the name of a profile.  These are arbitrary names.
`<mount>...` is one or more mount specifications that will be bind-mounted into
the container when you start it with this profile.  Each mount specification
has the form `<host path>[:<container path>]`.  If `<container path>` is
omitted, the mount will be placed at `/home/llm/workspace/<basename of host
path>`.  If `<container path>` is a relative path, it will be interpreted as
relative to `/home/llm/workspace`.  For example:

```
llmbox mount add claude ../claude-container
llmbox mount add claude /home/user/projects/myapp:/opt/myapp
```

Mount paths are stored as absolute paths.  Relative paths provided on the
command line are resolved to absolute paths at the time of the `mount add`
command.

By default, `mount add` will fail if a provided host directory doesn't exist.
Use `--force` to override this and add a mount for a directory that doesn't
exist yet.

This needs to be saved in a file.  Profile definitions will be stored in
`$XDG_CONFIG_HOME/llmbox` (defaulting to `~/.config/llmbox` if not set).
Runtime state such as the "last used profile" will be stored in
`$XDG_STATE_HOME/llmbox` (defaulting to `~/.local/state/llmbox` if not set).

If a profile doesn't already exist, the `add` command should automatically
create it.  It should print an information message when it creates a profile.

```
llmbox mount list <profile>
```

This lists all the mounts in a profile, and numbers them.  The numbers are
important for the next command.

```
llmbox mount delete <profile> <mount>...
```

This is the opposite of `mount add`: it deletes a mount from a profile.
`<mount>` can be either the path to a mount, or the number given by the `mount
list` command.

## `run`

```
llmbox run [--compose|-c <path to compose YAML>] [<profile>] [<args>]
```

This should start a new `llm` container using `docker compose run` as I've
shown above.  It should add `-v` switches for each of the mounts given in the
profile definition, if there are any mounts.

If there is no profile given on the command line, or if `<profile>` is a
single hyphen (`-`), use the *default profile*.  The default profile is one of
the following profiles, stopping at the first one that yields a profile:

1. The last profile that was `run`
2. The only profile that exists
3. The command should create a profile called `default` and use that

`run` should always print which profile it's using.  If it creates a profile,
it should print that it is both creating and using that profile.

If the profile has no mounts, `run` should print a warning before starting the
container.

`<args>`, if any, are passed verbatim to `docker compose run` at the end of
the command line.

### Locating docker-compose.yaml

The `run` command needs to locate the `docker-compose.yaml` file.  The
location is determined by (in order of precedence):

1. The `--compose` / `-c` global option: `llmbox -c /path/to/docker-compose.yaml run`
2. The `LLMBOX_COMPOSE_FILE` environment variable
3. `docker-compose.yaml` in the current working directory

If none of these yield a valid file, the `run` command should error out.  Only
the `run` command requires the compose file; other commands should work without
it.

When running `docker compose`, the command must be executed with the compose
file's directory as the working directory (or using appropriate flags) so that
Docker Compose uses the correct project name and context.

## `profile`

```
llmbox profile list
```

This should list all profiles.  It should number them, and highlight or put a
star next to the default profile.

```
llmbox profile create <profile>
```

This will create the given profile.  It's an error if the profile already
exists.

```
llmbox profile delete <profile>
```

Deletes a profile and all of its configuration data.  (It's OK if there are
container(s) currently running under that profile, ignore that.)  `<profile>`
can be either the name of a profile or a profile number as printed by `profile
list`.

```
llmbox profile rename <old-name> <new-name>
```

Renames a profile.  It's an error if `<old-name>` doesn't exist or if
`<new-name>` already exists.

```
llmbox profile copy <source> <destination>
```

Copies a profile, including all of its mounts.  The copy works even if the
source profile has no mounts (creating an empty destination profile).  It's an
error if `<source>` doesn't exist or if `<destination>` already exists.

## `proxy`

```
llmbox proxy reload
```

Sends SIGUSR1 to tinyproxy to reload its configuration.
