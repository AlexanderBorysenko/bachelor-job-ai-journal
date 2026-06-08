"""Tests for media handling in the bake pipeline."""

import pytest
from datetime import date
from unittest.mock import AsyncMock, patch

from app.models.media_file import MediaFile, MediaKind, MediaStatus
from app.models.raw_message import RawMessage, SourceType, MessageStatus
from app.services.bake import bake_messages
from app.services.blocks import ensure_all_blocks, collect_shortcodes


class TestCompletenessPass:
    def test_appends_figure_for_missing(self):
        blocks = [{"type": "markdown", "text": "Текст"}]
        out = ensure_all_blocks(blocks, ["att_a", "att_b"], {"att_a"})
        assert collect_shortcodes(out) == {"att_b"}
        assert out[-1] == {"type": "figure", "media": "att_b", "width": 100, "align": "full", "caption": ""}

    def test_noop_when_all_present(self):
        blocks = [{"type": "figure", "media": "att_a", "width": 100, "align": "full", "caption": ""}]
        assert ensure_all_blocks(blocks, ["att_a"], {"att_a"}) == blocks


@pytest.mark.asyncio
class TestBakeWithMedia:
    @patch("app.services.bake.extract_highlights_for_entries", new_callable=AsyncMock)
    @patch("app.services.bake._call_claude", new_callable=AsyncMock)
    async def test_media_placed_and_descriptive_not_leaked(self, mock_claude, mock_highlights, test_user):
        # Model "forgets" the media; the completeness pass must place it as a figure.
        mock_claude.return_value = [{"type": "markdown", "text": "Гарний день у парку."}]
        mock_highlights.return_value = []

        mf = MediaFile(user_id=test_user.id, shortcode="att_park", kind=MediaKind.PHOTO,
                       status=MediaStatus.READY, attached=True)
        await mf.insert()

        media_msg = RawMessage(user_id=test_user.id, source_type=SourceType.MEDIA,
                               media_file_ids=[mf.id], descriptive="секретна підказка розташування",
                               telegram_message_id=0, classified_date=date(2026, 6, 2),
                               status=MessageStatus.PENDING)
        await media_msg.insert()

        entries = await bake_messages(test_user.id, [media_msg])
        blocks = entries[0].blocks

        assert "att_park" in collect_shortcodes(blocks)                       # placed
        assert all("секретна підказка" not in (b.get("text") or "") for b in blocks)  # never leaked
