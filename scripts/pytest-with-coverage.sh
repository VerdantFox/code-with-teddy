#!/usr/bin/env bash
# pytest-with-coverage: run pytests with coverage to receive a coverage report

cd "$(dirname "$0")/.."
set -euo pipefail

python -m pytest tests/ \
    --cov-report=term \
    --cov-report=html \
    --cov=tests \
    --cov=app \
    "$@"

rm .coverage
