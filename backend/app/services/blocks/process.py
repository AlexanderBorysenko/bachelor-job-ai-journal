from app.services.blocks.base import BLOCK_REGISTRY


def build_blocks_schema() -> dict:
    """Structured-output schema: a flat list of typed blocks (anyOf of the
    registered block fragments). No recursion; additionalProperties false."""
    return {
        "type": "object",
        "properties": {
            "blocks": {
                "type": "array",
                "items": {"anyOf": [spec.schema for spec in BLOCK_REGISTRY.values()]},
            },
        },
        "required": ["blocks"],
        "additionalProperties": False,
    }


def normalize_blocks(blocks, ctx: dict):
    """Validate + normalize every block via its spec. Drops unknown/invalid
    blocks. Returns (clean_blocks, used_shortcodes)."""
    clean: list[dict] = []
    used: set = set()
    if not isinstance(blocks, list):
        return clean, used
    for b in blocks:
        if not isinstance(b, dict):
            continue
        t = b.get("type")
        if not isinstance(t, str):
            continue
        spec = BLOCK_REGISTRY.get(t)
        if spec is None:
            continue
        norm = spec.validate(b, ctx)
        if norm is None:
            continue
        clean.append(norm)
        used |= spec.collect(norm)
    return clean, used


def collect_shortcodes(blocks) -> set:
    """Every media shortcode referenced by the (stored) blocks — used to build
    the per-entry media manifest."""
    codes: set = set()
    if not isinstance(blocks, list):
        return codes
    for b in blocks:
        if not isinstance(b, dict):
            continue
        t = b.get("type")
        if not isinstance(t, str):
            continue
        spec = BLOCK_REGISTRY.get(t)
        if spec is not None:
            codes |= spec.collect(b)
    return codes


def blocks_to_text(blocks) -> str:
    """Plain-text projection for text-only consumers (highlights, previews):
    markdown prose + widget captions."""
    parts: list[str] = []
    if not isinstance(blocks, list):
        return ""
    for b in blocks:
        if not isinstance(b, dict):
            continue
        if b.get("type") == "markdown":
            t = b.get("text")
            if isinstance(t, str) and t.strip():
                parts.append(t.strip())
        else:
            cap = b.get("caption")
            if isinstance(cap, str) and cap.strip():
                parts.append(cap.strip())
    return "\n\n".join(parts)


def ensure_all_blocks(blocks: list, shortcodes, used) -> list:
    """Completeness pass: every media file must be placed. Appends a trailing
    full-width `figure` block for any shortcode not already placed."""
    placed = set(used)
    missing = [s for s in shortcodes if s not in placed]
    if not missing:
        return blocks
    extra = [
        {"type": "figure", "media": s, "width": 100, "align": "full", "caption": ""}
        for s in missing
    ]
    return blocks + extra
