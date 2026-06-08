# Archivarius — AI Diary

A personal AI diary you talk to instead of write. Send text and voice notes to a Telegram bot throughout the day; whenever you're ready, hit **Bake** and Claude turns the day's scattered messages into one coherent, literary journal entry — then automatically extracts the ideas, stories, moods and insights worth remembering.

This is an independent pet project I build and run myself.

> **Core idea:** one entry = one day. Many messages collected through the day are merged, on bake, into a single connected entry for that date.

---

## Why

Keeping a diary is hard because writing is friction. Talking is not. Archivarius removes the writing step: you just dump thoughts (typed or spoken) into a chat as they happen, and the AI does the authoring, the date-sorting, and the curation later. Voice notes are transcribed; "we went to the cinema yesterday" lands on yesterday's page, not today's.

---

## Features

**Capture (Telegram bot)**
- 📝 **Text messages** — written straight into the day's buffer
- 🎙️ **Voice messages** — transcribed via OpenAI Whisper, then buffered
- 🖼️ **Media** — photos and attachments stored and woven into the baked entry
- 🧠 **Smart date classification** — Claude decides which day each message belongs to ("yesterday", "last Friday", …), so entries land on the right date

**Bake (the core process)**
- 🔥 **On-demand baking** — pending messages are grouped by date and rewritten into literary diary entries
- ➕ **Incremental entries** — bake again later and new messages are merged into the existing entry for that day (versioned)
- ✨ **Auto-highlights** — after baking, Claude extracts highlights tagged `idea` / `story` / `mood` / `insight` (plus your own custom categories)
- 📡 **Live progress** — bake status is pushed to the web UI in real time over Server-Sent Events; restart/reload-safe via a persistent bake job

**Browse (web app)**
- 📖 **Diary** — read your baked entries, rendered from typed content blocks (text, figures, galleries)
- 🗂️ **Buffer** — see and manage pending messages before baking
- 💡 **Highlights** — browse the extracted highlights across entries
- ⚙️ **Settings** — manage custom highlight categories and account
- 🔐 **Telegram login** — sign in with your Telegram account; protected media served behind an httpOnly cookie
- 🌍 **Multilingual** — UI and bot adapt to the user's language

**Bot commands**

| Command  | Action |
| -------- | ------ |
| `/start` | Register / welcome |
| `/bake`  | Turn buffered messages into diary entries |
| `/skip`  | Skip the current buffered item |
| `/web`   | Get a link to the web app |
| `/help`  | Show help |

---

## How it works

```
Telegram  ──►  Buffer (raw_messages)  ──►  Bake (Claude)  ──►  Entries  ──►  Highlights
  text                  ▲                        │                 │
  voice ─► Whisper ─────┘                        ▼                 ▼
  media ─► storage ─────┘                   one entry per day   web UI (SSE)
```

1. **Collect** — messages arrive via the Telegram webhook. Voice is transcribed (Whisper), media is stored, and Claude classifies each message's date. Everything lands in a buffer with `status: pending`.
2. **Accumulate** — messages pile up in `raw_messages`, grouped by classified date.
3. **Bake** — on command, all pending messages per date are sent to Claude, which writes (or extends) that day's entry as typed content blocks. Highlights are then extracted per entry. Progress streams to the web UI.

The full architecture — sequence diagrams, the MongoDB collection model, and the SSE event bus — lives in [architecture.md](../architecture.md).

---

## Tech stack

| Layer     | Tech |
| --------- | ---- |
| Bot + API | Python 3.12, FastAPI, aiogram 3.x — a single process serves the Telegram webhook **and** the REST API |
| AI        | Anthropic Claude (bake / highlights — Sonnet; date classification — Haiku) + OpenAI Whisper (transcription) |
| Database  | MongoDB 7 (Beanie / Motor async ODM) |
| Frontend  | Vue 3 + TypeScript, Vite, Tailwind CSS |
| Realtime  | Server-Sent Events (in-process asyncio pub/sub event bus) |
| Deploy    | Docker Compose (frontend nginx · backend · mongodb) |

---

## Setup

The app is a Docker Compose stack (frontend nginx · backend · MongoDB) — the same stack runs locally and on a server. The difference is only how the outside world reaches it.

### Prerequisites

- Docker + Docker Compose
- A Telegram bot — create one via [@BotFather](https://t.me/BotFather) (`/newbot`)
- An Anthropic API key ([console.anthropic.com](https://console.anthropic.com)) and an OpenAI API key ([platform.openai.com](https://platform.openai.com))

### 1. Clone and configure

```bash
git clone https://github.com/AlexanderBorysenko/my-archivarius.git ai-diary
cd ai-diary
cp .env.example .env
nano .env
```

Fill in `.env`:

| Key | Purpose |
| --- | ------- |
| `TELEGRAM_BOT_TOKEN` | Bot token from @BotFather (`7123456789:AAH...`) |
| `VITE_TELEGRAM_BOT_ID` | Numeric part before `:` in the token (used by Telegram web login) |
| `TELEGRAM_WEBHOOK_URL` | `https://your-domain.com/api/webhook/telegram` (or your tunnel URL) |
| `ANTHROPIC_API_KEY` | Claude — baking, highlights, date classification |
| `OPENAI_API_KEY` | Whisper — voice transcription |
| `MONGODB_URL` / `MONGODB_DB_NAME` | Database connection (defaults work as-is) |
| `JWT_SECRET_KEY` | Session signing — generate with `openssl rand -hex 32` |
| `COOKIE_SECURE` | `true` for production (HTTPS); `false` for local http dev |

---

## Run locally

For developing and testing on your own machine.

1. In `.env` set `COOKIE_SECURE=false` (media cookies need this over plain http).
2. Start the stack:

   ```bash
   docker compose up -d --build       # first build takes 3–5 min
   ```

3. Open:
   - **Web** → `http://localhost:3004`
   - **API health** → `http://localhost:8000/api/health` → `{"status": "ok"}`
   - **MongoDB** → `localhost:27017`

The frontend's nginx proxies `/api` to the backend, so both share one origin.

**Reaching the bot locally.** Telegram can't deliver webhooks to `localhost`. To test the bot from your machine, expose port `3004` with a tunnel and point the webhook at it:

```bash
cloudflared tunnel --url http://127.0.0.1:3004        # prints a https://*.trycloudflare.com URL
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://<TUNNEL>.trycloudflare.com/api/webhook/telegram"}'
```

(Telegram web login also needs a real HTTPS domain registered via `/setdomain` — for pure local dev you can skip login and exercise the API directly.)

---

## Run on a server (production)

For a public, always-on deployment on a VPS.

### 1. Telegram bot domain

In @BotFather: `/setdomain` → select your bot → enter your domain (e.g. `journal.example.com`). Required — Telegram web login does not work without it.

### 2. Deploy the stack

```bash
git clone https://github.com/AlexanderBorysenko/my-archivarius.git ai-diary
cd ai-diary
cp .env.example .env && nano .env     # COOKIE_SECURE=true, real domain in TELEGRAM_WEBHOOK_URL
docker compose up -d --build
```

### 3. Reverse proxy + HTTPS

Put a reverse proxy (CloudPanel / Caddy / nginx) in front of port `3004` and terminate HTTPS for your domain. The frontend container proxies `/api/` to the backend internally — only `3004` needs to be exposed.

Verify: `https://your-domain.com/api/health` → `{"status": "ok"}`.

### 4. Register the Telegram webhook

Telegram **does not** deliver webhooks to IPs inside its own ranges (`91.108.0.0/16`, `149.154.160.0/20`) — an SSRF guard. Check your server: `dig your-domain.com +short`.

**If your IP is _not_ in those ranges** — set the webhook directly:

```bash
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-domain.com/api/webhook/telegram"}'
```

**If your IP _is_ in those ranges** — route the webhook through a Cloudflare Tunnel as a persistent systemd service:

```bash
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 \
  -o /usr/local/bin/cloudflared && chmod +x /usr/local/bin/cloudflared

sudo tee /etc/systemd/system/cloudflared-tunnel.service > /dev/null <<'EOF'
[Unit]
Description=Cloudflare Tunnel for Telegram Webhook
After=network.target docker.service
[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/cloudflared tunnel --url http://127.0.0.1:3004
Restart=always
RestartSec=10
[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload && sudo systemctl enable --now cloudflared-tunnel

# grab the generated URL, then point the webhook at it
journalctl -u cloudflared-tunnel --no-pager -n 20 | grep trycloudflare.com
curl -X POST "https://api.telegram.org/bot<TOKEN>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://<TUNNEL>.trycloudflare.com/api/webhook/telegram"}'
```

> A free-tier Quick Tunnel generates a **new URL on every restart**, so you must re-run `setWebhook` after a reboot. For a stable URL, create a free Cloudflare account and configure a Named Tunnel. A `docker compose` redeploy does **not** restart the tunnel.

Check it: `curl "https://api.telegram.org/bot<TOKEN>/getWebhookInfo"` → expect `"pending_update_count": 0`.

### 5. Smoke test

- **Web** → open your domain → "Log in with Telegram" → authorize
- **Bot** → find your bot → `/start` → send a message → `/bake`

---

## Operating

```bash
docker compose up -d --build        # start / rebuild (also: deploy an update after git pull)
docker compose logs -f              # tail all services
docker compose logs -f backend      # tail backend only
docker compose down                 # stop (keep data)
docker compose down -v              # stop and wipe data
docker compose exec backend python -m pytest tests/ -v   # run tests
```

Update a running deployment:

```bash
git pull && docker compose up -d --build
```

### Troubleshooting

| Symptom | Fix |
| ------- | --- |
| `port already in use` | Change the port in `docker-compose.yml` or stop the conflicting service |
| Bot doesn't respond | Check the webhook: `curl .../getWebhookInfo` |
| Webhook `Connection timed out` | Server IP is in Telegram's range — use a Cloudflare Tunnel (server step 4) |
| Webhook URL changed after reboot | Quick Tunnel issued a new URL — re-run `setWebhook` or switch to a Named Tunnel |
| Telegram login fails | Re-check the domain in @BotFather (`/setdomain`) |
| Transcription error | Check `OPENAI_API_KEY` and balance at platform.openai.com |
| Bake error | Check `ANTHROPIC_API_KEY` and balance at console.anthropic.com |
| Blank page | Open DevTools → Console for the error |

---

## Project layout

```
ai-diary/
├── backend/            # FastAPI + aiogram (Python 3.12)
│   └── app/{api,bot,core,models,services}
├── frontend/           # Vue 3 + TypeScript (Vite)
│   └── src/{views,components,api,stores,utils}
└── docker-compose.yml
```

---

## License

Personal project — all rights reserved.
