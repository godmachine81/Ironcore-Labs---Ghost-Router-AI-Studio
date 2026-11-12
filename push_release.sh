#!/usr/bin/env bash
set -e

GITHUB_USER="godmachine81"
GITHUB_EMAIL="tekpros@proton.me"
REPO_NAME="ironcore-ghost-router"

cd "$(dirname "$0")"

echo "[*] Configuring Git user identity..."
git config user.name "$GITHUB_USER"
git config user.email "$GITHUB_EMAIL"

echo "[*] Initializing repository / checking status..."
if [ ! -d ".git" ]; then
    git init
    git branch -M main
fi

git add ghost_router_proxy_clean.c ghost_upstream_relay.py IronCore_Labs_Ghost_Router_Architecture_Spec.md test_harness.py

echo "[*] Committing release v8.0..."
git commit -m "feat(core): release IronCore Labs Ghost Router v8.0 with native Google AI Studio & ephemeral C proxy" || echo "No changes to commit"

echo "[*] Tagging v8.0..."
git tag -d v8.0 2>/dev/null || true
git tag -a v8.0 -m "IronCore Labs Ghost Router v8.0 - Production Sovereign Release"

echo "[*] Setting remote origin to git@github.com:$GITHUB_USER/$REPO_NAME.git..."
git remote remove origin 2>/dev/null || true
git remote add origin git@github.com:$GITHUB_USER/$REPO_NAME.git

echo "[*] Pushing to GitHub..."
git push -u origin main --tags

echo "[+] Success! Repository pushed and tagged on GitHub."
