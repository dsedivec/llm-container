#!/bin/bash
exec docker run --rm -it \
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
     "$@" \
    llm
