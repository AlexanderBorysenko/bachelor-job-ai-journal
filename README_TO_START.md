# AI Diary — деплой

## Передумови

- VPS з Docker і Docker Compose
- Домен з HTTPS (reverse proxy через CloudPanel, Caddy, nginx тощо)
- Telegram-бот (створений через @BotFather)

## 1. Створити Telegram-бота

1. Відкрий **@BotFather** в Telegram → `/newbot`
2. Обери ім'я та username → отримаєш токен виду `7123456789:AAH...`
3. Число до `:` — це **Bot ID** (наприклад, `7123456789`)
4. `/setdomain` → обери бота → вкажи домен (наприклад, `journal.example.com`)

Домен обов'язковий — без нього вхід через Telegram на веб-інтерфейсі не працюватиме.

## 2. Отримати API ключі

| Ключ | Для чого | Де отримати |
|------|----------|-------------|
| `ANTHROPIC_API_KEY` | Claude API (генерація записів, хайлайтів) | https://console.anthropic.com → API Keys |
| `OPENAI_API_KEY` | Whisper API (транскрибація голосових) | https://platform.openai.com → API Keys |

## 3. Клонувати та налаштувати

```bash
git clone https://github.com/AlexanderBorysenko/bachelor-job-ai-journal.git ai-diary
cd ai-diary
cp .env.example .env
nano .env
```

Заповнити `.env`:

```env
MONGODB_URL=mongodb://mongodb:27017
MONGODB_DB_NAME=ai_diary

TELEGRAM_BOT_TOKEN=7123456789:AAHxxx_твій_токен
VITE_TELEGRAM_BOT_ID=7123456789
TELEGRAM_WEBHOOK_URL=https://journal.example.com/api/webhook/telegram

ANTHROPIC_API_KEY=sk-ant-api03-твій_ключ
CLAUDE_MODEL=claude-sonnet-4-6
OPENAI_API_KEY=sk-proj-твій_ключ

JWT_SECRET_KEY=
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

AUDIO_FILES_PATH=/app/audio_files
```

Згенерувати `JWT_SECRET_KEY`:

```bash
openssl rand -hex 32
```

## 4. Запустити

```bash
docker compose up -d --build
```

Перший запуск — 3-5 хв. Перевірити: `https://journal.example.com/api/health` → `{"status": "ok"}`.

## 5. Reverse proxy

Створити reverse proxy для домену на порт `3004` (або який вказано в `docker-compose.yml`).
Frontend nginx всередині контейнера сам проксює `/api/` запити на backend.

## 6. Зареєструвати webhook

```bash
curl -X POST "https://api.telegram.org/bot<ТОКЕН>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://journal.example.com/api/webhook/telegram"}'
```

Перевірити: `curl "https://api.telegram.org/bot<ТОКЕН>/getWebhookInfo"`

## 7. Перевірити роботу

- **Веб:** відкрити `https://journal.example.com` → "Увійти через Telegram" → авторизація
- **Бот:** знайти бота в Telegram → Start → надіслати повідомлення → `/bake`

---

## Оновлення

```bash
cd ai-diary
git pull
docker compose up -d --build
```

## Зупинка

```bash
docker compose down        # зберегти дані
docker compose down -v     # видалити дані
```

## Логи

```bash
docker compose logs -f           # всі сервіси
docker compose logs -f backend   # тільки backend
```

## Тести

```bash
docker compose exec backend python -m pytest tests/ -v
```

## Типові проблеми

| Проблема | Рішення |
|----------|---------|
| `port already in use` | Змінити порт у `docker-compose.yml` або зупинити конфлікт |
| Бот не відповідає | Перевірити webhook: `curl .../getWebhookInfo` |
| Telegram Login не працює | Перевірити домен у BotFather (`/setdomain`) |
| Помилка транскрибації | Перевірити `OPENAI_API_KEY`, баланс на platform.openai.com |
| Помилка запікання | Перевірити `ANTHROPIC_API_KEY`, баланс на console.anthropic.com |
| Біла сторінка | DevTools → Console, подивитись помилку |
