#!/usr/bin/env bash
# setup_venv.sh — Create a virtual environment and install project dependencies.
#
# Usage:
#   bash setup_venv.sh
#
# After running, activate the environment with:
#   source venv/bin/activate
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Creating virtual environment..."
python3 -m venv venv

echo "Activating and installing dependencies..."
# shellcheck disable=SC1091
source venv/bin/activate
pip install --upgrade pip --quiet
pip install -r requirements.txt --quiet

echo ""
echo "Setup complete."
echo "Activate with:  source venv/bin/activate"
echo "Clean data:     python scripts/clean_draft.py <draft.csv>"
echo "Run dashboard:  streamlit run scripts/dashboard.py"
echo "Run tests:      pytest tests/"
