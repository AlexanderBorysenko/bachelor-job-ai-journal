from typing import Optional

from app.services.blocks.base import BlockSpec, register

SCHEMA = {
    "type": "object",
    "properties": {
        "type": {"const": "markdown"},
        "text": {"type": "string"},
    },
    "required": ["type", "text"],
    "additionalProperties": False,
}


def _validate(block: dict, ctx: dict) -> Optional[dict]:
    text = block.get("text")
    if not isinstance(text, str) or not text.strip():
        return None
    return {"type": "markdown", "text": text}


def _collect(block: dict) -> set:
    return set()


register(BlockSpec(name="markdown", schema=SCHEMA, validate=_validate, collect=_collect))
