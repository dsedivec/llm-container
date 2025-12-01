# llmbox

Helper CLI to manage llm sandbox containers and their profiles/volumes.

## Installation options

- **uv tool install (recommended)**  
  `uv tool install . --force`  
  Installs an isolated runtime and places an `llmbox` launcher in `~/.local/bin` (or your XDG bin). No venv activation needed.

- **pipx**  
  `pipx install . --force`  
  Also exposes `llmbox` in `~/.local/bin` using an isolated pipx-managed virtualenv.

- **Repo-local virtualenv**  
  `uv sync --extra dev` then run with `uv run llmbox ...` or `./.venv/bin/llmbox ...`. Add `./.venv/bin` to PATH if you want to call it directly.

Ensure `~/.local/bin` is on your PATH so the installed launcher is found.
