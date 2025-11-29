#!/usr/bin/env bash

set -xeuo pipefail

cat /etc/sudoers.d/llm_sudoers
cd /root
curl -Lo github_meta.json https://api.github.com/meta
jq -r '(.api + .git + .web)[]' github_meta.json > github_ips
nft -f ./rules.nft
python3 ./add_ip_ranges_to_nft_sets.py llm_egress allowed_ipv4 allowed_ipv6 \
        < github_ips

# Make sure network protections are working.
set +e
curl https://www.google.com >/dev/null
result=$?
set -e
if [ "$result" != 56 ]; then
     echo "We should not be able to get to Google through tinyproxy" >&2
     exit 1
fi

# Make llm's own files readable/writable by llm.
chown -R "$LLM_USER:$LLM_USER" "$LLM_HOME_DIR"

# runuser sets up the environment for us.  Otherwise we'd have to
# bootstrap stuff like HOME ourselves.
exec setpriv \
    --bounding-set -net_admin,-setpcap \
    --inh-caps -all \
    --ambient -all \
    -- \
    runuser -u "$LLM_USER" -g "$LLM_USER" \
    -- \
    sh -lc 'cd && exec "$@"' -- "$@"

bash -l
