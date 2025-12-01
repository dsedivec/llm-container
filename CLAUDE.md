# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This project provides a security-hardened Docker container for running Claude Code with network isolation. The container uses a default-allow networking model with blocklist filtering, audit logging, and UID-based firewall rules to prevent direct connections.

## Architecture

### Core Components

- **llm/Dockerfile**: Fedora-based container with Claude Code, tinyproxy, nftables, and development utilities
- **llm/entrypoint.sh**: Container initialization script that:
  1. Creates tinyproxy log directory
  2. Detects Docker subnet and configures nftables
  3. Starts tinyproxy
  4. Drops privileges and launches user shell
- **llm/rules.nft**: nftables configuration with UID-based rules - only tinyproxy can make outbound HTTP/HTTPS
- **llm/tinyproxy.conf**: Proxy configuration with blocklist mode
- **llm/blocklist**: Regex patterns blocking direct IP connections

### Network Isolation

The container uses a two-layer network isolation approach:

1. **nftables firewall** (llm/rules.nft): UID-based filtering:
   - Only tinyproxy user can make outbound HTTP/HTTPS (ports 80/443)
   - DNS allowed to Cloudflare (1.1.1.1) and Quad9 (9.9.9.9)
   - Private networks blocked (RFC1918, RFC6598) to prevent SSRF
   - Docker subnet dynamically allowed at startup
   - All other outbound connections are rejected

2. **tinyproxy blocklist** (llm/blocklist): Blocks connections to:
   - Direct IP addresses (forces DNS usage)
   - Any domains added to the blocklist

### Security Model

- Container runs with minimal capabilities (run_container.sh)
- Only tinyproxy can make outbound web requests (UID-based nftables rules)
- Private networks blocked to prevent SSRF attacks
- Privileges are dropped after network setup via setpriv (llm/entrypoint.sh:35-42)
- User runs with limited sudo access for package installation (llm/llm_sudoers)
- Persistent Claude configuration via Docker volume

## Development Commands

### Building and Running

```bash
# Build the container
docker build -t llm --build-arg LLM_USER=llm --build-arg LLM_HOME_DIR=/home/llm llm/

# Run the container
./run_container.sh

# Or run with a specific command
./run_container.sh claude
```

### Testing Network Isolation

```bash
# Should succeed (allowed via proxy)
curl https://www.google.com

# Should fail (direct connection blocked by nftables)
curl --noproxy '*' https://www.google.com

# Should fail (IP-based connection blocked by tinyproxy)
curl https://1.2.3.4

# Should fail (private network blocked)
curl http://192.168.1.1

# DNS resolution should work
dig example.com

# Check tinyproxy logs
cat /var/log/tinyproxy/tinyproxy.log
```

### Modifying Network Access

To block additional domains, edit `llm/blocklist` and rebuild the container.

To modify IP-level firewall rules, edit `llm/rules.nft` and rebuild the container.

## Key Files

- **llm/Dockerfile:65**: Claude Code installation
- **llm/entrypoint.sh:15**: Firewall setup
- **llm/rules.nft:40-64**: Output chain with UID-based rules
- **llm/tinyproxy.conf**: Proxy configuration
- **llm/blocklist**: Domain/IP blocklist patterns
- **run_container.sh**: Container run script with capabilities

## Environment Configuration

- `.env`: Defines `LLM_USER` (default: llm) - used during build
- Persistent config stored in Docker volume `claude_config`

## Installing Packages

You can use `sudo dnf install` to install any commands or packages you need.

## Development Workflow

When developing new features (such as `llmbox`), work in a feature branch and make commits at logical points throughout development. For `llmbox` development, use the branch `llmbox`.
