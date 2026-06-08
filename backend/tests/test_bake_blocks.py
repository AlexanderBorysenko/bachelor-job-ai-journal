"""Tests for block normalization inside the bake pipeline."""

import pytest
from datetime import date
from unittest.mock import AsyncMock, patch

from app.models.media_file import MediaFile, MediaKind, MediaStatus
from app.models.raw_message import RawMessage, SourceType, MessageStatus
from app.services.bake import bake_messages
from app.services.blocks import collect_shortcodes


@pytest.mark.asyncio
class TestBakeBlocks:
    @patch("app.services.bake.extract_highlights_for_entries", new_callable=AsyncMock)
    @patch("app.services.bake._call_claude", new_callable=AsyncMock)
    async def test_gallery_normalized_not_double_placed(self, mock_claude, mock_hl, test_user):
        mock_hl.return_value = []
        a = MediaFile(user_id=test_user.id, shortcode="att_a", kind=MediaKind.PHOTO,
                      status=MediaStatus.READY, attached=True)
        b = MediaFile(user_id=test_user.id, shortcode="att_b", kind=MediaKind.PHOTO,
                      status=MediaStatus.READY, attached=True)
        await a.insert(); await b.insert()
        # Model returns raw blocks (a gallery + prose)
        mock_claude.return_value = [
            {"type": "markdown", "text": "День був чудовий."},
            {"type": "gallery", "images": ["att_a", "att_b"], "caption": "Прогулянка"},
        ]
        msg = RawMessage(user_id=test_user.id, source_type=SourceType.MEDIA,
                         media_file_ids=[a.id, b.id], descriptive="секрет",
                         telegram_message_id=0, classified_date=date(2026, 6, 2),
                         status=MessageStatus.PENDING)
        await msg.insert()

        entries = await bake_messages(test_user.id, [msg])
        blocks = entries[0].blocks

        # descriptive never leaked into any block
        assert all("секрет" not in (b.get("text") or "") and "секрет" not in (b.get("caption") or "")
                   for b in blocks)
        # both photos placed exactly once, inside the gallery — no trailing fallback figure
        assert collect_shortcodes(blocks) == {"att_a", "att_b"}
        assert sum(1 for b in blocks if b["type"] == "figure") == 0
        gallery = next(b for b in blocks if b["type"] == "gallery")
        assert gallery["images"] == ["att_a", "att_b"]
        assert gallery["caption"] == "Прогулянка"

    @patch("app.services.bake.extract_highlights_for_entries", new_callable=AsyncMock)
    @patch("app.services.bake._call_claude", new_callable=AsyncMock)
    async def test_figure_accepts_video(self, mock_claude, mock_hl, test_user):
        mock_hl.return_value = []
        v = MediaFile(user_id=test_user.id, shortcode="att_v", kind=MediaKind.VIDEO,
                      status=MediaStatus.READY, attached=True)
        await v.insert()
        mock_claude.return_value = [
            {"type": "figure", "media": "att_v", "width": 100, "align": "full", "caption": "Кліп"},
        ]
        msg = RawMessage(user_id=test_user.id, source_type=SourceType.MEDIA,
                         media_file_ids=[v.id], descriptive="",
                         telegram_message_id=0, classified_date=date(2026, 6, 2),
                         status=MessageStatus.PENDING)
        await msg.insert()

        entries = await bake_messages(test_user.id, [msg])
        fig = next(b for b in entries[0].blocks if b["type"] == "figure")
        assert fig["media"] == "att_v"
