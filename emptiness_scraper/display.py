from __future__ import annotations

import unicodedata
from functools import lru_cache
import regex

from arabic_reshaper import ArabicReshaper
from bidi.algorithm import get_display
from markdown_it import MarkdownIt
from rich.text import Text


_reshaper = ArabicReshaper(configuration={
    "delete_harakat": False,
    "shift_harakat_position": True,
    "support_ligatures": False,
})
_direction_controls = frozenset("\u061c\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069")


@lru_cache(maxsize=2048)
def display_text(value: str, *, single_line: bool = False) -> str:
    """Convert logical text to terminal cells; never use this for stored data or input values."""
    value = value.replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ")
    value = "".join(c for c in value if c not in _direction_controls and (c == "\n" or unicodedata.category(c) != "Cc"))
    if single_line:
        value = " ".join(value.splitlines())
    lines = []
    for line in value.split("\n"):
        if any(unicodedata.bidirectional(c) in {"R", "AL"} for c in line):
            clusters = {}
            def protect(match):
                cluster = match.group()
                if "\u200d" not in cluster or not regex.search(r"\p{Extended_Pictographic}", cluster):
                    return cluster
                marker = chr(0xF0000 + len(clusters))
                while marker in line or marker in clusters:
                    marker = chr(ord(marker) + 1)
                clusters[marker] = cluster
                return marker
            line = regex.sub(r"\X", protect, line)
            line = get_display(_reshaper.reshape(line), base_dir="L")
            line = "".join(clusters.get(c, c) for c in line)
        lines.append(line)
    return "\n".join(lines)


def display_label(value: str) -> Text:
    return Text(display_text(value, single_line=True), no_wrap=True, overflow="ellipsis")


def markdown_parser() -> MarkdownIt:
    parser = MarkdownIt("gfm-like")

    def prepare_display(state) -> None:
        for token in state.tokens:
            for child in token.children or []:
                if child.type in {"text", "code_inline"}:
                    child.content = display_text(child.content)

    parser.core.ruler.after("inline", "terminal_display", prepare_display)
    return parser
