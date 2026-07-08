#!/usr/bin/env bash
set -euo pipefail

REPO_URL="git@github.com:Jojo-Edtech/teacherai.git"

git config --global user.name "Jojo-Edtech"
git config --global user.email "xinyanzjo@gmail.com"

git init
git remote remove origin 2>/dev/null || true
git remote add origin "$REPO_URL"
git branch -M main
git add .
git commit -m "init hk ai education site" || true
git push -u origin main

echo "First version uploaded to GitHub:"
echo "https://github.com/Jojo-Edtech/teacherai"
