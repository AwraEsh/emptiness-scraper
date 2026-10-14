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
    try:
        while True:
            print("\nChoose your interface:\n\n1. Full-screen — Keyboard navigation, panels and report previews.\n2. Classic text — Numbered menus and prompts; better for basic terminals and screen readers.\n0. Exit\n", flush=True)
            choice = input("Choice: ").strip()
            if choice == "0":
                return 0
            if choice == "2":
                from .classic import ClassicInterface
                code = ClassicInterface().run()
                if code == 10:
                    continue
                return code
            if choice != "1":
                print("Choose 1, 2, or 0.")
                continue
            if not sys.stdin.isatty() or not sys.stdout.isatty() or os.environ.get("TERM") == "dumb":
                print("Full-screen mode needs an interactive terminal with cursor support. Choose 2 for Classic text.")
                continue
            from .tui import EmptinessApp
            EmptinessApp().run()
            return 0
    except EOFError:
        return 0
    except KeyboardInterrupt:
        print("\nCancelled.")
        return 130
