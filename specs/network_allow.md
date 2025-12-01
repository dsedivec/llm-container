# Network Architecture: Default-Allow with Blocklist

## Overview

Transition from a restrictive allowlist-based network policy to a more permissive blocklist-based approach. This enables AI coding agents to access documentation, APIs, and other resources while still maintaining security controls and audit logging.

## Goals

1. **Default-allow networking** - Allow most outbound HTTP/HTTPS traffic
2. **Blocklist filtering** - Block specific known-bad domains
3. **Audit logging** - Log all outbound connection attempts via proxy
4. **No direct IP connections** - Force all traffic through DNS (prevents DNS bypass)
5. **Simplified deployment** - Single container, no Docker Compose required

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│ Container                                               │
│                                                         │
│  ┌──────────────┐    ┌─────────────────────────────┐   │
│  │ Claude Code  │───▶│ tinyproxy (uid: tinyproxy)  │   │
│  │ (uid: llm)   │    │ - blocklist filtering       │   │
│  │ HTTP_PROXY   │    │ - rejects IP-only CONNECTs  │   │
│  └──────────────┘    │ - logs all requests         │   │
│        │             └──────────────┬──────────────┘   │
│        │                            │                   │
│        ▼                            ▼                   │
│  ┌─────────────────────────────────────────────────┐   │
│  │ nftables                                         │   │
│  │ - ONLY tinyproxy uid can reach 80/443 outbound  │   │
│  │ - Block private networks (except Docker subnet) │   │
│  │ - Allow DNS (53) to public resolvers            │   │
│  │ - Drop everything else                          │   │
│  └─────────────────────────────────────────────────┘   │
│                             │                           │
└─────────────────────────────┼───────────────────────────┘
                              ▼
                          Internet
```

## Implementation Plan

### 1. Dockerfile Changes

- [ ] Install `tinyproxy` package by adding it to the existing `dnf install`
      command under "packages required for isolation"
- [ ] Ensure `tinyproxy` user/group exists (created by package)
- [ ] Copy tinyproxy configuration files into container
- [ ] Remove dependency on external tinyproxy container

```dockerfile
# Copy tinyproxy configs
COPY --chown=root:root --chmod=644 tinyproxy.conf /etc/tinyproxy/tinyproxy.conf
COPY --chown=root:root --chmod=644 blocklist /etc/tinyproxy/blocklist
```

### 2. tinyproxy.conf Changes

- [ ] Change `FilterDefaultDeny Yes` → `FilterDefaultDeny No`
- [ ] Rename filter file from `allowlist` to `blocklist`
- [ ] Configure logging to `/var/log/tinyproxy/` or a bind-mountable location
- [ ] Bind to localhost only (`Listen 127.0.0.1`)

```conf
# Key settings
Listen 127.0.0.1
Port 8888
LogFile "/var/log/tinyproxy/tinyproxy.log"

# Blocklist mode
Filter "/etc/tinyproxy/blocklist"
FilterURLs On
FilterType ere
FilterCaseSensitive Off
FilterDefaultDeny No
```

### 3. blocklist File

Create new blocklist with:

- [ ] Regex patterns to block direct IPv4 connections
- [ ] Regex patterns to block direct IPv6 connections
- [ ] Any known-bad domains

```
### Block direct IP connections (force DNS usage)

# Block anything that's just numbers and dots
^[0-9.]+$
# Old hex IPv4 addresses
^0x[0-9]+$

# Anything with a colon, %, or []
[\[\]%:]


### Blocked domains
# (add as needed, blank for now)
```

### 4. entrypoint.sh Changes

- [ ] Create tinyproxy log directory
- [ ] Start tinyproxy as tinyproxy user before dropping privileges
- [ ] Detect Docker subnet dynamically for nftables rules and add it to the
      `allowed_ipv4_networks` nftables set (see below)
- [ ] Remove network validation tests
- [ ] Set `HTTP_PROXY` and `HTTPS_PROXY` to `http://127.0.0.1:8888`

```bash
# Create log directory
install -d -m 755 -o tinyproxy -g tinyproxy /var/log/tinyproxy

# Start tinyproxy
/usr/sbin/tinyproxy -c /etc/tinyproxy/tinyproxy.conf

# Detect Docker subnet (for nftables exception)
DOCKER_SUBNET=$(ip route | grep -oP 'default via \K[0-9.]+' | sed 's/\.[0-9]*$/.0\/16/')
```

### 5. rules.nft Changes

- [ ] Allow outbound TCP 80/443 only for tinyproxy UID
- [ ] Allow DNS (UDP/TCP 53) to public resolvers
- [ ] Block all private network ranges (RFC1918 + RFC6598)
- [ ] Add exception for Docker subnet (determined at runtime)
- [ ] Drop all other outbound traffic

```nft
table inet llm_egress {
    set private_ipv4_networks {
        typeof ip daddr
        flags interval
        elements = {
            10.0.0.0/8,
            172.16.0.0/12,
            192.168.0.0/16,
            100.64.0.0/10,    # RFC6598 CGNAT
            169.254.0.0/16,   # Link-local
        }
    }

    set allowed_ipv4_networks {
        typeof ip daddr
    }

    set dns_servers {
        typeof ip daddr
        elements = {
            1.1.1.1,    # Cloudflare
            9.9.9.9,    # Quad9
        }
    }

    chain output {
        type filter hook output priority filter
        policy drop

        # Allow established/related
        ct state vmap {established: accept, related: accept, invalid: drop}

        # Allow loopback
        oif lo accept

        # Allow DNS to approved servers (any process)
        ip daddr @dns_servers meta l4proto {tcp, udp} th dport 53 accept

        # Explicitly allowed subnets, mainly Docker's (set up at runtime)
        ip daddr @allowed_ipv4_networks counter accept

        # Block private networks
        ip daddr @private_ipv4_networks counter reject

        # Only tinyproxy can make outbound HTTP/HTTPS
        meta skuid "tinyproxy" tcp dport {80, 443} counter accept

        # Reject with error for faster failure
        meta l4proto {tcp, udp} reject
    }
}
```

### 6. Remove Docker Compose and tinyproxy sidecar

- [ ] Delete `docker-compose.yaml`
- [ ] Delete `tinyproxy/Dockerfile`
- [ ] Delete `tinyproxy/tinyproxy.conf`
- [ ] Delete `tinyproxy/allowlist`

### 7. Create run_container.sh

- [ ] Create `run_container.sh` in repo root
- [ ] Script passes through all arguments to container via `"$@"`
- [ ] All configuration baked into image (no required mounts)

```bash
#!/bin/bash
exec docker run -it \
    --cap-drop ALL \
    --cap-add NET_ADMIN \
    --cap-add SETPCAP \
    --cap-add SETUID \
    --cap-add SETGID \
    --cap-add AUDIT_WRITE \
    --cap-add DAC_OVERRIDE \
    --cap-add CHOWN \
    --dns 1.1.1.1 --dns 9.9.9.9 \
    -e HTTP_PROXY=http://127.0.0.1:8888 \
    -e HTTPS_PROXY=http://127.0.0.1:8888 \
    -e NO_PROXY=localhost,127.0.0.1 \
    -e CLAUDE_CONFIG_DIR=/home/llm/.claude_persistent \
    -v claude_config:/home/llm/.claude_persistent \
    -v codex_config:/home/llm/.codex \
    llm "$@"
```

## Security Considerations

### What this allows

- Outbound HTTP/HTTPS to any non-blocked domain
- DNS resolution via Cloudflare (1.1.1.1) and Quad9 (9.9.9.9)

### What this blocks

- Direct connections to IP addresses (must use DNS)
- All non-HTTP/HTTPS protocols outbound
- Connections to private networks (prevents SSRF to internal services)
- Specific domains on the blocklist

### Audit trail

- All CONNECT requests logged by tinyproxy
- Log includes timestamp, destination host, and port

## Testing

NOTE: Left here for the user.  Coding agent cannot run these tests.

After implementation, verify:

1. `curl https://www.google.com` - should succeed
2. `curl --noproxy '*' https://www.google.com` - should fail (direct connection blocked)
3. `curl https://1.2.3.4` - should fail (IP-based connection blocked by tinyproxy)
4. `curl https://blocked-domain.com` - should fail (if on blocklist)
5. DNS resolution works: `dig example.com`
6. Private network access blocked: `curl http://192.168.1.1` - should fail
7. Check tinyproxy logs show connection attempts

## File Summary

| File                  | Action                                         |
|-----------------------|------------------------------------------------|
| `llm/Dockerfile`      | Add tinyproxy package and config files         |
| `llm/entrypoint.sh`   | Start tinyproxy, detect Docker subnet          |
| `llm/rules.nft`       | New UID-based rules, block private networks    |
| `llm/tinyproxy.conf`  | New config (moved into llm/)                   |
| `llm/blocklist`       | New blocklist with IP-blocking regexes         |
| `run_container.sh`    | New script to run container with docker run    |
| `docker-compose.yaml` | Delete                                         |
| `tinyproxy/`          | Delete entire directory                        |
