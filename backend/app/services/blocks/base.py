from dataclasses import dataclass
from typing import Callable, Optional

# ctx is the user's media map: {shortcode: kind}
ValidateFn = Callable[[dict, dict], Optional[dict]]
# collect reports the media shortcodes a block REFERENCES (valid or not); it does
# NOT filter by ctx — that's validate's job.
CollectFn = Callable[[dict], set]


@dataclass(frozen=True)
class BlockSpec:
    name: str
    schema: dict          # JSON-schema fragment for this block type (an anyOf member)
    validate: ValidateFn  # (block, ctx) -> normalized block | None (drop)
    collect: CollectFn    # block -> set of media shortcodes it references


BLOCK_REGISTRY: dict[str, BlockSpec] = {}


def register(spec: BlockSpec) -> None:
    BLOCK_REGISTRY[spec.name] = spec
