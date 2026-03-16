#!/bin/bash
# Deploy script — run as deploy user on the server
# Usage: ./deploy.sh
set -e

APP_DIR="/srv/landing-reply"
cd "$APP_DIR"

echo "=== Backend: install dependencies ==="
cd apps/api
python3.11 -m venv .venv
.venv/bin/pip install -q --upgrade pip
.venv/bin/pip install -q -r requirements.txt
cd "$APP_DIR"

echo "=== Frontend: install and build ==="
cd apps/web
npm ci --quiet
npm run build
cd "$APP_DIR"

echo "=== Installing systemd units ==="
sudo cp infrastructure/systemd/landing-reply-api.service /etc/systemd/system/
sudo cp infrastructure/systemd/landing-reply-web.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable landing-reply-api landing-reply-web

echo "=== Restarting services ==="
sudo systemctl restart landing-reply-api
sudo systemctl restart landing-reply-web

echo "=== Installing nginx config ==="
sudo cp infrastructure/nginx/landing-reply.conf /etc/nginx/sites-available/landing-reply
sudo ln -sf /etc/nginx/sites-available/landing-reply /etc/nginx/sites-enabled/landing-reply
sudo nginx -t && sudo systemctl reload nginx

echo ""
echo "Deploy complete."
echo "Check: sudo systemctl status landing-reply-api landing-reply-web"
