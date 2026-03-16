#!/bin/bash
# One-time server setup script for Ubuntu 22.04
# Run as root on a fresh VPS
set -e

echo "=== Installing system packages ==="
apt-get update -qq
apt-get install -y python3.11 python3.11-venv python3-pip nodejs npm nginx postgresql postgresql-contrib certbot python3-certbot-nginx git

echo "=== Creating deploy user ==="
useradd -m -s /bin/bash deploy || true

echo "=== Setting up PostgreSQL ==="
# Start and enable postgres
systemctl enable postgresql
systemctl start postgresql

# Create DB and user (change password in production)
sudo -u postgres psql << 'SQL'
CREATE USER landing_reply WITH PASSWORD 'CHANGE_THIS_PASSWORD';
CREATE DATABASE landing_reply_db OWNER landing_reply;
GRANT ALL PRIVILEGES ON DATABASE landing_reply_db TO landing_reply;
SQL

echo "=== Creating env dirs ==="
mkdir -p /etc/landing-reply
chmod 750 /etc/landing-reply

echo "=== App directory ==="
mkdir -p /srv/landing-reply
chown deploy:deploy /srv/landing-reply

echo ""
echo "Server setup complete."
echo "Next: clone repo to /srv/landing-reply and run deploy.sh"
