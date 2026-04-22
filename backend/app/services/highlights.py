"""Highlights extraction service — identifies ideas, stories, moods, insights from entries."""

import json
import logging
from datetime import date, datetime
from typing import Optional

import anthropic

from app.core.config import settings
from app.models.entry import Entry
from app.models.highlight import Highlight, HighlightCategory
from app.models.user import User, CustomCategory

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_TEMPLATE = """Ти — аналітик особистого щоденника. Твоє завдання — виокремити з тексту запису значущі хайлайти (вижимки).

Категорії хайлайтів:
- **idea** — креативні думки, плани, задуми, бізнес-ідеї
- **story** — визначні події, подорожі, зустрічі, історії варті запам'ятовування
- **mood** — емоційний стан, рефлексія, психологічні спостереження
- **insight** — висновки, усвідомлення, «аха-моменти», життєві уроки, зсуви у світогляді, нове розуміння себе або життя
{custom_section}

Правила:
1. Хайлайт має бути самодостатнім — зрозумілим без контексту решти запису.
2. Не створюй хайлайт з буденних речей ("поснідав", "поїхав на роботу").
3. Один запис може мати 0-5 хайлайтів. Якщо нічого значущого — поверни порожній масив.
4. Заголовок — короткий, ємний (3-7 слів).
5. Контент — стислий переказ (1-3 речення), що передає суть.
6. Будь уважний до інсайтів: якщо автор описує нове усвідомлення, зміну підходу до життя, або важливий висновок зі свого досвіду — це ЗАВЖДИ хайлайт категорії "insight".

Формат відповіді (JSON):
{{"highlights": [{{"title": "...", "category": "...", "content": "..."}}]}}

Відповідай ТІЛЬКИ у JSON форматі."""


def _build_system_prompt(custom_categories: list[CustomCategory] | None = None) -> str:
    """Build system prompt with optional custom categories."""
    if custom_categories:
        lines = ["Додаткові категорії користувача:"]
        for cat in custom_categories:
            lines.append(f"- **{cat.name}** — {cat.description}")
        custom_section = "\n".join(lines)
    else:
        custom_section = ""

    return SYSTEM_PROMPT_TEMPLATE.format(custom_section=custom_section)


async def extract_highlights(entry: Entry, user: Optional[User] = None) -> list[Highlight]:
    """Extract highlights from a diary entry using Claude API.

    Deletes any previous highlights for this entry before creating new ones.

    Args:
        entry: The Entry document to analyze.
        user: Optional User document (for custom categories).

    Returns:
        List of created Highlight documents.
    """
    deleted = await Highlight.find({"source_entries": entry.id}).delete()
    if deleted and deleted.deleted_count:
        logger.info("Deleted %d old highlights for entry %s before re-extraction", deleted.deleted_count, entry.id)

    custom_cats = user.custom_categories if user else None
    system_prompt = _build_system_prompt(custom_cats)

    formatted_date = entry.date.strftime("%d %B %Y")
    user_prompt = (
        f"Дата запису: {formatted_date}\n\n"
        f"Текст запису:\n---\n{entry.content}\n---\n\n"
        f"Виокреми хайлайти з цього запису."
    )

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    last_error = None
    for attempt in range(3):
        try:
            response = await client.messages.create(
                model=settings.claude_model,
                max_tokens=2048,
                temperature=0.3,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )

            raw_text = response.content[0].text.strip()
            data = _parse_response(raw_text)

            highlights = []
            for item in data.get("highlights", []):
                h = Highlight(
                    user_id=entry.user_id,
                    title=item["title"],
                    category=item["category"],
                    content=item["content"],
                    source_entries=[entry.id],
                    date_range={"from_date": entry.date, "to_date": entry.date},
                )
                await h.insert()
                highlights.append(h)

            # Mark entry as checked
            entry.highlights_checked = True
            entry.updated_at = datetime.utcnow()
            await entry.save()

            logger.info(
                "Extracted %d highlights from entry %s",
                len(highlights),
                entry.id,
            )
            return highlights

        except anthropic.RateLimitError:
            import asyncio

            wait = 2 ** (attempt + 1)
            logger.warning("Rate limit hit, retrying in %ds", wait)
            await asyncio.sleep(wait)
            last_error = "rate_limit"

        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.warning("Invalid response on attempt %d: %s", attempt + 1, exc)
            last_error = exc

        except anthropic.APIError as exc:
            logger.error("Claude API error: %s", exc)
            last_error = exc
            break

    logger.error("Highlights extraction failed (%s)", last_error)
    return []


def _parse_response(raw_text: str) -> dict:
    """Parse JSON response, stripping markdown fences if present."""
    text = raw_text
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [l for l in lines[1:] if not l.strip().startswith("```")]
        text = "\n".join(lines)

    return json.loads(text)


async def extract_highlights_for_entries(entries: list[Entry], user: Optional[User] = None) -> list[Highlight]:
    """Extract highlights for multiple entries.

    Returns all created highlights.
    """
    all_highlights = []
    for entry in entries:
        if not entry.highlights_checked:
            highlights = await extract_highlights(entry, user)
            all_highlights.extend(highlights)
    return all_highlights
