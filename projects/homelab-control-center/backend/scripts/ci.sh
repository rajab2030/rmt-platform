#!/usr/bin/env bash
#
# RMT Control Center -- CI gate (production-readiness item V2).
#
# One command that proves the backend tree is green and reproducible:
#   1. build a fresh venv strictly from requirements.lock.txt  (reproducible install)
#   2. ruff lint, errors-only  (config: backend/ruff.toml -- select F,E9; app/core excluded)
#   3. the full backend test suite  (includes the 122 frozen-Core tests)
#
# Exit 0  -> green; safe to merge / deploy.
# Exit !0 -> the tree must not merge / deploy; the failing step is the last output.
#
# Usage:
#   scripts/ci.sh          # full gate in a throwaway venv (what CI runs)
#   scripts/ci.sh --fast   # reuse backend/.venv, skip the reinstall (quick local check)
#
# Invoked by .github/workflows/ci.yml; also runnable by hand from anywhere.

set -euo pipefail

RUFF_VERSION="0.14.2"   # pinned; CI tooling only -- deliberately not in requirements.lock.txt

BACKEND="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$BACKEND"

FAST=0
if [ "${1:-}" = "--fast" ]; then
    FAST=1
elif [ -n "${1:-}" ]; then
    echo "usage: scripts/ci.sh [--fast]" >&2
    exit 2
fi

step() { printf '\n\033[1m==> %s\033[0m\n' "$1"; }

if [ "$FAST" -eq 1 ]; then
    VENV="$BACKEND/.venv"
    [ -x "$VENV/bin/python" ] || { echo "no $VENV -- run without --fast first" >&2; exit 2; }
    step "--fast: reusing $VENV (no reinstall)"
    "$VENV/bin/pip" install --quiet "ruff==$RUFF_VERSION"
else
    VENV="$(mktemp -d)/venv"
    trap 'rm -rf "$(dirname "$VENV")"' EXIT
    step "creating throwaway venv: $VENV"
    python3 -m venv "$VENV"
    "$VENV/bin/pip" install --quiet --upgrade pip
    step "installing from requirements.lock.txt (reproducible)"
    "$VENV/bin/pip" install --quiet -r requirements.lock.txt
    "$VENV/bin/pip" install --quiet "ruff==$RUFF_VERSION"
fi

PY="$VENV/bin/python"

step "python / tool versions"
"$PY" --version
"$VENV/bin/ruff" --version

step "lint: ruff (errors-only -- see ruff.toml)"
"$VENV/bin/ruff" check .

step "test: full backend suite (app/ -- includes 122 frozen-Core tests)"
PYTHONPATH=. "$PY" -m pytest -q

step "CI gate PASSED"
