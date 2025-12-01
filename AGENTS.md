# Repository Guidelines

## Overview & Layout
- Single-container setup: build from `llm/` and run via `run_container.sh`; no docker-compose or proxy sidecar.
- Key files: `llm/Dockerfile` (installs Claude Code, nftables, tinyproxy), `llm/entrypoint.sh` (nftables + proxy bootstrap), `llm/rules.nft` (egress policy), `llm/tinyproxy.conf` (blocklist proxy), `llm/blocklist` (regexes), `llm/llm_sudoers` (restricted sudo).
- Volumes: `claude_config` -> `/home/llm/.claude_persistent`, `codex_config` -> `/home/llm/.codex` for persisted settings.

## Build & Run
- Build image: `docker build -t llm --build-arg LLM_USER=llm --build-arg LLM_HOME_DIR=/home/llm llm/`.
- Run (caps + proxy env wired in): `./run_container.sh [cmd]`; defaults to shell. Proxy listens on `127.0.0.1:8888` with `HTTP_PROXY`/`HTTPS_PROXY` set; DNS pinned to `1.1.1.1` and `9.9.9.9`.
- Logs: tinyproxy logs to `/var/log/tinyproxy/tinyproxy.log` inside the container.

## Network Model & Key Rules
- Default-allow via tinyproxy with blocklist filtering; direct IP CONNECTs blocked by regexes in `llm/blocklist`.
- nftables (`llm/rules.nft`): drop-by-default; only `tinyproxy` UID may reach TCP 80/443; DNS allowed to public resolvers; private networks rejected; Docker subnet detected at runtime and added to `allowed_ipv4`.
- `llm/entrypoint.sh` loads rules, inserts the detected subnet, starts tinyproxy, and drops privileges with `setpriv` to the unprivileged `LLM_USER`.

## Coding Style & Conventions
- Shell: use `bash` with `set -euo pipefail` like `llm/entrypoint.sh`; keep logic small and comment only non-obvious steps.
- Firewall: preserve table/set names (`llm_egress`, `allowed_ipv4`, `private_ipv4_networks`, `dns_servers`) and drop-first posture; ensure tinyproxy remains the sole outbound path.
- Configs/scripts: keep kebab-case for configs, lower-case Dockerfile dirs; match existing tinyproxy/nftables formatting.

## Manual Checks (inside container)
- `curl https://www.google.com` should succeed via proxy.
- `curl --noproxy '*' https://www.google.com` should fail (direct blocked).
- `curl https://1.2.3.4` should fail (IP blocked by proxy).
- `curl http://192.168.1.1` should fail (private range blocked by nftables).
- `dig example.com` should resolve; audit via `/var/log/tinyproxy/tinyproxy.log`.

## Commit & PR Guidelines
- Commit subjects imperative/present (e.g., “Tighten proxy blocklist”). Group related changes only.
- PRs: note rationale and manual checks (commands + outcomes). If touching network rules, spell out expected allow/deny behavior and how you validated it; include relevant config/log snippets when useful.

## Security & Configuration Tips
- Keep the blocklist focused; add domains/IP regexes only when needed to avoid over-blocking.
- Do not loosen nftables/tinyproxy so processes can bypass the proxy; retain UID-based egress restriction and DNS pinning.
- Secrets stay outside the repo; prefer env vars or Docker secrets.
