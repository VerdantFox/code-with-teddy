#!/usr/bin/env bash
# Updates requirements-dev.txt and requirements-prod.txt dependencies to the
#   latest versions, and creates an updated local virtual environment at "venv/".
# shellcheck disable=SC2129

# --allow-unsafe: allows pinning pip, setuptools, and distribute.
#   Does not otherwise affect hashes or safety of installation.

set -euo pipefail
cd "$(dirname "$0")/.."

echo "Updating requirements-prod.txt file..."
pip-compile --quiet --upgrade --strip-extras --generate-hashes --allow-unsafe --resolver=backtracking --output-file=requirements-prod.txt pyproject.toml
echo "Updating requirements-dev.txt file..."
pip-compile --quiet --upgrade --strip-extras --generate-hashes --allow-unsafe --resolver=backtracking --output-file=requirements-dev.txt --extra dev pyproject.toml
echo "Syncing venv with requirements-dev.txt..."
pip-sync requirements-dev.txt
