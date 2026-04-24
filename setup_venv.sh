#!/usr/bin/env bash
# setup_venv.sh — Create a virtual environment and install project dependencies.
#
# Usage:
#   bash setup_venv.sh
#
# After running, activate the environment with:
#   source venv/bin/activate
# Exit immediately if any command fails so we don't silently continue with a
# broken environment.
set -e

# Resolve the project root regardless of where the script is called from, then
# change into it so relative paths (venv/, requirements.txt) always work.
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Creating virtual environment..."
python3 -m venv venv

echo "Activating and installing dependencies..."
# SC1091: shellcheck cannot follow the dynamically-generated venv path, so we
# suppress the warning rather than letting it fail in CI lint checks.
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
