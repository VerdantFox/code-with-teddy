#!/usr/bin/env bash
# Updates requirements-dev.txt and requirements-prod.txt dependencies to the
#   latest versions, and creates an updated local virtual environment at "venv/".
# shellcheck disable=SC2129

set -euo pipefail
cd "$(dirname "$0")/.."

echo "Updating requirements-prod.txt file..."
uv pip compile --upgrade --generate-hashes --output-file=requirements-prod.txt --quiet pyproject.toml
echo "Updating requirements-dev.txt file..."
uv pip compile --upgrade --generate-hashes --output-file=requirements-dev.txt --extra=dev --quiet pyproject.toml
echo "Syncing venv with requirements-dev.txt..."
uv pip sync requirements-dev.txt

if [[ $* == *--node* ]]; then  # --node flag
    echo "Updating node packages"
    ncu -u
    npm update
fi
