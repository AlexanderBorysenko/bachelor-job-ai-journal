"""Tests for rebake — engine (regenerate-from-scratch) and the rebake endpoint."""

import pytest
from datetime import date, datetime
from unittest.mock import AsyncMock, patch

from bson import ObjectId
from fastapi import HTTPException

from app.models.entry import Entry
from app.models.raw_message import RawMessage, MessageStatus, SourceType
from app.models.highlight import Highlight
from app.models.bake_job import BakeJob, BakeJobStatus
from app.services import bake
from app.api import entries as entries_api


def _baked_msg(test_user, content="ходив у гори", mid=1, day=date(2026, 6, 1)):
    return RawMessage(
        user_id=test_user.id,
        source_type=SourceType.TEXT,
        content=content,
        telegram_message_id=mid,
        classified_date=day,
        status=MessageStatus.BAKED,
        created_at=datetime(2026, 6, 1, 9, 0),
    )


# --- engine -----------------------------------------------------------------

@pytest.mark.asyncio
class TestRebakeEntryEngine:
    @patch("app.services.bake.extract_highlights_for_entries", new_callable=AsyncMock)
    @patch("app.services.bake._call_claude", new_callable=AsyncMock)
    async def test_regenerates_and_replaces_content(self, mock_claude, mock_highlights, test_user):
        mock_claude.return_value = "# Новий запис\n\nПро гори."
        mock_highlights.return_value = []

        msg = _baked_msg(test_user)
        await msg.insert()
        entry = Entry(
            user_id=test_user.id, date=date(2026, 6, 1),
            content="СТАРИЙ ТЕКСТ (ручна правка)", source_messages=[msg.id], version=3,
        )
        await entry.insert()

        result = await bake.rebake_entry(test_user.id, entry)

        assert result == [entry]
        assert "Новий запис" in entry.content
        assert "СТАРИЙ ТЕКСТ" not in entry.content
        assert entry.version == 4                     # bumped by _save_entry
        assert entry.source_messages == [msg.id]      # unchanged
        refreshed = await RawMessage.get(msg.id)
        assert refreshed.status == MessageStatus.BAKED  # status untouched

    @patch("app.services.bake.extract_highlights_for_entries", new_callable=AsyncMock)
    @patch("app.services.bake._call_claude", new_callable=AsyncMock)
    async def test_reports_progress_baking_then_highlights(self, mock_claude, mock_highlights, test_user):
        mock_claude.return_value = "Запис."
        mock_highlights.return_value = []

        msg = _baked_msg(test_user)
        await msg.insert()
        entry = Entry(user_id=test_user.id, date=date(2026, 6, 1), content="old",
                      source_messages=[msg.id])
        await entry.insert()

        calls = []

        async def record(completed, total, label, phase):
            calls.append((completed, total, phase))

        await bake.rebake_entry(test_user.id, entry, on_progress=record)

        assert calls[0] == (0, 1, "baking")
        assert calls[-1] == (1, 1, "highlights")

    @patch("app.services.bake._call_claude", new_callable=AsyncMock)
    async def test_reextracts_highlights_drops_stale(self, mock_claude, test_user):
        # Claude returns plain text (not JSON) -> highlight extraction yields [] but
        # still deletes the entry's stale highlights before re-extraction.
        mock_claude.return_value = "# Запис\n\nТекст."

        msg = _baked_msg(test_user, content="ідея для стартапу")
        await msg.insert()
        entry = Entry(user_id=test_user.id, date=date(2026, 6, 1), content="old",
                      source_messages=[msg.id])
        await entry.insert()
        stale = Highlight(
            user_id=test_user.id, title="stale", category="idea", content="stale",
            source_entries=[entry.id],
            date_range={"from_date": entry.date, "to_date": entry.date},
        )
        await stale.insert()

        await bake.rebake_entry(test_user.id, entry)

        remaining = await Highlight.find({"source_entries": entry.id}).to_list()
        assert all(h.id != stale.id for h in remaining)


@pytest.mark.asyncio
class TestRenderDateContentDispatch:
    async def test_new_vs_append(self, test_user):
        calls = {}

        async def fake_new(*a, **k):
            calls["new"] = True
            return "NEW"

        async def fake_append(*a, **k):
            calls["append"] = True
            return "APPENDED"

        with patch("app.services.bake._bake_new", new=fake_new), \
             patch("app.services.bake._bake_append", new=fake_append), \
             patch("app.services.bake.process_macros", new=lambda c, ctx: (c, frozenset())):
            fresh = await bake._render_date_content(
                date(2026, 6, 1), [], None, {}, existing_content=None)
            appended = await bake._render_date_content(
                date(2026, 6, 1), [], None, {}, existing_content="OLD")

        assert fresh == "NEW" and calls.get("new")
        assert appended == "APPENDED" and calls.get("append")


# --- endpoint ---------------------------------------------------------------

@pytest.mark.asyncio
class TestRebakeEndpoint:
    async def test_starts_job(self, test_user):
        msg = _baked_msg(test_user)
        await msg.insert()
        entry = Entry(user_id=test_user.id, date=date(2026, 6, 1), content="old",
                      source_messages=[msg.id])
        await entry.insert()

        fake_job = BakeJob(user_id=test_user.id, total_steps=1)
        with patch("app.api.entries.launch_bake", new=AsyncMock(return_value=fake_job)) as lb:
            result = await entries_api.rebake(str(entry.id), user_id=str(test_user.id))

        assert result["status"] == "running"
        assert result["total_steps"] == 1
        assert lb.await_count == 1

    async def test_404_for_missing(self, test_user):
        with pytest.raises(HTTPException) as exc:
            await entries_api.rebake(str(ObjectId()), user_id=str(test_user.id))
        assert exc.value.status_code == 404

    async def test_404_for_other_users_entry(self, test_user):
        entry = Entry(user_id=ObjectId(), date=date(2026, 6, 1), content="x",
                      source_messages=[ObjectId()])
        await entry.insert()
        with pytest.raises(HTTPException) as exc:
            await entries_api.rebake(str(entry.id), user_id=str(test_user.id))
        assert exc.value.status_code == 404

    async def test_422_when_no_source_messages(self, test_user):
        entry = Entry(user_id=test_user.id, date=date(2026, 6, 1), content="old",
                      source_messages=[])
        await entry.insert()
        with pytest.raises(HTTPException) as exc:
            await entries_api.rebake(str(entry.id), user_id=str(test_user.id))
        assert exc.value.status_code == 422

    async def test_409_when_bake_active(self, test_user):
        msg = _baked_msg(test_user)
        await msg.insert()
        entry = Entry(user_id=test_user.id, date=date(2026, 6, 1), content="old",
                      source_messages=[msg.id])
        await entry.insert()
        await BakeJob(user_id=test_user.id, total_steps=1, status=BakeJobStatus.RUNNING).insert()

        with pytest.raises(HTTPException) as exc:
            await entries_api.rebake(str(entry.id), user_id=str(test_user.id))
        assert exc.value.status_code == 409
