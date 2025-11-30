#!/usr/bin/env bash

set -xeuo pipefail

nft -f /root/rules.nft

# Make sure network protections are working.
set +e

curl https://www.google.com >/dev/null
result=$?
if [ "$result" != 56 ]; then
     echo "We should not be able to get to Google through tinyproxy" >&2
     exit 1
fi

curl --noproxy '*' https://www.google.com >/dev/null
result=$?
if [ "$result" != 7 ]; then
     echo "We should not be able to get to Google directly" >&2
     exit 1
fi

set -e

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
