"""Tests for story points — model + /api/storypoints router."""

import pytest
from datetime import date

from app.models.entry import Entry
from app.models.story_point import StoryPoint


async def _make_entry(user, d=date(2026, 6, 8)):
    entry = Entry(user_id=user.id, date=d, blocks=[], source_messages=[], version=1)
    await entry.insert()
    return entry


@pytest.mark.asyncio
class TestStoryPointModel:
    async def test_defaults(self, test_user):
        entry = await _make_entry(test_user)
        p = StoryPoint(user_id=test_user.id, entry_id=entry.id, date=entry.date, title="First light")
        await p.insert()
        fetched = await StoryPoint.get(p.id)
        assert fetched.title == "First light"
        assert fetched.order == 0
        assert fetched.source == "manual"
        assert fetched.date == date(2026, 6, 8)


@pytest.mark.asyncio
class TestCreateAndList:
    async def test_create_appends_order_and_returns_point(self, test_user):
        from app.api.story_points import create_story_point, CreateStoryPointRequest
        entry = await _make_entry(test_user)
        uid = str(test_user.id)

        first = await create_story_point(CreateStoryPointRequest(entry_id=str(entry.id), title="  Morning swim  "), user_id=uid)
        second = await create_story_point(CreateStoryPointRequest(entry_id=str(entry.id), title="Lunch with Anna"), user_id=uid)

        assert first["title"] == "Morning swim"   # trimmed
        assert first["order"] == 0
        assert second["order"] == 1
        assert first["source"] == "manual"

    async def test_create_rejects_empty_title(self, test_user):
        from fastapi import HTTPException
        from app.api.story_points import create_story_point, CreateStoryPointRequest
        entry = await _make_entry(test_user)
        with pytest.raises(HTTPException) as exc:
            await create_story_point(CreateStoryPointRequest(entry_id=str(entry.id), title="   "), user_id=str(test_user.id))
        assert exc.value.status_code == 422

    async def test_create_foreign_entry_404(self, test_user):
        from fastapi import HTTPException
        from bson import ObjectId
        from app.api.story_points import create_story_point, CreateStoryPointRequest
        missing = str(ObjectId())
        with pytest.raises(HTTPException) as exc:
            await create_story_point(CreateStoryPointRequest(entry_id=missing, title="x"), user_id=str(test_user.id))
        assert exc.value.status_code == 404

    async def test_list_for_entry_ordered(self, test_user):
        from app.api.story_points import create_story_point, list_for_entry, CreateStoryPointRequest
        entry = await _make_entry(test_user)
        uid = str(test_user.id)
        await create_story_point(CreateStoryPointRequest(entry_id=str(entry.id), title="a"), user_id=uid)
        await create_story_point(CreateStoryPointRequest(entry_id=str(entry.id), title="b"), user_id=uid)
        result = await list_for_entry(entry_id=str(entry.id), user_id=uid)
        assert [p["title"] for p in result["items"]] == ["a", "b"]


@pytest.mark.asyncio
class TestTimeline:
    async def test_timeline_groups_by_date_newest_first(self, test_user):
        from datetime import date
        from app.api.story_points import create_story_point, get_timeline, CreateStoryPointRequest
        uid = str(test_user.id)
        older = await _make_entry(test_user, date(2026, 6, 1))
        newer = await _make_entry(test_user, date(2026, 6, 8))
        await create_story_point(CreateStoryPointRequest(entry_id=str(older.id), title="old-1"), user_id=uid)
        await create_story_point(CreateStoryPointRequest(entry_id=str(newer.id), title="new-1"), user_id=uid)
        await create_story_point(CreateStoryPointRequest(entry_id=str(newer.id), title="new-2"), user_id=uid)

        result = await get_timeline(user_id=uid)
        groups = result["groups"]
        assert [g["date"] for g in groups] == ["2026-06-08", "2026-06-01"]
        assert [p["title"] for p in groups[0]["points"]] == ["new-1", "new-2"]

    async def test_timeline_empty(self, test_user):
        from app.api.story_points import get_timeline
        result = await get_timeline(user_id=str(test_user.id))
        assert result["groups"] == []


@pytest.mark.asyncio
class TestRename:
    async def test_rename_updates_title(self, test_user):
        from app.api.story_points import create_story_point, rename_story_point, CreateStoryPointRequest, UpdateStoryPointRequest
        entry = await _make_entry(test_user)
        uid = str(test_user.id)
        p = await create_story_point(CreateStoryPointRequest(entry_id=str(entry.id), title="old"), user_id=uid)
        updated = await rename_story_point(point_id=p["id"], body=UpdateStoryPointRequest(title="new"), user_id=uid)
        assert updated["title"] == "new"

    async def test_rename_foreign_point_404(self, test_user):
        from fastapi import HTTPException
        from bson import ObjectId
        from app.api.story_points import rename_story_point, UpdateStoryPointRequest
        with pytest.raises(HTTPException) as exc:
            await rename_story_point(point_id=str(ObjectId()), body=UpdateStoryPointRequest(title="x"), user_id=str(test_user.id))
        assert exc.value.status_code == 404


@pytest.mark.asyncio
class TestReorder:
    async def test_reorder_assigns_order(self, test_user):
        from app.api.story_points import create_story_point, reorder_story_points, list_for_entry, CreateStoryPointRequest, ReorderRequest
        entry = await _make_entry(test_user)
        uid = str(test_user.id)
        a = await create_story_point(CreateStoryPointRequest(entry_id=str(entry.id), title="a"), user_id=uid)
        b = await create_story_point(CreateStoryPointRequest(entry_id=str(entry.id), title="b"), user_id=uid)
        c = await create_story_point(CreateStoryPointRequest(entry_id=str(entry.id), title="c"), user_id=uid)

        await reorder_story_points(body=ReorderRequest(entry_id=str(entry.id), ordered_ids=[c["id"], a["id"], b["id"]]), user_id=uid)

        result = await list_for_entry(entry_id=str(entry.id), user_id=uid)
        assert [p["title"] for p in result["items"]] == ["c", "a", "b"]
        assert [p["order"] for p in result["items"]] == [0, 1, 2]

    async def test_reorder_mismatch_422(self, test_user):
        from fastapi import HTTPException
        from app.api.story_points import create_story_point, reorder_story_points, CreateStoryPointRequest, ReorderRequest
        entry = await _make_entry(test_user)
        uid = str(test_user.id)
        a = await create_story_point(CreateStoryPointRequest(entry_id=str(entry.id), title="a"), user_id=uid)
        await create_story_point(CreateStoryPointRequest(entry_id=str(entry.id), title="b"), user_id=uid)
        with pytest.raises(HTTPException) as exc:
            await reorder_story_points(body=ReorderRequest(entry_id=str(entry.id), ordered_ids=[a["id"]]), user_id=uid)
        assert exc.value.status_code == 422

    async def test_reorder_duplicate_ids_422(self, test_user):
        from fastapi import HTTPException
        from app.api.story_points import create_story_point, reorder_story_points, CreateStoryPointRequest, ReorderRequest
        entry = await _make_entry(test_user)
        uid = str(test_user.id)
        a = await create_story_point(CreateStoryPointRequest(entry_id=str(entry.id), title="a"), user_id=uid)
        await create_story_point(CreateStoryPointRequest(entry_id=str(entry.id), title="b"), user_id=uid)
        # duplicate id 'a' + missing 'b' — same length as entry's points but not the same set/multiset
        with pytest.raises(HTTPException) as exc:
            await reorder_story_points(body=ReorderRequest(entry_id=str(entry.id), ordered_ids=[a["id"], a["id"]]), user_id=uid)
        assert exc.value.status_code == 422


@pytest.mark.asyncio
class TestDeleteAndCascade:
    async def test_delete_point(self, test_user):
        from app.api.story_points import create_story_point, delete_story_point, get_timeline, CreateStoryPointRequest
        entry = await _make_entry(test_user)
        uid = str(test_user.id)
        p = await create_story_point(CreateStoryPointRequest(entry_id=str(entry.id), title="bye"), user_id=uid)
        await delete_story_point(point_id=p["id"], user_id=uid)
        result = await get_timeline(user_id=uid)
        assert result["groups"] == []

    async def test_deleting_entry_cascades_story_points(self, test_user):
        from app.api.entries import delete_entry
        from app.api.story_points import create_story_point, get_timeline, CreateStoryPointRequest
        entry = await _make_entry(test_user)
        uid = str(test_user.id)
        await create_story_point(CreateStoryPointRequest(entry_id=str(entry.id), title="will vanish"), user_id=uid)

        await delete_entry(entry_id=str(entry.id), user_id=uid)

        result = await get_timeline(user_id=uid)
        assert result["groups"] == []
