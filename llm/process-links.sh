#!/usr/bin/env bash

set -euo pipefail

PERSIST_DIR="$HOME/.persist"
LINKS_FILE="$PERSIST_DIR/LINKS.txt"

# Create default LINKS.txt if it doesn't exist
if [ ! -f "$LINKS_FILE" ]; then
    cat > "$LINKS_FILE" <<'EOF'
# Files to symlink from ~/.persist into $HOME
# Each line is a path relative to $HOME (e.g. .bash_history)
.bash_history
.claude.json
.bashrc
EOF
fi

while IFS= read -r line || [ -n "$line" ]; do
    # Strip leading/trailing whitespace
    line="${line#"${line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"

    # Skip blank lines and comments
    [ -z "$line" ] && continue
    [[ "$line" == \#* ]] && continue

    # Security: reject paths with .. or absolute paths
    if [[ "$line" == /* ]] || [[ "$line" == *..* ]]; then
        echo "LINKS.txt: skipping unsafe path: $line" >&2
        continue
    fi

    persist_path="$PERSIST_DIR/$line"
    home_path="$HOME/$line"

    # Ensure .bash_history always exists in .persist so history is
    # persisted from the very first session.
    if [ "$line" = ".bash_history" ] && [ ! -e "$persist_path" ]; then
        mkdir -p "$(dirname "$persist_path")"
        touch "$persist_path"
    fi

    # Skip if the file doesn't exist in .persist
    [ -e "$persist_path" ] || continue

    # Create parent directories in $HOME as needed
    mkdir -p "$(dirname "$home_path")"

    # Already the correct symlink — skip
    if [ -L "$home_path" ] && [ "$(readlink "$home_path")" = "$persist_path" ]; then
        continue
    fi

    # Existing file or wrong symlink — back up
    if [ -e "$home_path" ] || [ -L "$home_path" ]; then
        mv "$home_path" "${home_path}.bak"
    fi

    ln -s "$persist_path" "$home_path"
done < "$LINKS_FILE"
