from __future__ import annotations

import os
import sys

from .branding import BANNER, CREATOR_NOTE, about_text
from .services import parse_path_input


def main() -> int:
    if os.environ.get("EMPTYNESS_SCRAPER_SMOKE") == "1":
        print(BANNER)
        print(CREATOR_NOTE)
        print(about_text())
        return 0
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print("Emptiness Scraper needs an interactive terminal. Open a terminal and run python run.py.", file=sys.stderr)
        return 2
    from .tui import EmptinessApp

    try:
        EmptinessApp().run()
    except KeyboardInterrupt:
        return 130
    return 0
