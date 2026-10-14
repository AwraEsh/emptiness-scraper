from __future__ import annotations

import unicodedata
import os
from collections.abc import Mapping
from functools import lru_cache
import regex
from arabic_reshaper import ArabicReshaper
from bidi.algorithm import get_display
from markdown_it import MarkdownIt
from rich.text import Text


_direction_controls = frozenset("\u061c\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069")
_render_mode = "native"
_reshaper = ArabicReshaper(configuration={"delete_harakat": False, "shift_harakat_position": True})


def resolve_rendering(mode: str, environment: Mapping[str, str] | None = None) -> tuple[str, str]:
    if mode not in {"auto", "native", "compatibility"}:
        raise ValueError("Terminal rendering must be auto, native, or compatibility.")
    env = os.environ if environment is None else environment
    terminal = "VTE / GNOME-compatible terminal" if env.get("VTE_VERSION") or env.get("GNOME_TERMINAL_SCREEN") or env.get("GNOME_TERMINAL_SERVICE") else "Unknown terminal"
    return ("native" if mode == "auto" else mode), terminal


def configure_rendering(mode: str, environment: Mapping[str, str] | None = None) -> tuple[str, str]:
    global _render_mode
    _render_mode, terminal = resolve_rendering(mode, environment)
    return _render_mode, terminal


def display_text(value: str, *, single_line: bool = False) -> str:
    """Sanitize display controls without pre-shaping or reversing native Unicode text."""
    return _prepare_text(value, single_line, _render_mode)


@lru_cache(maxsize=2048)
def _prepare_text(value: str, single_line: bool, mode: str) -> str:
    value = value.replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ")
    value = "".join(c for c in value if c not in _direction_controls and (c == "\n" or unicodedata.category(c) != "Cc"))
    if single_line:
        value = " ".join(value.splitlines())
    if mode == "native":
        return value
    lines = []
    for line in value.split("\n"):
        if any(unicodedata.bidirectional(c) in {"R", "AL"} for c in line):
            clusters: dict[str, str] = {}
            def protect(match: regex.Match) -> str:
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
