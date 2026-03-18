#!/usr/bin/env bash

set -euo pipefail

# Skip if disabled
if [ "${LLM_UPDATE_AGENTS:-1}" != "1" ]; then
    exit 0
fi

STATUS_DIR=$(mktemp -d)
export STATUS_DIR

update_agent() {
    local name="$1"
    local label="$2"
    shift 2
    echo "Updating $label..."
    local rc=0
    "$@" 2>&1 || rc=$?
    if [ "$rc" -eq 0 ]; then
        echo -e "\nSUCCESS"
        echo 0 > "$STATUS_DIR/$name"
    else
        echo -e "\nFAILED (exit code $rc)"
        echo 1 > "$STATUS_DIR/$name"
    fi
    sleep infinity
}

run_monitor() {
    while [ ! -f "$STATUS_DIR/claude" ] || [ ! -f "$STATUS_DIR/codex" ] || [ ! -f "$STATUS_DIR/copilot" ]; do
        sleep 0.5
    done

    failures=0
    for f in "$STATUS_DIR"/*; do
        [ "$(cat "$f")" != "0" ] && failures=$((failures + 1))
    done

    if [ "$failures" -eq 0 ]; then
        echo "All agents updated successfully!"
        sleep 2
        tmux kill-session -t updates
    else
        echo "$failures update(s) failed. Press Enter to continue..."
        read -r
        tmux kill-session -t updates
    fi
}

# Fallback: no tty or no tmux
if [ ! -t 0 ] || ! command -v tmux &>/dev/null; then
    echo "=== Updating agents (parallel) ==="

    update_simple() {
        local label="$1"
        shift
        echo "[$label] Updating..."
        if "$@" 2>&1 | sed "s/^/[$label] /"; then
            echo "[$label] SUCCESS"
        else
            echo "[$label] FAILED"
        fi
    }

    update_simple "Claude Code" bash -c 'curl -fsSL https://claude.ai/install.sh | bash' &
    update_simple "Codex" npm install -g @openai/codex &
    update_simple "Copilot CLI" npm install -g @github/copilot &
    wait
    rm -rf "$STATUS_DIR"
    exit 0
fi

# tmux UI
export -f update_agent run_monitor

tmux new-session -d -s updates -x "$(tput cols)" -y "$(tput lines)" \
    "bash -c 'update_agent claude \"Claude Code\" bash -c \"curl -fsSL https://claude.ai/install.sh | bash\"'"

tmux split-window -h -t updates \
    "bash -c 'update_agent codex \"Codex\" npm install -g @openai/codex'"

tmux split-window -h -t updates \
    "bash -c 'update_agent copilot \"Copilot CLI\" npm install -g @github/copilot'"

# Even out the top panes
tmux select-layout -t updates even-horizontal

# Bottom monitor pane (small)
tmux split-window -v -l 3 -t updates \
    "bash -c 'run_monitor'"

tmux attach -t updates

rm -rf "$STATUS_DIR"
