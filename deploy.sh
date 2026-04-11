#!/bin/bash
# Deploy Aquarela to Raspberry Pi
set -e

REPO_DIR="$(cd "$(dirname "$0")" && pwd)"
REMOTE="/home/pi/aquarela"

# Try mDNS first, fall back to direct ethernet IP
if ssh -o ConnectTimeout=3 pi@aquarela.local true 2>/dev/null; then
  PI="pi@aquarela.local"
elif ssh -o ConnectTimeout=3 pi@10.42.1.1 true 2>/dev/null; then
  PI="pi@10.42.1.1"
else
  echo "ERROR: Cannot reach Pi at aquarela.local or 10.42.1.1"
  exit 1
fi
echo "Using Pi at: $PI"

echo "=== Building frontend ==="
cd "$REPO_DIR/frontend"
npm run build

echo "=== Syncing to Pi ==="
cd "$REPO_DIR"
rsync -avz --delete \
  --exclude node_modules \
  --exclude .git \
  --exclude __pycache__ \
  --exclude venv \
  --exclude '*.pyc' \
  --exclude 'data/aquarela-config.json' \
  --exclude 'data/sessions' \
  --exclude 'data/aquarela.db*' \
  --exclude 'aquarela-android' \
  ./ "$PI:$REMOTE/"

echo "=== Restarting Aquarela ==="
ssh "$PI" "sudo systemctl restart aquarela"

echo "=== Done! http://aquarela.local:8080 ==="
