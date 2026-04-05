#!/bin/bash
# Simple HTTP file server script
# Usage: ./serve.sh [directory] [port]
# Default directory: ~/Downloads
# Default port: 8080

DIR="${1:-$HOME/Downloads}"
PORT="${2:-9081}"

# Resolve to absolute path
DIR="$(cd "$DIR" 2>/dev/null && pwd)"
if [ ! -d "$DIR" ]; then
    echo "Error: Directory '$1' does not exist"
    exit 1
fi

echo "Serving '$DIR' on http://0.0.0.0:$PORT"
python3 -m http.server "$PORT" --directory "$DIR" --bind 0.0.0.0
