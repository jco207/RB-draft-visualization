#!/usr/bin/env bash
# Cloud Agent install step for RB-draft-visualization.
#
# Runs after the repository is checked out into /workspace. It is idempotent and
# must terminate (no long-running processes here).
#
# The virtualenv is created OUTSIDE /workspace (at $VENV_DIR) on purpose: the
# per-boot git checkout can remove untracked files under /workspace, so a venv
# stored there would not survive. Keeping it in the home directory makes it
# stable across boots and prebuilt-environment snapshots.
set -euo pipefail

VENV_DIR="${VENV_DIR:-$HOME/venv}"

# The default base image ships Python 3 but not the venv/ensurepip module, so
# install it ourselves. This keeps the environment self-contained regardless of
# the base image.
if ! python3 -c "import ensurepip" >/dev/null 2>&1; then
  sudo apt-get update
  sudo apt-get install -y python3-venv
fi

python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r requirements.txt

echo "Install complete. Virtualenv: $VENV_DIR"
