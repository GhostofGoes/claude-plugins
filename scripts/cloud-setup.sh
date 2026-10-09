#!/bin/bash
# Setup script for a personal Claude Code cloud environment (claude.ai/code).
# It clones this marketplace into the VM, and the environment variable
#   CLAUDE_CODE_PLUGIN_DIRS=/opt/claude-plugins/plugins/lead-coder
# makes the session load the lead-coder plugin from there. Nothing is written
# to the project repository.
#
# A setup script that exits non-zero stops the session from starting, so a
# failed clone or pull only logs a warning and the script always exits 0.

dir="${CLAUDE_PLUGINS_CHECKOUT:-/opt/claude-plugins}"

if [ -d "$dir/.git" ]; then
  git -C "$dir" pull --ff-only --quiet ||
    echo "claude-plugins: pull failed, keeping the existing checkout" >&2
else
  git clone --depth 1 --quiet https://github.com/GhostofGoes/claude-plugins "$dir" ||
    echo "claude-plugins: clone failed, lead-coder will be missing" >&2
fi

exit 0
