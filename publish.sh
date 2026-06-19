#!/usr/bin/env bash
#
# publish.sh — Initialize the APVA repository and push it to GitHub.
#
# Prerequisites:
#   * git installed
#   * GitHub CLI (gh) installed and authenticated (`gh auth status`)
#
# Usage:
#   ./publish.sh [repo-name]
#
# If [repo-name] is omitted, defaults to "apva-framework".

set -Eeuo pipefail

REPO_NAME="${1:-apva-framework}"
COMMIT_MSG="feat: Initial commit of APVA framework MVP"

log()  { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
fail() { printf '\033[1;31mERROR:\033[0m %s\n' "$*" >&2; exit 1; }

# --- Preflight checks -------------------------------------------------------
command -v git >/dev/null 2>&1 || fail "git is not installed."
command -v gh  >/dev/null 2>&1 || fail "GitHub CLI (gh) is not installed."

if ! gh auth status >/dev/null 2>&1; then
  fail "GitHub CLI is not authenticated. Run: gh auth login"
fi

# Run from the directory this script lives in (the repo root).
cd "$(dirname "$0")"

# --- Local verification before publishing -----------------------------------
if command -v pytest >/dev/null 2>&1; then
  log "Running test suite before publishing..."
  pytest -q || fail "Tests failed — aborting publish."
else
  log "pytest not found on PATH; skipping pre-publish test run."
fi

# --- Git lifecycle ----------------------------------------------------------
if [ -d .git ]; then
  log "Git repository already initialized; reusing it."
else
  log "Initializing git repository..."
  git init -b main
fi

log "Staging files..."
git add .

if git diff --cached --quiet; then
  log "No staged changes to commit."
else
  log "Creating initial commit..."
  git commit -m "${COMMIT_MSG}"
fi

# --- Create remote + push ----------------------------------------------------
if git remote get-url origin >/dev/null 2>&1; then
  log "Remote 'origin' already exists; pushing to it..."
  git push -u origin HEAD
else
  log "Creating public GitHub repo '${REPO_NAME}' and pushing..."
  gh repo create "${REPO_NAME}" --public --source=. --remote=origin --push
fi

log "Done. Repository published as '${REPO_NAME}'."
