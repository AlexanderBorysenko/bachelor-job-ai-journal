"""Content-block foundation. Importing this package registers all block specs."""

from app.services.blocks import markdown, gallery, figure  # noqa: F401  (registers specs)
from app.services.blocks.base import BLOCK_REGISTRY, BlockSpec, register  # noqa: F401
from app.services.blocks.process import (  # noqa: F401
    build_blocks_schema,
    normalize_blocks,
    collect_shortcodes,
    blocks_to_text,
    ensure_all_blocks,
)
