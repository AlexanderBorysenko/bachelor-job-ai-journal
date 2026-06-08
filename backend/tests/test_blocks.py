"""Tests for the content-block foundation, specs, and processor."""

from app.services.blocks.base import BlockSpec, BLOCK_REGISTRY, register
from app.services.blocks import markdown as md_block
from app.services.blocks import gallery as gallery_block
from app.services.blocks import figure as figure_block
import app.services.blocks  # registers all specs via __init__
from app.services.blocks import (
    build_blocks_schema, normalize_blocks, collect_shortcodes, blocks_to_text, ensure_all_blocks,
)


class TestRegistry:
    def test_register_adds_to_registry(self):
        spec = BlockSpec(
            name="_dummy", schema={"type": "object"},
            validate=lambda b, c: b, collect=lambda b: set(),
        )
        try:
            register(spec)
            assert BLOCK_REGISTRY["_dummy"] is spec
        finally:
            BLOCK_REGISTRY.pop("_dummy", None)


class TestMarkdownSpec:
    def test_keeps_text(self):
        assert md_block._validate({"type": "markdown", "text": "Привіт"}, {}) == {
            "type": "markdown", "text": "Привіт"
        }

    def test_drops_empty_or_nonstr(self):
        assert md_block._validate({"type": "markdown", "text": "   "}, {}) is None
        assert md_block._validate({"type": "markdown", "text": 5}, {}) is None
        assert md_block._validate({"type": "markdown"}, {}) is None

    def test_collect_is_empty(self):
        # markdown blocks never carry media
        assert md_block._collect({"type": "markdown", "text": "![](attach:att_a)"}) == set()


CTX = {"att_a": "photo", "att_b": "photo", "att_v": "video"}


class TestGallerySpec:
    def test_keeps_present_photos_dedup(self):
        out = gallery_block._validate(
            {"type": "gallery", "images": ["att_a", "att_b", "att_a", "att_v", "att_x"], "caption": " hi "},
            CTX,
        )
        assert out == {"type": "gallery", "images": ["att_a", "att_b"], "caption": "hi"}

    def test_none_when_no_valid_images(self):
        assert gallery_block._validate({"type": "gallery", "images": ["att_v", "att_x"]}, CTX) is None
        assert gallery_block._validate({"type": "gallery", "images": "nope"}, CTX) is None

    def test_caption_optional_and_capped(self):
        out = gallery_block._validate({"type": "gallery", "images": ["att_a"], "caption": "x" * 500}, CTX)
        assert len(out["caption"]) == 300
        out2 = gallery_block._validate({"type": "gallery", "images": ["att_a"]}, CTX)
        assert out2["caption"] == ""

    def test_collect_returns_image_codes(self):
        assert gallery_block._collect({"type": "gallery", "images": ["att_a", "att_b", 5]}) == {"att_a", "att_b"}


class TestFigureSpec:
    def test_basic_photo(self):
        out = figure_block._validate(
            {"type": "figure", "media": "att_a", "width": 33, "align": "left", "caption": "c"}, CTX
        )
        assert out == {"type": "figure", "media": "att_a", "width": 33, "align": "left", "caption": "c"}

    def test_accepts_video(self):
        # figure is kind-polymorphic: any media present in ctx, not just photos
        out = figure_block._validate(
            {"type": "figure", "media": "att_v", "width": 100, "align": "full", "caption": ""}, CTX
        )
        assert out["media"] == "att_v" and out["align"] == "full"

    def test_rejects_foreign_or_missing(self):
        assert figure_block._validate({"type": "figure", "media": "att_x"}, CTX) is None
        assert figure_block._validate({"type": "figure"}, CTX) is None

    def test_snaps_width_and_align_defaults(self):
        out = figure_block._validate({"type": "figure", "media": "att_a", "width": 40, "align": "weird"}, CTX)
        assert out["width"] == 33   # 40 snaps to nearest of {25,33,50,100}
        assert out["align"] == "left"

    def test_width_100_forces_full(self):
        out = figure_block._validate({"type": "figure", "media": "att_a", "width": 100, "align": "left"}, CTX)
        assert out["align"] == "full"

    def test_collect_returns_media(self):
        assert figure_block._collect({"type": "figure", "media": "att_a"}) == {"att_a"}


PROC_CTX = {"att_a": "photo", "att_b": "photo", "att_v": "video"}


class TestBuildSchema:
    def test_shape(self):
        schema = build_blocks_schema()
        assert schema["type"] == "object"
        assert schema["required"] == ["blocks"]
        members = schema["properties"]["blocks"]["items"]["anyOf"]
        consts = {m["properties"]["type"]["const"] for m in members}
        assert {"markdown", "gallery", "figure"} <= consts
        fig = next(m for m in members if m["properties"]["type"]["const"] == "figure")
        assert fig["properties"]["width"]["enum"] == [25, 33, 50, 100]


class TestNormalizeBlocks:
    def test_drops_unknown_and_invalid_keeps_order_collects_used(self):
        raw = [
            {"type": "markdown", "text": "Прелюдія"},
            {"type": "bogus", "x": 1},
            {"type": "gallery", "images": ["att_a", "att_v"], "caption": "c"},
            {"type": "figure", "media": "att_v", "width": 100, "align": "full", "caption": ""},
            {"type": "figure", "media": "att_x"},  # foreign -> dropped
        ]
        blocks, used = normalize_blocks(raw, PROC_CTX)
        assert [b["type"] for b in blocks] == ["markdown", "gallery", "figure"]
        assert blocks[1]["images"] == ["att_a"]   # att_v (video) dropped from gallery
        assert used == {"att_a", "att_v"}

    def test_non_list_returns_empty(self):
        assert normalize_blocks("nope", PROC_CTX) == ([], set())

    def test_non_string_type_is_dropped(self):
        # untrusted LLM output may carry a non-hashable / non-string type
        raw = [
            {"type": ["markdown"], "text": "x"},   # unhashable type -> must not crash
            {"type": 5, "text": "y"},               # non-string type -> dropped
            {"type": "markdown", "text": "ок"},
        ]
        blocks, used = normalize_blocks(raw, PROC_CTX)
        assert blocks == [{"type": "markdown", "text": "ок"}]
        assert used == set()


class TestCollectShortcodes:
    def test_unions_media_blocks_only(self):
        blocks = [
            {"type": "markdown", "text": "![](attach:att_z)"},          # no media collected
            {"type": "gallery", "images": ["att_a", "att_b"], "caption": ""},
            {"type": "figure", "media": "att_v", "width": 100, "align": "full", "caption": ""},
        ]
        assert collect_shortcodes(blocks) == {"att_a", "att_b", "att_v"}

    def test_non_string_type_ignored(self):
        assert collect_shortcodes([{"type": ["figure"], "media": "att_a"}]) == set()


class TestBlocksToText:
    def test_prose_plus_captions_only(self):
        blocks = [
            {"type": "markdown", "text": "## Ранок\n\nТекст"},
            {"type": "figure", "media": "att_a", "width": 50, "align": "center", "caption": "Підпис"},
        ]
        text = blocks_to_text(blocks)
        assert "## Ранок" in text and "Текст" in text and "Підпис" in text
        assert "att_a" not in text


class TestEnsureAllBlocks:
    def test_appends_figure_for_missing(self):
        blocks = [{"type": "markdown", "text": "Текст"}]
        out = ensure_all_blocks(blocks, ["att_a", "att_b"], {"att_a"})
        assert out[0]["type"] == "markdown"
        appended = out[1:]
        assert [b["media"] for b in appended] == ["att_b"]
        assert appended[0] == {"type": "figure", "media": "att_b", "width": 100, "align": "full", "caption": ""}

    def test_noop_when_all_placed(self):
        blocks = [{"type": "figure", "media": "att_a", "width": 100, "align": "full", "caption": ""}]
        assert ensure_all_blocks(blocks, ["att_a"], {"att_a"}) == blocks
