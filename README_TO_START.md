# AI Diary — інструкція з запуску

## Передумови (для будь-якого режиму)

**Docker і Docker Compose** — обов'язково. Все інше залежить від режиму запуску.

Встановити Docker Desktop для macOS: https://docs.docker.com/desktop/install/mac-install/

Після встановлення перевір у терміналі:

```bash
docker --version
docker compose version
```

## Отримання API ключів

Потрібно 3 ключі. Всі безкоштовні для обмеженого використання (або мають trial).

### 1. Telegram Bot Token

Потрібен для прийому повідомлень від користувача.

1. Відкрий Telegram, знайди бота **@BotFather**
2. Напиши `/newbot`
3. Обери ім'я (наприклад, "Мій AI Щоденник") і username (наприклад, `my_ai_diary_bot`)
4. BotFather дасть токен виду `7123456789:AAH...` — збережи його
5. Число до `:` в токені — це Bot ID (наприклад, `7123456789`). Він потрібен для `VITE_TELEGRAM_BOT_ID`

### 2. Anthropic API Key (Claude)

Потрібен для класифікації дат, генерації тексту щоденника та виділення хайлайтів.

1. Зареєструйся на https://console.anthropic.com
2. Settings → API Keys → Create Key
3. Скопіюй ключ виду `sk-ant-api03-...`

### 3. OpenAI API Key (Whisper)

Потрібен для транскрибації голосових повідомлень у текст.

1. Зареєструйся на https://platform.openai.com
2. API Keys → Create new secret key
3. Скопіюй ключ виду `sk-proj-...`

---

# Режим A: Локальна розробка (на своєму комп'ютері)

Підходить для тестування, розробки, демонстрації на захисті з ноутбука.

### A.1. Створити .env

У папці `ai-diary/` виконай:

```bash
cp .env.example .env
```

Відкрий `.env` у текстовому редакторі та заповни:

```env
# MongoDB — залишити як є, Docker сам підніме базу
MONGODB_URL=mongodb://mongodb:27017
MONGODB_DB_NAME=ai_diary

# Telegram Bot — вставити свій токен від BotFather
TELEGRAM_BOT_TOKEN=7123456789:AAHxxx_твій_токен
VITE_TELEGRAM_BOT_ID=7123456789

# Webhook — ПОКИ ЗАЛИШИТИ ПОРОЖНІМ, заповниш на кроці A.3
TELEGRAM_WEBHOOK_URL=

# Claude API — вставити свій ключ
ANTHROPIC_API_KEY=sk-ant-api03-твій_ключ
CLAUDE_MODEL=claude-sonnet-4-20250514

# Whisper — вставити свій ключ
OPENAI_API_KEY=sk-proj-твій_ключ

# JWT — згенерувати секрет (або просто придумати довгий рядок)
JWT_SECRET_KEY=
JWT_ALGORITHM=HS256
JWT_ACCESS_TOKEN_EXPIRE_MINUTES=60
JWT_REFRESH_TOKEN_EXPIRE_DAYS=30

# Audio — залишити як є
AUDIO_FILES_PATH=/app/audio_files
```

Для генерації `JWT_SECRET_KEY`:

```bash
openssl rand -hex 32
```

Вставити результат у .env.

### A.2. Запустити

```bash
cd ai-diary
docker compose up --build
```

Перший запуск займе 3-5 хвилин (качає Docker-образи та залежності). Наступні запуски — швидші.

Коли в логах з'явиться:

```
backend-1   | INFO:     Uvicorn running on http://0.0.0.0:8000
```

перевір що все працює:

- http://localhost:8000/api/health — має повернути `{"status": "ok"}`
- http://localhost:8000/docs — Swagger UI з усіма ендпоінтами
- http://localhost:3000 — веб-інтерфейс

### A.3. Підключити Telegram-бота (ngrok)

**Навіщо це потрібно:** коли ти пишеш боту в Telegram, серверам Telegram потрібно кудись надіслати твоє повідомлення. Вони надсилають його на URL (webhook), який ти вкажеш. Але `localhost` видно тільки з твого комп'ютера — Telegram до нього достукатися не може.

**ngrok** — це маленька утиліта яка створює тимчасовий тунель: дає тобі публічну HTTPS-адресу, а все що на неї приходить — перенаправляє на твій localhost. Тобто: Telegram → ngrok (інтернет) → твій комп'ютер.

**Встановлення ngrok** (один з варіантів):

- Через Homebrew: `brew install ngrok`
- Або скачати напряму: https://ngrok.com/download → macOS → розпакувати і перемістити у `/usr/local/bin/`
- Потрібна безкоштовна реєстрація на ngrok.com для отримання authtoken

Після встановлення, одноразово прив'язати authtoken:

```bash
ngrok config add-authtoken ТВІЙ_ТОКЕН_З_NGROK_DASHBOARD
```

**Запуск тунеля** — в окремому вікні терміналу (не закривай його):

```bash
ngrok http 3000
```

ngrok покаже щось таке:

```
Forwarding  https://a1b2c3d4.ngrok-free.app → http://localhost:3000
```

Тепер:

1. Скопіюй цей URL у `.env`:

    ```env
    TELEGRAM_WEBHOOK_URL=https://a1b2c3d4.ngrok-free.app/api/webhook/telegram
    ```

2. Налаштуй домен для Telegram Login у BotFather:

    - Відкрий **@BotFather** → `/setdomain`
    - Обери свого бота
    - Вкажи домен ngrok **без https://** (наприклад, `a1b2c3d4.ngrok-free.app`)

    **Без цього кроку вхід через Telegram на веб-інтерфейсі не працюватиме.**

3. Перезапусти backend:

    ```bash
    docker compose restart backend
    ```

4. Зареєструй webhook у Telegram (одна команда в терміналі, замінити `<ТОКЕН>` і `<NGROK_URL>`):

    ```bash
    curl -X POST "https://api.telegram.org/bot<ТОКЕН>/setWebhook" \
      -H "Content-Type: application/json" \
      -d '{"url": "<NGROK_URL>/api/webhook/telegram"}'
    ```

    curl -X POST "https://api.telegram.org/bot8617169441:AAH9Tc4rsm6_i8-ZlGzm4-wijI8kCJfzp9I/setWebhook" \
     -H "Content-Type: application/json" \
     -d '{"url": "https://dimple-goofy-plausibly.ngrok-free.dev/api/webhook/telegram"}'

    Приклад:

    ```bash
    curl -X POST "https://api.telegram.org/bot7123456789:AAHxxx/setWebhook" \
      -H "Content-Type: application/json" \
      -d '{"url": "https://a1b2c3d4.ngrok-free.app/api/webhook/telegram"}'
    ```

    Відповідь `{"ok": true, ...}` — все працює.

**Важливо:** ngrok дає нову адресу при кожному запуску. Якщо перезапустив ngrok — повтори кроки 2 і 4 з новим URL (оновити домен у BotFather та webhook).

### A.4. Тестування

**Telegram Bot:**

1. Знайди свого бота в Telegram → натисни Start
2. Надішли текстове повідомлення → бот відповість "✅ Записано!"
3. Надішли голосове → бот відповість "🎙️ Отримано голосове..." → через кілька секунд "✅ Голосове транскрибовано та записано!"
4. Напиши `/bake` → бот запече все в літературний запис

**Web-інтерфейс:**

**Важливо:** Telegram Login не працює на `localhost`. Для входу через Telegram потрібно відкривати сайт через ngrok URL (наприклад, `https://a1b2c3d4.ngrok-free.app`).

1. Відкрий ngrok URL у браузері → натисни "Увійти через Telegram" → відбудеться OAuth-авторизація
2. "Буфер" — тут будуть повідомлення надіслані боту (ще не запечені)
3. "Щоденник" — записи після bake, навігація по датах
4. "Хайлайти" — ідеї, настрої, інсайти виділені з записів

**Unit-тести:**

```bash
docker compose exec backend pip install pytest pytest-asyncio mongomock-motor
docker compose exec backend python -m pytest tests/ -v
```

### A.5. Зупинити

```bash
docker compose down
```

Дані MongoDB зберігаються у Docker volume і не зникнуть після зупинки. Щоб видалити і дані:

```bash
docker compose down -v
```

---

# Режим B: Деплой на сервер (production)

Підходить для постійної роботи — бот доступний 24/7, ngrok не потрібен.

### B.1. Що потрібно

- VPS сервер (DigitalOcean, Hetzner, AWS EC2 тощо) — Ubuntu 22.04+, мінімум 1 GB RAM
- Домен (або субдомен), наприклад `diary.example.com`
- Docker і Docker Compose на сервері
- SSL-сертифікат (Telegram вимагає HTTPS для webhook)

### B.2. Встановити Docker на сервер

```bash
# На сервері (Ubuntu)
sudo apt update
sudo apt install -y docker.io docker-compose-plugin
sudo usermod -aG docker $USER
# Перелогінитись або newgrp docker
```

### B.3. Перенести проєкт на сервер

```bash
# На локальному комп'ютері
scp -r ai-diary/ user@ваш-сервер:~/ai-diary/
```

Або через git:

```bash
# На сервері
git clone <url-репозиторію> ai-diary
```

### B.4. Створити .env на сервері

```bash
cd ~/ai-diary
cp .env.example .env
nano .env
```

Заповнити так само як для локального режиму, але `TELEGRAM_WEBHOOK_URL` тепер вказує на реальний домен:

```env
TELEGRAM_WEBHOOK_URL=https://diary.example.com/api/webhook/telegram
```

Для production обов'язково згенерувати надійний JWT_SECRET_KEY:

```bash
openssl rand -hex 32
```

### B.5. Налаштувати SSL (HTTPS)

Telegram вимагає HTTPS для webhook. Найпростіший варіант — Caddy як reverse proxy (автоматично отримує SSL-сертифікат від Let's Encrypt).

Створити `Caddyfile` у папці `ai-diary/`:

```
diary.example.com {
    reverse_proxy frontend:80
}
```

Додати Caddy в `docker-compose.yml`:

```yaml
services:
    caddy:
        image: caddy:2-alpine
        ports:
            - "80:80"
            - "443:443"
        volumes:
            - ./Caddyfile:/etc/caddy/Caddyfile
            - caddy_data:/data
        depends_on:
            - frontend
        restart: unless-stopped

    frontend:
        # ... прибрати ports: "3000:80" (Caddy буде проксювати)
        ...
```

Додати volume:

```yaml
volumes:
    mongo_data:
    audio_files:
    caddy_data:
```

**Альтернатива:** якщо вже є nginx з certbot — використовуй його замість Caddy.

### B.6. Запустити

```bash
cd ~/ai-diary
docker compose up -d --build
```

Прапорець `-d` запускає у фоновому режимі (detached).

### B.7. Налаштувати домен для Telegram Login

У **@BotFather** → `/setdomain` → обери бота → вкажи домен (наприклад, `diary.example.com`).

### B.8. Зареєструвати webhook

```bash
curl -X POST "https://api.telegram.org/bot<ТОКЕН>/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url": "https://diary.example.com/api/webhook/telegram"}'
```

Перевірити статус webhook:

```bash
curl "https://api.telegram.org/bot<ТОКЕН>/getWebhookInfo"
```

### B.9. Моніторинг

```bash
# Логи всіх сервісів
docker compose logs -f

# Логи тільки backend
docker compose logs -f backend

# Перезапуск
docker compose restart

# Оновлення коду
git pull
docker compose up -d --build
```

---

# Різниця між режимами

|                  | Локальна розробка                    | Деплой на сервер                    |
| ---------------- | ------------------------------------ | ----------------------------------- |
| ngrok            | Потрібен (тунель для Telegram)       | Не потрібен (є реальний домен)      |
| SSL сертифікат   | ngrok дає автоматично                | Caddy/certbot (Let's Encrypt)       |
| Webhook URL      | `https://xxx.ngrok-free.app/api/...` | `https://diary.example.com/api/...` |
| Доступність бота | Тільки поки ngrok запущений          | 24/7                                |
| Frontend URL     | `http://localhost:3000`              | `https://diary.example.com`         |
| Docker Compose   | `docker compose up --build`          | `docker compose up -d --build`      |
| Telegram Login   | Telegram OAuth (через ngrok URL)     | Telegram OAuth (через домен)        |

---

# Запуск тестів

Тести не вимагають API ключів — використовують моки.

```bash
# Через Docker
docker compose exec backend pip install pytest pytest-asyncio mongomock-motor
docker compose exec backend python -m pytest tests/ -v

# Або локально (Python 3.10+)
cd backend
pip install -r requirements.txt
pip install pytest pytest-asyncio mongomock-motor
TELEGRAM_BOT_TOKEN=test ANTHROPIC_API_KEY=test OPENAI_API_KEY=test JWT_SECRET_KEY=test python -m pytest tests/ -v
```

Очікуваний результат: 34 passed.

---

# Типові проблеми

| Проблема                          | Причина                                     | Рішення                                                                            |
| --------------------------------- | ------------------------------------------- | ---------------------------------------------------------------------------------- |
| `port already in use` при запуску | Порт зайнятий іншим процесом                | `docker compose down` або змінити порти в `docker-compose.yml`                     |
| Бот не відповідає в Telegram      | Webhook не встановлений або ngrok зупинений | Перевірити `curl .../getWebhookInfo`, перезапустити ngrok, повторити `setWebhook`  |
| "Помилка транскрибації"           | Невірний OpenAI ключ або нуль на балансі    | Перевірити `OPENAI_API_KEY` в `.env`, поповнити баланс на platform.openai.com      |
| "Помилка запікання"               | Невірний Anthropic ключ або нуль на балансі | Перевірити `ANTHROPIC_API_KEY` в `.env`, поповнити баланс на console.anthropic.com |
| Frontend — біла сторінка          | JS помилка                                  | Відкрити DevTools (F12) → Console, подивитись помилку                              |
| MongoDB не підключається          | Контейнер не запустився                     | `docker compose logs mongodb`                                                      |
| ngrok дає нову адресу             | Безкоштовний план ngrok                     | Повторити `setWebhook` з новим URL                                                 |
| `docker compose` не знайдено      | Стара версія Docker                         | Оновити Docker Desktop або встановити docker-compose-plugin                        |

---

# Структура проєкту

```
ai-diary/
├── docker-compose.yml          # 3 сервіси: frontend, backend, mongodb
├── .env                        # API ключі (НЕ комітити в git!)
├── .env.example                # Шаблон .env
│
├── backend/
│   ├── Dockerfile              # Python 3.12 + ffmpeg
│   ├── requirements.txt        # Залежності
│   ├── pytest.ini              # Конфіг тестів
│   ├── app/
│   │   ├── main.py             # FastAPI — точка входу
│   │   ├── core/
│   │   │   ├── config.py       # Налаштування з .env
│   │   │   └── database.py     # Підключення до MongoDB
│   │   ├── models/             # 5 Beanie-моделей (колекції MongoDB)
│   │   │   ├── user.py         # Користувач
│   │   │   ├── raw_message.py  # Сире повідомлення (буфер)
│   │   │   ├── audio_job.py    # Задача транскрибації
│   │   │   ├── entry.py        # Запис щоденника
│   │   │   └── highlight.py    # Хайлайт
│   │   ├── api/                # REST API ендпоінти
│   │   │   ├── auth.py         # POST /api/auth/telegram, /refresh
│   │   │   ├── buffer.py       # GET/PATCH/DELETE /api/buffer, POST /bake
│   │   │   ├── entries.py      # GET /api/entries, /by-date/:date
│   │   │   ├── highlights.py   # GET /api/highlights, /categories
│   │   │   ├── webhook.py      # POST /api/webhook/telegram
│   │   │   └── dependencies.py # JWT auth middleware
│   │   ├── bot/                # Telegram bot (aiogram)
│   │   │   ├── setup.py        # Bot + Dispatcher
│   │   │   └── handlers.py     # /start, /bake, /help, voice, text
│   │   └── services/           # Бізнес-логіка
│   │       ├── auth.py         # JWT + Telegram OAuth верифікація
│   │       ├── classification.py # Claude API — визначення дати
│   │       ├── transcription.py  # Whisper API — голос → текст
│   │       ├── bake.py         # Claude API — повідомлення → запис
│   │       └── highlights.py   # Claude API — виділення хайлайтів
│   └── tests/                  # 34 unit-тести
│       ├── conftest.py         # Фікстури (mongomock)
│       ├── test_auth.py
│       ├── test_bake.py
│       ├── test_classification.py
│       ├── test_highlights.py
│       └── test_models.py
│
└── frontend/
    ├── Dockerfile              # Node 20 → nginx
    ├── nginx.conf              # Proxy /api → backend
    └── src/
        ├── main.ts             # Vue app entry point
        ├── App.vue             # Кореневий компонент
        ├── router.ts           # Vue Router (4 маршрути)
        ├── style.css           # Tailwind + Claude palette
        ├── api/
        │   ├── client.ts       # Axios + JWT interceptor
        │   └── index.ts        # Всі API виклики
        ├── stores/
        │   └── auth.ts         # Pinia store (авторизація)
        ├── components/
        │   └── AppNav.vue      # Навігація
        └── views/
            ├── LoginView.vue     # Вхід через Telegram
            ├── DiaryView.vue     # Щоденник (навігація по датах)
            ├── BufferView.vue    # Буфер повідомлень + bake
            └── HighlightsView.vue # Хайлайти з фільтрами
```
