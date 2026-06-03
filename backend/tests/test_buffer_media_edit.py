"""Tests for web media editing of unbaked buffer messages."""

import pytest
from datetime import date

from fastapi import HTTPException

from app.models.raw_message import RawMessage, SourceType, MessageStatus
from app.models.media_file import MediaFile, MediaKind, MediaStatus
from app.models.bake_job import BakeJob
from app.services import media_storage


@pytest.fixture(autouse=True)
def _tmp_media_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(media_storage.settings, "media_files_path", str(tmp_path))


async def _media_file(user_id, code, *, kind=MediaKind.PHOTO, status=MediaStatus.READY,
                      attached=True, with_bytes=True, poster=False):
    storage_key = media_storage.save_bytes(code, b"BYTES", ".jpg") if with_bytes else None
    poster_key = media_storage.save_poster(code, b"POSTER") if poster else None
    mf = MediaFile(
        user_id=user_id, shortcode=code, kind=kind, status=status, attached=attached,
        storage_key=storage_key, poster_key=poster_key, mime="image/jpeg", source="telegram",
    )
    await mf.insert()
    return mf


async def _media_message(user_id, file_ids):
    msg = RawMessage(
        user_id=user_id, source_type=SourceType.MEDIA, content="",
        media_file_ids=file_ids, descriptive="desc", telegram_message_id=0,
        classified_date=date(2026, 4, 22), status=MessageStatus.PENDING,
    )
    await msg.insert()
    return msg


@pytest.mark.asyncio
class TestSerializerOrder:
    async def test_media_files_follow_media_file_ids_order(self, test_user):
        from app.api.buffer import _serialize_buffer_message
        a = await _media_file(test_user.id, "att_a")
        b = await _media_file(test_user.id, "att_b")
        c = await _media_file(test_user.id, "att_c")
        # media_file_ids order is REVERSED vs insertion order
        msg = await _media_message(test_user.id, [c.id, a.id, b.id])

        data = await _serialize_buffer_message(msg)
        assert [f["shortcode"] for f in data["media_files"]] == ["att_c", "att_a", "att_b"]


from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
class TestCreateWebMedia:
    async def test_image_happy_path(self, test_user):
        from app.services.media_ingest_web import create_web_media
        mf = await create_web_media(test_user.id, b"PNGBYTES", "image/png", "x.png")
        assert mf.kind == MediaKind.PHOTO
        assert mf.status == MediaStatus.READY
        assert mf.attached is True
        assert mf.source == "web"
        assert mf.storage_key and mf.storage_key.endswith(".png")
        with open(mf.storage_key, "rb") as f:
            assert f.read() == b"PNGBYTES"

    async def test_video_generates_poster(self, test_user):
        from app.services import media_ingest_web
        with patch.object(media_ingest_web, "_generate_video_poster",
                          new=AsyncMock(return_value=b"POSTER")):
            mf = await media_ingest_web.create_web_media(
                test_user.id, b"MP4BYTES", "video/mp4", "x.mp4")
        assert mf.kind == MediaKind.VIDEO
        assert mf.poster_key is not None

    async def test_video_without_poster_is_ok(self, test_user):
        from app.services import media_ingest_web
        with patch.object(media_ingest_web, "_generate_video_poster",
                          new=AsyncMock(return_value=None)):
            mf = await media_ingest_web.create_web_media(
                test_user.id, b"MP4BYTES", "video/mp4", "x.mp4")
        assert mf.kind == MediaKind.VIDEO
        assert mf.poster_key is None

    async def test_rejects_disallowed_mime(self, test_user):
        from app.services.media_ingest_web import create_web_media
        with pytest.raises(HTTPException) as exc:
            await create_web_media(test_user.id, b"x", "application/pdf", "x.pdf")
        assert exc.value.status_code == 415

    async def test_rejects_oversize(self, test_user, monkeypatch):
        from app.services import media_ingest_web
        monkeypatch.setattr(media_ingest_web.settings, "media_max_upload_bytes", 4)
        with pytest.raises(HTTPException) as exc:
            await media_ingest_web.create_web_media(
                test_user.id, b"toolong", "image/jpeg", "x.jpg")
        assert exc.value.status_code == 413


@pytest.mark.asyncio
class TestEditableMediaGuard:
    async def test_missing_404(self, test_user):
        from app.api.buffer import _get_editable_media_message
        from bson import ObjectId
        with pytest.raises(HTTPException) as exc:
            await _get_editable_media_message(str(ObjectId()), str(test_user.id))
        assert exc.value.status_code == 404

    async def test_foreign_404(self, test_user):
        from app.api.buffer import _get_editable_media_message
        msg = await _media_message(test_user.id, [])
        with pytest.raises(HTTPException) as exc:
            await _get_editable_media_message(str(msg.id), "000000000000000000000000")
        assert exc.value.status_code == 404

    async def test_active_bake_409(self, test_user):
        from app.api.buffer import _get_editable_media_message
        msg = await _media_message(test_user.id, [])
        await BakeJob(user_id=test_user.id, total_steps=1).insert()
        with pytest.raises(HTTPException) as exc:
            await _get_editable_media_message(str(msg.id), str(test_user.id))
        assert exc.value.status_code == 409

    async def test_non_media_400(self, test_user):
        from app.api.buffer import _get_editable_media_message
        msg = RawMessage(
            user_id=test_user.id, source_type=SourceType.TEXT, content="hi",
            telegram_message_id=1, classified_date=date(2026, 4, 22),
            status=MessageStatus.PENDING,
        )
        await msg.insert()
        with pytest.raises(HTTPException) as exc:
            await _get_editable_media_message(str(msg.id), str(test_user.id))
        assert exc.value.status_code == 400

    async def test_baked_400(self, test_user):
        from app.api.buffer import _get_editable_media_message
        msg = await _media_message(test_user.id, [])
        msg.status = MessageStatus.BAKED
        await msg.save()
        with pytest.raises(HTTPException) as exc:
            await _get_editable_media_message(str(msg.id), str(test_user.id))
        assert exc.value.status_code == 400


@pytest.mark.asyncio
class TestUpdateMessageMedia:
    async def test_reorder(self, test_user):
        from app.api.buffer import update_message_media, UpdateMediaOrderRequest
        a = await _media_file(test_user.id, "att_a")
        b = await _media_file(test_user.id, "att_b")
        msg = await _media_message(test_user.id, [a.id, b.id])

        result = await update_message_media(
            str(msg.id), UpdateMediaOrderRequest(shortcodes=["att_b", "att_a"]),
            user_id=str(test_user.id),
        )
        assert [f["shortcode"] for f in result["media_files"]] == ["att_b", "att_a"]
        refreshed = await RawMessage.get(msg.id)
        assert refreshed.media_file_ids == [b.id, a.id]

    async def test_delete_one_removes_file_and_bytes(self, test_user):
        from app.api.buffer import update_message_media, UpdateMediaOrderRequest
        a = await _media_file(test_user.id, "att_a")
        b = await _media_file(test_user.id, "att_b")
        msg = await _media_message(test_user.id, [a.id, b.id])
        a_path = a.storage_key

        await update_message_media(
            str(msg.id), UpdateMediaOrderRequest(shortcodes=["att_b"]),
            user_id=str(test_user.id),
        )
        assert await MediaFile.find_one({"shortcode": "att_a"}) is None
        import os
        assert not os.path.exists(a_path)
        refreshed = await RawMessage.get(msg.id)
        assert refreshed.media_file_ids == [b.id]

    async def test_empty_deletes_message(self, test_user):
        from app.api.buffer import update_message_media, UpdateMediaOrderRequest
        import os
        a = await _media_file(test_user.id, "att_a")
        a_path = a.storage_key
        msg = await _media_message(test_user.id, [a.id])

        result = await update_message_media(
            str(msg.id), UpdateMediaOrderRequest(shortcodes=[]),
            user_id=str(test_user.id),
        )
        assert result == {"deleted": True}
        assert await RawMessage.get(msg.id) is None
        assert await MediaFile.find_one({"shortcode": "att_a"}) is None
        assert not os.path.exists(a_path)

    async def test_foreign_shortcode_404(self, test_user):
        from app.api.buffer import update_message_media, UpdateMediaOrderRequest
        a = await _media_file(test_user.id, "att_a")
        msg = await _media_message(test_user.id, [a.id])
        with pytest.raises(HTTPException) as exc:
            await update_message_media(
                str(msg.id), UpdateMediaOrderRequest(shortcodes=["att_a", "att_ghost"]),
                user_id=str(test_user.id),
            )
        assert exc.value.status_code == 404

    async def test_duplicate_shortcodes_400(self, test_user):
        from app.api.buffer import update_message_media, UpdateMediaOrderRequest
        a = await _media_file(test_user.id, "att_a")
        msg = await _media_message(test_user.id, [a.id])
        with pytest.raises(HTTPException) as exc:
            await update_message_media(
                str(msg.id), UpdateMediaOrderRequest(shortcodes=["att_a", "att_a"]),
                user_id=str(test_user.id),
            )
        assert exc.value.status_code == 400


@pytest.mark.asyncio
class TestUploadMessageMedia:
    async def test_uploads_and_does_not_attach_to_message(self, test_user):
        from app.api.buffer import upload_message_media
        from starlette.datastructures import UploadFile, Headers
        import io
        msg = await _media_message(test_user.id, [])
        upload = UploadFile(
            filename="x.png",
            file=io.BytesIO(b"PNGBYTES"),
            headers=Headers({"content-type": "image/png"}),
        )
        result = await upload_message_media(
            str(msg.id), file=upload, user_id=str(test_user.id))
        assert result["kind"] == "photo"
        assert result["status"] == "ready"
        assert result["has_poster"] is False
        created = await MediaFile.find_one({"shortcode": result["shortcode"]})
        assert created is not None
        refreshed = await RawMessage.get(msg.id)
        assert refreshed.media_file_ids == []
