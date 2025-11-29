# Repository Guidelines

## Project Structure & Module Organization
- Root: `docker-compose.yaml` orchestrates the Claude Code container (`llm`) and the local HTTP proxy (`tinyproxy`).
- `llm/`: Fedora-based image and network lock-down assets — `Dockerfile`, `entrypoint.sh`, nftables rules (`rules.nft`), and helper `add_ip_ranges_to_nft_sets.py`.
- `tinyproxy/`: Minimal proxy image (`Dockerfile`, `tinyproxy.conf`, `allowlist`) used to funnel outbound requests through filtered destinations.
- Volumes: `claude_config` and `codex_config` persist Claude/Codex settings inside the container.

## Build, Test, and Development Commands
- `docker-compose build`: Build both images (llm and tinyproxy) with the provided args/env.
- `docker-compose up -d`: Start the stack in detached mode.
- `docker-compose logs -f llm`: Tail the llm container logs for startup and network checks.
- `docker-compose exec llm bash`: Enter the llm container as the unprivileged user for development.
- Network validation (inside the container): `curl https://www.google.com` should fail; `curl https://api.github.com` should succeed.

## Coding Style & Naming Conventions
- Shell: Prefer `bash` with `set -euo pipefail` (see `entrypoint.sh`); keep functions small and comment only non-obvious logic.
- Python: Match `add_ip_ranges_to_nft_sets.py` (stdlib only, typed variables optional, clear argparse usage).
- nftables: Follow existing table/set names (`llm_egress`, `allowed_ipv4`, `allowed_ipv6`); keep rules drop-by-default.
- File naming: kebab-case for configs, snake_case for scripts, lower-case Dockerfile directories.

## Testing Guidelines
- No automated test suite; rely on manual validation.
- After rule or proxy changes, rebuild and run `curl` checks as above to confirm allowed vs blocked destinations.
- For Python utility changes, feed sample CIDRs: `printf '192.0.2.0/24\n2001:db8::/32\n' | python3 add_ip_ranges_to_nft_sets.py llm_egress allowed_ipv4 allowed_ipv6 --nft /usr/sbin/nft`.

## Commit & Pull Request Guidelines
- Commits: Use imperative, present-tense subjects (e.g., “Harden nftables defaults”, “Clarify proxy allowlist”). Group related changes; avoid mixed concerns.
- PRs: Include a short summary, rationale, and testing notes (commands run and results). Link any related issues. If changing network rules, describe the expected allowed/blocked destinations and how you verified them. Attach config diffs or log snippets when helpful.

## Security & Configuration Tips
- Keep the allowlist minimal; prefer adding CIDR ranges via the Python helper rather than inlining many rules.
- If adding outbound destinations, justify the need and ensure Google (or other broad internet hosts) remains blocked.
- Secrets should stay outside the repo; use environment variables or Docker secrets if needed.
