from typing import Optional

from app.services.blocks.base import BlockSpec, register

WIDTHS = (25, 33, 50, 100)
ALIGNS = ("left", "right", "center", "full")
MAX_CAPTION = 300

SCHEMA = {
    "type": "object",
    "properties": {
        "type": {"const": "figure"},
        "media": {"type": "string"},
        "width": {"type": "integer", "enum": list(WIDTHS)},
        "align": {"type": "string", "enum": list(ALIGNS)},
        "caption": {"type": "string"},
    },
    "required": ["type", "media", "width", "align", "caption"],
    "additionalProperties": False,
}


def _snap_width(value) -> int:
    try:
        v = int(value)
    except (TypeError, ValueError):
        return 33
    return min(WIDTHS, key=lambda w: abs(w - v))


def _validate(block: dict, ctx: dict) -> Optional[dict]:
    code = block.get("media")
    if not isinstance(code, str) or code not in ctx:   # any media kind, must exist
        return None
    width = _snap_width(block.get("width", 33))
    align = block.get("align") if block.get("align") in ALIGNS else "left"
    if width == 100:
        align = "full"
    caption = str(block.get("caption") or "").strip()[:MAX_CAPTION]
    return {"type": "figure", "media": code, "width": width, "align": align, "caption": caption}


def _collect(block: dict) -> set:
    code = block.get("media")
    return {code} if isinstance(code, str) else set()


register(BlockSpec(name="figure", schema=SCHEMA, validate=_validate, collect=_collect))
