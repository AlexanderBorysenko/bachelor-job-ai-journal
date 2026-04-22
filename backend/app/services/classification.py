"""Date classification service — determines which date a message belongs to."""

import json
import logging
from datetime import date, datetime

import anthropic

from app.core.config import settings

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """Ти — асистент для класифікації повідомлень щоденника. Твоє завдання — визначити, до якої дати належить повідомлення.

Правила:
1. Якщо повідомлення описує події «сьогодні» або не містить часових маркерів — дата = дата відправки.
2. Якщо є маркери «вчора», «позавчора», «минулого тижня» тощо — обчисли відповідну дату відносно дати відправки.
3. Якщо є конкретна дата («15 квітня», «у понеділок») — визнач абсолютну дату.
4. Якщо повідомлення містить події з різних дат — вибери основну дату (ту, про яку найбільше тексту).

Відповідай ТІЛЬКИ у JSON форматі:
{"classified_date": "YYYY-MM-DD", "confidence": "high|medium|low"}"""

DAY_NAMES_UK = [
    "понеділок",
    "вівторок",
    "середа",
    "четвер",
    "п'ятниця",
    "субота",
    "неділя",
]


async def classify_date(
    message_content: str,
    send_datetime: datetime,
    max_retries: int = 3,
) -> date:
    """Classify which date a message belongs to using Claude API.

    Args:
        message_content: Text of the message.
        send_datetime: When the message was sent (UTC).
        max_retries: Number of retry attempts on failure.

    Returns:
        The classified date.
    """
    send_date = send_datetime.strftime("%Y-%m-%d")
    day_of_week = DAY_NAMES_UK[send_datetime.weekday()]
    send_time = send_datetime.strftime("%H:%M")

    user_prompt = (
        f"Дата відправки: {send_date} ({day_of_week})\n"
        f"Поточний час: {send_time}\n\n"
        f'Повідомлення:\n"{message_content}"\n\n'
        f"Визнач дату, до якої належить це повідомлення."
    )

    client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)

    last_error = None
    for attempt in range(max_retries):
        try:
            response = await client.messages.create(
                model=settings.claude_model,
                max_tokens=256,
                temperature=0.0,
                system=SYSTEM_PROMPT,
                messages=[{"role": "user", "content": user_prompt}],
            )

            raw_text = response.content[0].text.strip()
            result = _parse_response(raw_text, send_datetime.date())
            logger.info(
                "Classified message date: %s (confidence: %s)",
                result["classified_date"],
                result.get("confidence"),
            )
            return result["classified_date"]

        except anthropic.RateLimitError:
            import asyncio

            wait = 2 ** (attempt + 1)
            logger.warning("Rate limit hit, retrying in %ds (attempt %d)", wait, attempt + 1)
            await asyncio.sleep(wait)
            last_error = "rate_limit"

        except (json.JSONDecodeError, KeyError, ValueError) as exc:
            logger.warning("Invalid response on attempt %d: %s", attempt + 1, exc)
            last_error = exc
            # Retry with stricter instruction is handled by the same prompt
            # (system prompt already says "ТІЛЬКИ JSON")

        except anthropic.APIError as exc:
            logger.error("Claude API error: %s", exc)
            last_error = exc
            break

    # Fallback: use the send date
    logger.warning(
        "Classification failed after %d attempts (%s), falling back to send date",
        max_retries,
        last_error,
    )
    return send_datetime.date()


def _parse_response(raw_text: str, fallback_date: date) -> dict:
    """Parse the JSON response from Claude.

    Returns dict with 'classified_date' (date object), 'confidence', 'reasoning'.
    """
    # Strip markdown code fences if present
    text = raw_text
    if text.startswith("```"):
        lines = text.split("\n")
        # Remove first and last lines (```json and ```)
        lines = [l for l in lines[1:] if not l.strip().startswith("```")]
        text = "\n".join(lines)

    data = json.loads(text)

    classified_str = data.get("classified_date")
    if not classified_str:
        raise ValueError("Missing 'classified_date' in response")

    classified = date.fromisoformat(classified_str)

    return {
        "classified_date": classified,
        "confidence": data.get("confidence"),
        "reasoning": data.get("reasoning"),
    }
