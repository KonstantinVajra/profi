#!/bin/bash

set -e

echo "→ Building frontend"
npm run build

echo "→ Sync static for standalone"
rm -rf .next/standalone/.next/static
mkdir -p .next/standalone/.next
cp -R .next/static .next/standalone/.next/static

if [ -d public ]; then
  rm -rf .next/standalone/public
  cp -R public .next/standalone/public
fi

echo "→ Restarting server"
pkill -f "standalone/server.js" || true
nohup node .next/standalone/server.js > web.log 2>&1 &

echo "✅ Deploy done"