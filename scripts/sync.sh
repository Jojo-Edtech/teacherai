#!/usr/bin/env bash
set -euo pipefail

BRANCH="${1:-main}"
MSG_PREFIX="${2:-chore: sync from codex}"

if ! command -v git >/dev/null 2>&1; then
  echo "Git not found."
  exit 1
fi

git pull --rebase "origin" "$BRANCH"
git add .

if git diff --cached --quiet; then
  echo "No changes to sync."
  exit 0
fi

TIMESTAMP="$(date '+%Y-%m-%d %H:%M')"
COMMIT_MSG="${MSG_PREFIX} ${TIMESTAMP}"
git commit -m "$COMMIT_MSG"
git push origin "$BRANCH"

echo "Pushed changes to ${BRANCH}."
