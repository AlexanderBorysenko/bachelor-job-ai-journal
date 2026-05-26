"""Bake service — transforms raw messages into literary diary entries via Claude API."""

import json
import logging
from collections import defaultdict
from datetime import date, datetime
from typing import Optional

import anthropic

from app.core.config import settings
from app.models.raw_message import RawMessage, MessageStatus
from app.models.entry import Entry
from app.models.user import User
from app.services.highlights import extract_highlights_for_entries

logger = logging.getLogger(__name__)

CORE_RULES = """Ти — редактор особистого щоденника. Твоє завдання — перетворити сирі повідомлення (нотатки, голосові транскрипції) у зв'язний текст щоденникового запису.

Обов'язкові правила:
1. ЗБЕРЕЖИ весь смисловий зміст — не вигадуй фактів, не додавай того, чого не було.
2. Виправляй граматичні помилки та помилки транскрибації, але зберігай авторський стиль та характерні вирази.
3. Хронологічний порядок: якщо можна визначити послідовність подій — зберігай її.
4. Якщо є повтори (одне й те саме сказано в тексті і в голосовому) — об'єднай, не дублюй.
5. Формат: Markdown. Використовуй абзаци, **жирний** для акцентів, списки де доречно.
6. Відповідай ТІЛЬКИ текстом запису, без вступів типу "Ось ваш запис:" чи пояснень."""

DEFAULT_STYLE = """Стиль та оформлення:
- Структуруй запис за допомогою заголовків Markdown: використовуй `## Назва теми` для кожної тематичної секції. Якщо в секції є підтеми — використовуй `### Підтема`. Кожна секція — окрема тема чи подія дня. Придумай короткий, змістовний заголовок для кожної секції (наприклад: "## Ранкова пробіжка", "## Робочі справи", "## Вечірні роздуми"). НЕ використовуй `---` для розділення тем — тільки заголовки.
- Стиль — особистий щоденник: від першої особи, природній, не надто формальний."""


def build_system_prompt(user_style: str | None) -> str:
    style = user_style.strip() if user_style and user_style.strip() else None
    return f"{CORE_RULES}\n\n{style if style else DEFAULT_STYLE}"


async def bake_messages(user_id, messages: list[RawMessage]) -> list[Entry]:
    """Group messages by date and bake each group into an Entry."""
    user = await User.get(user_id)
    style_prompt = user.bake_style_prompt if user else None

    by_date: dict[date, list[RawMessage]] = defaultdict(list)
    for msg in messages:
        by_date[msg.classified_date].append(msg)

    entries = []
    for entry_date in sorted(by_date.keys()):
        date_messages = by_date[entry_date]
        date_messages.sort(key=lambda m: m.created_at or datetime.min)

        entry = await _bake_date(user_id, entry_date, date_messages, style_prompt)
        entries.append(entry)

        for msg in date_messages:
            msg.status = MessageStatus.BAKED
            await msg.save()

    try:
        await extract_highlights_for_entries(entries, user)
    except Exception as exc:
        logger.warning("Highlights extraction failed (non-critical): %s", exc)

    return entries


async def _bake_date(
    user_id,
    entry_date: date,
    messages: list[RawMessage],
    style_prompt: str | None = None,
) -> Entry:
    """Bake messages for a single date into an Entry."""
    existing = await Entry.find_one({"user_id": user_id, "date": entry_date})

    if existing:
        content = await _bake_append(existing.content, messages, entry_date, style_prompt)
        existing.content = content
        existing.source_messages.extend([msg.id for msg in messages])
        existing.version = (existing.version or 1) + 1
        existing.highlights_checked = False
        existing.updated_at = datetime.utcnow()
        await existing.save()
        return existing
    else:
        content = await _bake_new(messages, entry_date, style_prompt)
        entry = Entry(
            user_id=user_id,
            date=entry_date,
            content=content,
            source_messages=[msg.id for msg in messages],
            version=1,
        )
        await entry.insert()
        return entry


async def _bake_new(messages: list[RawMessage], entry_date: date, style_prompt: str | None = None) -> str:
    """Generate a new diary entry from messages."""
    formatted_date = entry_date.strftime("%d %B %Y")
    messages_text = _format_messages(messages)

    user_prompt = (
        f"Дата: {formatted_date}\n\n"
        f"Сирі повідомлення (хронологічно):\n\n"
        f"{messages_text}\n\n"
        f"Створи щоденниковий запис за цю дату."
    )

    return await _call_claude(user_prompt, style_prompt=style_prompt, temperature=0.7, max_tokens=4096)


async def _bake_append(
    existing_content: str,
    new_messages: list[RawMessage],
    entry_date: date,
    style_prompt: str | None = None,
) -> str:
    """Append new messages to an existing diary entry."""
    formatted_date = entry_date.strftime("%d %B %Y")
    messages_text = _format_messages(new_messages)

    user_prompt = (
        f"Дата: {formatted_date}\n\n"
        f"Існуючий запис:\n---\n{existing_content}\n---\n\n"
        f"Нові повідомлення, які потрібно інтегрувати:\n\n"
        f"{messages_text}\n\n"
        f"Доповни існуючий запис новою інформацією. "
        f"Збережи вже наявний текст, лаконічно інтегруй нові дані. "
        f"Не дублюй те, що вже описано. Поверни ПОВНИЙ оновлений текст запису."
    )

    return await _call_claude(user_prompt, style_prompt=style_prompt, temperature=0.5, max_tokens=4096)


def _format_messages(messages: list[RawMessage]) -> str:
    """Format messages into the prompt template."""
    lines = []
    for msg in messages:
        time_str = msg.created_at.strftime("%H:%M") if msg.created_at else "??:??"
        source = msg.source_type.value  # "text" or "voice"
        lines.append(f"[{time_str}] ({source}): {msg.content}")
    return "\n".join(lines)


async def _call_claude(
    user_prompt: str,
    style_prompt: str | None = None,
    temperature: float = 0.7,
    max_tokens: int = 4096,
    max_retries: int = 3,
) -> str:
    """Call Claude API with retry logic."""
    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
    system_prompt = build_system_prompt(style_prompt)

    last_error = None
    for attempt in range(max_retries):
        try:
            response = await client.messages.create(
                model=settings.claude_model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return response.content[0].text.strip()

        except anthropic.RateLimitError:
            import asyncio

            wait = 2 ** (attempt + 1)
            logger.warning("Rate limit hit, retrying in %ds", wait)
            await asyncio.sleep(wait)
            last_error = "rate_limit"

        except anthropic.APIError as exc:
            logger.error("Claude API error on attempt %d: %s", attempt + 1, exc)
            last_error = exc
            break

    logger.error("Bake failed after retries (%s), returning raw text", last_error)
    return f"[Автоматичне запікання не вдалося. Сирі повідомлення:]\n\n{user_prompt}"
