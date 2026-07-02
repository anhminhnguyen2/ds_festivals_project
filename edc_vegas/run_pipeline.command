#!/bin/zsh
# Double-clickable pipeline launcher (macOS opens .command files in Terminal).
cd "$(dirname "$0")"
python3 run_pipeline.py "$@"
echo ""
read "?Pipeline finished - press Enter to close..."
