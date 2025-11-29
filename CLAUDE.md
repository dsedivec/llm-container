# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This project provides a security-hardened Docker container for running Claude Code with network isolation. The container restricts outbound network access to only essential services (Anthropic API, GitHub, and DNS servers) using nftables firewall rules.

## Architecture

### Core Components

- **Dockerfile**: Fedora-based container with Claude Code, network tools (nftables), and development utilities
- **entrypoint.sh**: Container initialization script that:
  1. Fetches GitHub's IP ranges from their API
  2. Configures nftables firewall rules
  3. Validates network isolation (ensures Google is unreachable)
  4. Drops privileges and launches user shell
- **rules.nft**: nftables configuration defining allowed IP ranges and drop-by-default policy
- **add_ip_ranges_to_nft_sets.py**: Python utility to populate nftables IP sets from CIDR ranges

### Network Isolation

The container uses a default-deny network policy implemented via nftables:

- **Allowed destinations** (rules.nft:30-51):
  - Cloudflare DNS (1.1.1.1)
  - Quad9 DNS (9.9.9.9)
  - Anthropic API (160.79.104.0/23, 2607:6bc0::/48)
  - GitHub (dynamically added via API during startup)
- **Policy**: All other outbound connections are rejected (rules.nft:62)
- **Validation**: Startup script verifies isolation by ensuring curl to Google fails (entrypoint.sh:13-21)

### Security Model

- Container runs with minimal capabilities (docker-compose.yaml:13-21)
- Privileges are dropped after network setup via setpriv (entrypoint.sh:28-35)
- User runs with sudo access for package installation (llm_sudoers)
- Persistent Claude configuration via Docker volume (docker-compose.yaml:26)

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

### Modifying Firewall Rules

1. Edit `rules.nft` to add/remove IP ranges in the `allowed_ipv4` or `allowed_ipv6` sets
2. Rebuild and restart the container
3. Alternatively, use the Python utility to add ranges dynamically:

   ```bash
   echo "192.0.2.0/24" | sudo python3 /root/add_ip_ranges_to_nft_sets.py llm_egress allowed_ipv4 allowed_ipv6
   ```

## Key Files

- **Dockerfile:64**: Claude Code installation
- **entrypoint.sh:7-11**: GitHub IP range fetching and firewall setup
- **rules.nft:53-64**: Output chain with drop policy
- **docker-compose.yaml:24**: DNS configuration (Cloudflare & Quad9)

## Environment Configuration

- `.env`: Defines `LLM_USER` (default: llm)
- Persistent config stored in Docker volume `claude_config`
