from typing import Optional

from app.services.blocks.base import BlockSpec, register

MAX_IMAGES = 30
MAX_CAPTION = 300

SCHEMA = {
    "type": "object",
    "properties": {
        "type": {"const": "gallery"},
        "images": {"type": "array", "items": {"type": "string"}},
        "caption": {"type": "string"},
    },
    "required": ["type", "images", "caption"],
    "additionalProperties": False,
}


def _validate(block: dict, ctx: dict) -> Optional[dict]:
    raw = block.get("images")
    if not isinstance(raw, list):
        return None
    images: list[str] = []
    for code in raw:
        if isinstance(code, str) and ctx.get(code) == "photo" and code not in images:
            images.append(code)
        if len(images) >= MAX_IMAGES:
            break
    if not images:
        return None
    caption = str(block.get("caption") or "").strip()[:MAX_CAPTION]
    return {"type": "gallery", "images": images, "caption": caption}


def _collect(block: dict) -> set:
    return {c for c in (block.get("images") or []) if isinstance(c, str)}


register(BlockSpec(name="gallery", schema=SCHEMA, validate=_validate, collect=_collect))
