# Stage A Deploy — VPS + PostgreSQL

Minimal external deploy: one VPS, PostgreSQL, backend + frontend running via terminal.
No nginx, no SSL, no systemd required at this stage.

## Server requirements

- Ubuntu 22.04
- 2GB RAM minimum
- Ports 3000 and 8000 open in firewall

Recommended providers: DigitalOcean ($12/mo Droplet), Hetzner CX22 (~€4/mo).

## 1. Provision server

```bash
# On your local machine
ssh root@YOUR_SERVER_IP
```

## 2. Install dependencies

```bash
apt-get update
apt-get install -y python3.11 python3.11-venv python3-pip nodejs npm postgresql git
```

## 3. Set up PostgreSQL

```bash
systemctl start postgresql
systemctl enable postgresql

sudo -u postgres psql << 'SQL'
CREATE USER landing_reply WITH PASSWORD 'choose_a_strong_password';
CREATE DATABASE landing_reply_db OWNER landing_reply;
GRANT ALL PRIVILEGES ON DATABASE landing_reply_db TO landing_reply;
\q
SQL
```

Verify:
```bash
psql -U landing_reply -d landing_reply_db -h localhost -c "SELECT 1;"
```

## 4. Deploy code

```bash
git clone https://github.com/YOUR_REPO /srv/landing-reply
cd /srv/landing-reply
```

## 5. Backend

```bash
cd /srv/landing-reply/apps/api
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Create env file
cat > .env << 'ENV'
DATABASE_URL=postgresql://landing_reply:choose_a_strong_password@localhost:5432/landing_reply_db
OPENAI_API_KEY=sk-your-real-key
OPENAI_MODEL=gpt-4o-mini
SITE_URL=http://YOUR_SERVER_IP:3000
ENV

# Start (tables created automatically on first run)
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Keep running with `screen` or `tmux`:
```bash
screen -S api
uvicorn app.main:app --host 0.0.0.0 --port 8000
# Ctrl+A, D to detach
```

Verify: `curl http://YOUR_SERVER_IP:8000/health` → `{"status":"ok"}`

## 6. Frontend

```bash
cd /srv/landing-reply/apps/web

cat > .env.local << 'ENV'
NEXT_PUBLIC_API_URL=http://YOUR_SERVER_IP:8000
NEXT_PUBLIC_SITE_URL=http://YOUR_SERVER_IP:3000
ENV

npm install
npm run build
```

Start in a second screen session:
```bash
screen -S web
npm run start
# Ctrl+A, D to detach
```

Verify: `curl http://YOUR_SERVER_IP:3000/` → HTML response

## 7. Verify the full flow

```bash
# Create project
curl -X POST http://YOUR_SERVER_IP:8000/projects \
  -H "Content-Type: application/json" -d '{}' | jq .id

# Extract order (replace PROJECT_ID)
curl -X POST http://YOUR_SERVER_IP:8000/orders/extract \
  -H "Content-Type: application/json" \
  -d '{"project_id":"PROJECT_ID","raw_text":"Фотограф на регистрацию 11 июня в СПб, бюджет 15000"}'

# Generate landing (replace PROJECT_ID)
curl -X POST http://YOUR_SERVER_IP:8000/projects/PROJECT_ID/landing/generate \
  -H "Content-Type: application/json" -d '{}'
# → copy slug from response

# Open in browser
# http://YOUR_SERVER_IP:3000/r/SLUG
```

## Stage B (later)

When Stage A is validated, add:
- Nginx reverse proxy → single port 80/443
- SSL via Let's Encrypt (certbot)
- Systemd units for auto-restart

Files are already in `infrastructure/nginx/`, `infrastructure/systemd/`.
See comments in those files for setup instructions.
