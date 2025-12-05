#!/usr/bin/env bash

set -xeuo pipefail

# Detect Docker subnet and add to allowed networks in nftables
# 1. Get the default gateway IP
gateway=$(ip -j route ls default | jq -r '.[0].gateway')
if [ -z "$gateway" ] || [ "$gateway" = "null" ]; then
    echo "ERROR: Could not determine default gateway" >&2
    exit 1
fi

# 2. Find the most specific non-default route that contains the gateway
#    - Filter out the default route
#    - Extract CIDR notation (dst field)
#    - Sort by prefix length (longest/most specific first)
#    - Take the first one
docker_subnet=$(ip -j route show match "$gateway" | \
    jq -r '.[] | select(.dst != "default") | .dst' | \
    awk -F/ '{ print ($2 ? $2 : 32), $0 }' | \
    sort -t' ' -k1 -nr | \
    head -1 | \
    awk '{ print $2 }')

if [ -z "$docker_subnet" ]; then
    echo "ERROR: Could not determine Docker subnet for gateway $gateway" >&2
    exit 1
fi

echo "Detected Docker subnet: $docker_subnet (gateway: $gateway)"

# Load nftables rules, then add the Docker subnet to the allowed set
nft -f /root/rules.nft
nft add element inet llm_egress allowed_ipv4 "{ $docker_subnet }"

# Start tinyproxy
/usr/sbin/tinyproxy -c /etc/tinyproxy/tinyproxy.conf

# Verify sudo permissions are restricted
if runuser -u "$LLM_USER" -- sudo -n true; then
    echo "User should not be able to run arbitrary sudo commands" >&2
    exit 1
fi

# Verify network is restricted
result=0
curl --noproxy '*' https://www.google.com || result=$?
if [ "$result" -ne 7 ]; then
    echo "Should not be able to connect to Google" >&2
    exit 1
fi

install -d -o "$LLM_USER" -g "$LLM_USER" -m 0700 \
        "$LLM_HOME_DIR/.persist/copilot"

chown -hR "$LLM_USER:$LLM_USER" "$LLM_HOME_DIR" &

# runuser sets up the environment for us.  Otherwise we'd have to
# bootstrap stuff like HOME ourselves.
exec setpriv \
    --bounding-set -net_admin,-setpcap \
    --inh-caps -all \
    --ambient -all \
    -- \
    runuser -u "$LLM_USER" -g "$LLM_USER" \
    -- \
    bash -lc 'cd && exec "$@"' -- "$@"
