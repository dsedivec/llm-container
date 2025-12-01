# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This project provides a security-hardened Docker container for running Claude Code with network isolation. The container restricts outbound network access to only essential services (Anthropic API, GitHub, and DNS servers) using nftables firewall rules.

## Architecture

### Core Components

- **llm/Dockerfile**: Fedora-based container with Claude Code, network tools (nftables), and development utilities
- **llm/entrypoint.sh**: Container initialization script that:
  1. Configures nftables firewall rules
  2. Validates network isolation (ensures Google is unreachable both via proxy and directly)
  3. Drops privileges and launches user shell
- **llm/rules.nft**: nftables configuration defining allowed IP ranges and drop-by-default policy
- **tinyproxy/**: HTTP proxy sidecar that allowlists specific domains (Anthropic API, GitHub, npm, etc.)

### Network Isolation

The container uses a two-layer network isolation approach:

1. **nftables firewall** (llm/rules.nft): Default-deny policy that only allows:
   - Cloudflare DNS (1.1.1.1) and Quad9 DNS (9.9.9.9)
   - Connections to tinyproxy on the Docker network (172.16.0.0/12 port 8888)
   - All other outbound connections are rejected

2. **tinyproxy allowlist** (tinyproxy/allowlist): HTTP proxy that only permits connections to specific domains (Anthropic API, GitHub, npm registry, etc.)

- **Validation**: Startup script verifies isolation by ensuring Google is unreachable both via proxy and directly (llm/entrypoint.sh:10-22)

### Security Model

- Container runs with minimal capabilities (docker-compose.yaml:14-22)
- Privileges are dropped after network setup via setpriv (llm/entrypoint.sh:38-45)
- User runs with limited sudo access for package installation (llm/llm_sudoers)
- Persistent Claude configuration via Docker volume (docker-compose.yaml:35-37)

## Development Commands

### Building and Running

```bash
# Build the container
docker-compose build

# Start the container
docker-compose up -d

# Enter the container
docker-compose exec llm bash

# View logs
docker-compose logs -f
```

### Testing Network Isolation

The entrypoint automatically validates isolation, but you can test manually:

```bash
# Should fail (blocked)
curl https://www.google.com

# Should succeed (allowed)
curl https://api.anthropic.com
curl https://api.github.com
```

### Modifying Network Access

To allow access to additional domains, edit `tinyproxy/allowlist` and either:
1. Rebuild and restart the container, or
2. Reload tinyproxy by sending SIGUSR1: `docker compose exec tinyproxy kill -USR1 1`

To modify IP-level firewall rules, edit `llm/rules.nft` and rebuild the container.

## Key Files

- **llm/Dockerfile:65**: Claude Code installation
- **llm/entrypoint.sh:5**: Firewall setup
- **llm/rules.nft:47-59**: Output chain with drop policy
- **tinyproxy/allowlist**: Domain allowlist for HTTP proxy
- **docker-compose.yaml:25**: DNS configuration (Cloudflare & Quad9)

## Environment Configuration

- `.env`: Defines `LLM_USER` (default: llm)
- Persistent config stored in Docker volume `claude_config`

## Installing Packages

You can use `sudo dnf install` to install any commands or packages you need.

## Development Workflow

When developing new features (such as `llmbox`), work in a feature branch and make commits at logical points throughout development. For `llmbox` development, use the branch `llmbox`.
