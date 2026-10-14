from __future__ import annotations

import json
import sys
from copy import deepcopy
from dataclasses import asdict
from pathlib import Path
from typing import TextIO

from .branding import BANNER, CREATOR_NOTE, about_text
from .display import configure_rendering, display_text
from .identity import Side, sender_counts, sender_names, suggest_sides
from .services import analyze_exports, file_audit, list_reports, load_input, parse_intervals, read_report_page
from .settings import AppSettings, load_settings, save_settings, validate_settings


class ClassicInterface:
    def __init__(self, settings: AppSettings | None = None, config_path: Path | None = None,
                 *, input_stream: TextIO | None = None, output_stream: TextIO | None = None) -> None:
        self.settings = settings if settings is not None else load_settings(config_path)
        self.config_path = config_path
        self.input = input_stream if input_stream is not None else sys.stdin
        self.output = output_stream if output_stream is not None else sys.stdout
        configure_rendering(self.settings.terminal_rendering)

    def write(self, value: str = "") -> None:
        print(display_text(value), file=self.output, flush=True)

    def ask(self, label: str, default: str | None = None) -> str:
        suffix = f" [{default}]" if default is not None else ""
        self.write(f"{label}{suffix}:")
        value = self.input.readline()
        if value == "":
            raise EOFError
        return value.strip() or (default if default is not None else "")

    def choice(self, label: str, options: set[str], default: str | None = None) -> str:
        while True:
            value = self.ask(label, default).lower()
            if value in options:
                return value
            self.write("Choose one of: " + ", ".join(sorted(options)))

    def confirm(self, label: str, default: bool = False) -> bool:
        return self.choice(label + " (y/n)", {"y", "n"}, "y" if default else "n") == "y"

    def run(self) -> int:
        self.write(BANNER)
        self.write(CREATOR_NOTE)
        self.write(about_text())
        self.write("CLASSIC TEXT / numbered menus, no full-screen controls. EOF exits; Ctrl+C cancels.")
        while True:
            try:
                self.write("\n1. New Analysis\n2. View Previous Reports\n3. Settings and Language Rules\n4. Validate Exports\n5. About\n6. Exit\n0. Return to interface chooser")
                choice = self.choice("Choose", set("0123456"))
                if choice == "6":
                    return 0
                if choice == "0":
                    return 10
                if choice == "1":
                    self.analyze()
                elif choice == "2":
                    self.reports()
                elif choice == "3":
                    self.preferences()
                elif choice == "4":
                    exports, _ = self.import_exports()
                    self.write(f"Valid: {len(exports)} one-to-one export(s).")
                else:
                    self.write(about_text())
            except EOFError:
                self.write("Input closed. Goodbye.")
                return 0
            except KeyboardInterrupt:
                self.write("\nCancelled. Source files were not changed.")
                return 130
            except (ValueError, OSError, KeyError, TypeError) as error:
                self.write(f"Error: {error}")

    def import_exports(self):
        self.write("Enter JSON paths or a directory. Separate paths with semicolons; quote paths containing semicolons. Numeric filenames such as 1.json are supported; internal timestamps determine order.")
        paths = self.ask("Export paths (blank to cancel)")
        if not paths:
            raise ValueError("Import cancelled.")
        timezone = self.ask("Export timezone (IANA name or offset)", self.settings.timezone)
        exports = load_input(paths, timezone)
        _, warnings = file_audit(exports)
        for index, export in enumerate(exports, 1):
            self.write(f"\n{index}. {export.path.name}\nMessages: {len(export.messages)}; service records: {export.service_count}\nFirst: {export.first_timestamp}; last: {export.last_timestamp}")
        for warning in warnings:
            self.write("Warning: " + warning)
        return exports, timezone

    def participants(self, exports) -> list[Side]:
        messages = [message for export in exports for message in export.messages]
        counts, names = sender_counts(messages), sender_names(messages)
        for sender_id, count in counts.most_common():
            self.write(f"\nSender: {sender_id}\nName: {names[sender_id]}\nMessages: {count}")
        left, right, excluded = suggest_sides(exports)
        self.write("Suggestions use message volume and account continuity, not identity verification.")
        self.write(f"A: {left.label}; IDs: {', '.join(sorted(left.ids))}\nB: {right.label}; IDs: {', '.join(sorted(right.ids))}\nExcluded: {', '.join(sorted(excluded)) or 'None'}")
        if self.confirm("Confirm this mapping", default=False):
            return [left, right]
        self.write("Assign every account alias to A or B. All unassigned senders are excluded.")
        ids_a = {value.strip() for value in self.ask("Participant A IDs, comma-separated").split(",") if value.strip()}
        ids_b = {value.strip() for value in self.ask("Participant B IDs, comma-separated").split(",") if value.strip()}
        if not ids_a or not ids_b or ids_a & ids_b or not (ids_a | ids_b) <= set(counts):
            raise ValueError("Choose distinct, nonempty participant groups using detected IDs.")
        label_a = self.ask("Participant A name", names[sorted(ids_a)[0]])
        label_b = self.ask("Participant B name", names[sorted(ids_b)[0]])
        if not label_a or not label_b or label_a == label_b:
            raise ValueError("Participant names must be nonempty and distinct.")
        self.write(f"A: {label_a}; IDs: {', '.join(sorted(ids_a))}\nB: {label_b}; IDs: {', '.join(sorted(ids_b))}\nExcluded: {', '.join(sorted(set(counts) - ids_a - ids_b)) or 'None'}")
        if not self.confirm("Confirm this mapping"):
            raise ValueError("Analysis cancelled before generating reports.")
        return [Side(label_a, ids_a), Side(label_b, ids_b)]

    def analyze(self) -> None:
        exports, timezone = self.import_exports()
        sides = self.participants(exports)
        settings = deepcopy(self.settings)
        settings.timezone = timezone
        intervals = []
        if self.confirm("Open advanced settings for this run"):
            settings.session_gap_hours = float(self.ask("Session gap in hours", str(settings.session_gap_hours)))
            settings.output_directory = self.ask("Output directory", settings.output_directory)
            self.write("Incomplete intervals: start | end | optional label; local Gregorian dates. Blank finishes.")
            lines = []
            while line := self.ask("Interval", ""):
                lines.append(line)
            intervals = parse_intervals("\n".join(lines), timezone)
        validate_settings(settings)
        self.write("Privacy: generated reports may contain participant names and excerpts.")
        output, result = analyze_exports(exports, sides, settings, intervals, progress=self.write)
        self.write(f"Analysis complete: {output}\nMessages: {result['summary']['message_count']}")
        for warning in result["audit"]["warnings"]:
            self.write("Warning: " + str(warning))
        self.write("Tip: Send the generated Markdown files to your Telegram Saved Messages for the best reading experience.")

    def reports(self) -> None:
        reports = list_reports(self.settings.output_directory)
        if not reports:
            self.write("No generated reports found.")
            return
        for index, report in enumerate(reports, 1):
            self.write(f"{index}. {report}")
        choice = int(self.choice("Report (0 to return)", {str(i) for i in range(len(reports) + 1)}, "0"))
        if not choice:
            return
        files = sorted(reports[choice - 1].glob("*.md"))
        if not files:
            self.write("No Markdown files remain in this folder.")
            return
        for index, file in enumerate(files, 1):
            self.write(f"{index}. {file.name}")
        selection = int(self.choice("File (0 to return)", {str(i) for i in range(len(files) + 1)}, "0"))
        if not selection:
            return
        selected = files[selection - 1]
        self.write(f"File location: {selected}\nPreview is plain Markdown; saved files are unchanged.")
        page_number = 0
        while True:
            page = read_report_page(selected, page_number, page_size=40)
            self.write(f"\nPAGE {page_number + 1}\n{page.text}")
            action = self.choice("n: next; p: previous; 0: return", {"n", "p", "0"}, "0")
            if action == "0":
                return
            if action == "n" and page.has_next:
                page_number += 1
            elif action == "p" and page_number:
                page_number -= 1
            else:
                self.write("No page in that direction.")

    def preferences(self) -> None:
        while True:
            self.write("\n1. Show settings\n2. Timezone\n3. Session gap\n4. Output directory\n5. Stopwords\n6. Language rules\n7. Reset defaults\n8. Persian terminal rendering\n0. Back")
            choice = self.choice("Choose", set("012345678"))
            if choice == "0":
                return
            if choice == "1":
                self.write(json.dumps(asdict(self.settings), ensure_ascii=False, indent=2))
                continue
            updated = deepcopy(self.settings)
            try:
                if choice == "2":
                    updated.timezone = self.ask("Timezone", updated.timezone)
                elif choice == "3":
                    updated.session_gap_hours = float(self.ask("Gap in hours", str(updated.session_gap_hours)))
                elif choice == "4":
                    updated.output_directory = self.ask("Output directory", updated.output_directory)
                elif choice == "5":
                    language = self.choice("Language: english / persian", {"english", "persian"}, "english")
                    current = getattr(updated, language + "_stopwords")
                    value = self.ask("Comma-separated stopwords (use - to clear)", ", ".join(current))
                    setattr(updated, language + "_stopwords", [] if value == "-" else [word.strip() for word in value.split(",") if word.strip()])
                elif choice == "6":
                    category = self.ask("Rule category", "check_in")
                    value = self.ask("JSON array of regex strings; [] disables category", json.dumps(updated.rules.get(category, []), ensure_ascii=False))
                    patterns = json.loads(value)
                    if not isinstance(patterns, list) or any(not isinstance(pattern, str) for pattern in patterns):
                        raise ValueError("Rules must be a JSON array of strings.")
                    updated.rules[category] = patterns
                elif choice == "7":
                    if not self.confirm("Reset all preferences"):
                        continue
                    updated = AppSettings()
                else:
                    self.write("Native: GNOME/VTE shapes Unicode. Compatibility: application shapes text for terminals without native RTL. Auto uses native Unicode.")
                    updated.terminal_rendering = self.choice("Rendering", {"auto", "native", "compatibility"}, updated.terminal_rendering)
                validate_settings(updated)
                save_settings(updated, self.config_path)
                self.settings = updated
                configure_rendering(updated.terminal_rendering)
                self.write("Preferences saved. Shared with both interfaces.")
            except (ValueError, OSError, KeyError, TypeError) as error:
                self.write(f"Error: {error}. Previous settings kept.")
