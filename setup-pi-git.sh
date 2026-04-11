#!/bin/bash
# One-time setup: initialize git repo on Pi and connect to GitHub
# Run from Mac while connected to Pi: bash setup-pi-git.sh
set -e

PI="pi@10.42.1.1"
REMOTE="/home/pi/aquarela"

echo "=== Setting up git on Pi ==="

ssh "$PI" bash -s <<'SCRIPT'
cd /home/pi/aquarela

# Init repo if not already
if [ ! -d .git ]; then
    git init
    git config user.email "pi@aquarela.local"
    git config user.name "Aquarela Pi"
fi

# Add remote
git remote remove origin 2>/dev/null || true
git remote add origin https://github.com/tommymancer/regata-software.git

# Fetch and reset to match remote
git fetch origin master
git reset --hard origin/master

# Install npm if frontend needs building
if [ -d frontend ] && ! command -v npm &>/dev/null; then
    echo "WARNING: npm not found — frontend builds will be skipped"
fi

echo "=== Git setup complete ==="
git log --oneline -3
SCRIPT
