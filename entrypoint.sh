#!/usr/bin/env bash

set -xeuo pipefail

cat /etc/sudoers.d/claude_sudoers
cd /root
curl -Lo github_meta.json https://api.github.com/meta
jq -r '(.api + .git + .web)[]' github_meta.json > github_ips
nft -f ./rules.nft
python3 ./add_ip_ranges_to_nft_sets.py claude_egress allowed_ipv4 allowed_ipv6 \
        < github_ips

# Make sure network protections are working.
set +e
curl https://www.google.com &>/dev/null
result=$?
set -e
if [ "$result" != 7 ]; then
     echo "We should not be able to get to Google" >&2
     exit 1
fi

# runuser sets up the environment for us.  Otherwise we'd have to
# bootstrap stuff like HOME ourselves.
exec setpriv \
    --bounding-set -net_admin,-setpcap \
    --inh-caps -all \
    --ambient -all \
    -- \
    runuser -u "$CLAUDE_USER" -g "$CLAUDE_USER" \
    -- \
    sh -lc 'cd && exec "$@"' -- "$@"

bash -l
