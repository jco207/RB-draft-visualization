#!/usr/bin/env bash
# Cloud Agent start step for RB-draft-visualization.
#
# Launches the Streamlit dashboard as an attached foreground process. If the
# virtualenv is missing (e.g. it was not preserved into a prebuilt snapshot),
# it is rebuilt first so the dashboard always comes up on a fresh boot.
set -euo pipefail

cd /workspace

VENV_DIR="${VENV_DIR:-$HOME/venv}"

if [ ! -x "$VENV_DIR/bin/streamlit" ]; then
  bash .cursor/install.sh
fi

exec "$VENV_DIR/bin/streamlit" run scripts/dashboard.py \
  --server.port 8501 \
  --server.address 0.0.0.0 \
  --server.headless true
