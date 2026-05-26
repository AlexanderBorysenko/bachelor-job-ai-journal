"""Tests for settings API — user preferences."""

import pytest
from unittest.mock import AsyncMock, patch

from app.models.user import User
from app.services.bake import build_system_prompt, DEFAULT_STYLE


@pytest.mark.asyncio
class TestGetSettings:
    async def test_returns_defaults_for_new_user(self, test_user):
        from app.api.settings import _get_settings_response
        result = _get_settings_response(test_user)
        assert result["bake_style_prompt"] is None
        assert result["default_style_prompt"] == DEFAULT_STYLE

    async def test_returns_custom_prompt(self, test_user):
        test_user.bake_style_prompt = "Пиши коротко."
        await test_user.save()

        refreshed = await User.get(test_user.id)
        from app.api.settings import _get_settings_response
        result = _get_settings_response(refreshed)
        assert result["bake_style_prompt"] == "Пиши коротко."


@pytest.mark.asyncio
class TestUpdateSettings:
    async def test_save_custom_prompt(self, test_user):
        test_user.bake_style_prompt = "Пиши поетично."
        await test_user.save()

        refreshed = await User.get(test_user.id)
        assert refreshed.bake_style_prompt == "Пиши поетично."

    async def test_reset_to_default(self, test_user):
        test_user.bake_style_prompt = "Щось"
        await test_user.save()

        test_user.bake_style_prompt = None
        await test_user.save()

        refreshed = await User.get(test_user.id)
        assert refreshed.bake_style_prompt is None

    async def test_blank_string_resets_to_none(self, test_user):
        from app.api.settings import _normalize_style_prompt
        assert _normalize_style_prompt("") is None
        assert _normalize_style_prompt("   ") is None
        assert _normalize_style_prompt(None) is None
        assert _normalize_style_prompt("Коротко") == "Коротко"
