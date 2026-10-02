from __future__ import annotations

import os
import re
from datetime import timedelta
from pathlib import Path
from zoneinfo import ZoneInfoNotFoundError

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, FloatPrompt, IntPrompt, Prompt
from rich.table import Table

from . import __version__
from .analysis import AnalysisOptions, analyze_chat
from .calendar_utils import parse_local_datetime, resolve_timezone
from .identity import Side, sender_counts, sender_names, suggest_sides
from .models import CensoredInterval, ExportFile
from .parser import ExportValidationError, load_exports, merge_messages
from .reporting import generate_bundle
from .settings import AppSettings, load_settings, save_settings


console = Console()

BANNER = r"""Emptiness Scraper
 _____                 _   _                          ____                                  
| ____|_ __ ___  _ __ | |_(_)_ __   ___  ___ ___   / ___|  ___ _ __ __ _ _ __   ___ _ __ 
|  _| | '_ ` _ \| '_ \| __| | '_ \ / _ \/ __/ __|  \___ \ / __| '__/ _` | '_ \ / _ \ '__|
| |___| | | | | | |_) | |_| | | | |  __/\__ \__ \   ___) | (__| | | (_| | |_) |  __/ |   
|_____|_| |_| |_| .__/ \__|_|_| |_|\___||___/___/  |____/ \___|_|  \__,_| .__/ \___|_|   
                |_|                                                       |_|               """

CREATOR_NOTE = "this tool is made by @AwraEsh just to use it on one person, i wanted to keep it private but i thought it might be useful for you too. i made this outa heart so. yea enjoy!"


def about_text() -> str:
    return f"Emptiness Scraper {__version__}\nGitHub: @AwraEsh\nTelegram: @Ou_Rash"


def parse_path_input(value: str) -> list[str]:
    return [part.strip().strip('"') for part in value.split(";") if part.strip().strip('"')]


def _show_exports(exports: list[ExportFile]) -> None:
    table = Table(title="Validated exports")
    for column in ("Order", "File", "Messages", "First timestamp", "Last timestamp", "Services"):
        table.add_column(column)
    for index, export in enumerate(exports, start=1):
        table.add_row(
            str(index),
            export.path.name,
            str(len(export.messages)),
            export.first_timestamp.isoformat() if export.first_timestamp else "Empty",
            export.last_timestamp.isoformat() if export.last_timestamp else "Empty",
            str(export.service_count),
        )
    console.print(table)


def _choose_sides(exports: list[ExportFile]) -> tuple[list[Side], set[str]]:
    messages = [message for export in exports for message in export.messages]
    counts = sender_counts(messages)
    names = sender_names(messages)
    table = Table(title="Detected senders")
    table.add_column("Sender ID")
    table.add_column("Latest name")
    table.add_column("Messages", justify="right")
    for sender_id, count in counts.most_common():
        table.add_row(sender_id, names.get(sender_id, sender_id), str(count))
    console.print(table)
    suggested_a, suggested_b, excluded = suggest_sides(exports)
    console.print(f"Suggested Participant A: [bold]{suggested_a.label}[/] — {', '.join(sorted(suggested_a.ids))}")
    console.print(f"Suggested Participant B: [bold]{suggested_b.label}[/] — {', '.join(sorted(suggested_b.ids))}")
    if excluded:
        console.print(f"Suggested exclusions: {', '.join(sorted(excluded))}")
    if Confirm.ask("Use this participant mapping?", default=True):
        return [suggested_a, suggested_b], excluded
    all_ids = set(counts)
    ids_a = {value.strip() for value in Prompt.ask("Participant A sender IDs, comma-separated").split(",") if value.strip()}
    ids_b = {value.strip() for value in Prompt.ask("Participant B sender IDs, comma-separated").split(",") if value.strip()}
    if not ids_a or not ids_b or ids_a & ids_b or not (ids_a | ids_b) <= all_ids:
        raise ValueError("Each participant needs distinct sender IDs from the detected list.")
    label_a = Prompt.ask("Participant A report name", default=names.get(next(iter(ids_a)), "Participant A"))
    label_b = Prompt.ask("Participant B report name", default=names.get(next(iter(ids_b)), "Participant B"))
    if label_a == label_b:
        label_b = f"{label_b} (B)"
    return [Side(label_a, ids_a), Side(label_b, ids_b)], all_ids - ids_a - ids_b


def _censored_intervals(timezone_name: str) -> list[CensoredInterval]:
    intervals: list[CensoredInterval] = []
    console.print("Enter incomplete intervals as local Gregorian date-times. Leave the start empty to finish.")
    while True:
        start_text = Prompt.ask("Interval start, YYYY-MM-DD HH:MM", default="").strip()
        if not start_text:
            break
        end_text = Prompt.ask("Interval end, YYYY-MM-DD HH:MM").strip()
        start = parse_local_datetime(start_text, timezone_name)
        end = parse_local_datetime(end_text, timezone_name)
        if end <= start:
            raise ValueError("Interval end must be later than its start.")
        label = Prompt.ask("Interval label", default="Incomplete or externally censored interval")
        intervals.append(CensoredInterval(start=start, end=end, label=label))
    return intervals


def _file_audit(exports: list[ExportFile]) -> tuple[list[dict], list[str]]:
    rows: list[dict] = []
    warnings: list[str] = []
    for index, export in enumerate(exports):
        rows.append(
            {
                "name": export.path.name,
                "messages": len(export.messages),
                "service_records": export.service_count,
                "first_timestamp": export.first_timestamp.isoformat() if export.first_timestamp else None,
                "last_timestamp": export.last_timestamp.isoformat() if export.last_timestamp else None,
            }
        )
        if index and exports[index - 1].last_timestamp and export.first_timestamp:
            difference = export.first_timestamp - exports[index - 1].last_timestamp
            if difference < timedelta(0):
                warnings.append(f"{export.path.name} overlaps the previous export by {abs(difference)}.")
            else:
                warnings.append(f"Gap before {export.path.name}: {difference}.")
    return rows, warnings


def run_analysis(settings: AppSettings) -> None:
    raw_paths = Prompt.ask("JSON export paths or a directory; separate multiple paths with semicolons")
    exports = load_exports(parse_path_input(raw_paths))
    _show_exports(exports)
    sides, excluded = _choose_sides(exports)
    timezone_name = settings.timezone
    session_gap = settings.session_gap_hours
    censored: list[CensoredInterval] = []
    if Confirm.ask("Open advanced settings for this analysis?", default=False):
        timezone_name = Prompt.ask("Display timezone", default=timezone_name)
        resolve_timezone(timezone_name)
        session_gap = FloatPrompt.ask("Session gap in hours", default=session_gap)
        if session_gap <= 0:
            raise ValueError("Session gap must be positive.")
        if Confirm.ask("Add incomplete or externally censored intervals?", default=False):
            censored = _censored_intervals(timezone_name)
    merged_messages, duplicate_count = merge_messages(exports)
    messages = [message for message in merged_messages if message.sender_id not in excluded]
    files, warnings = _file_audit(exports)
    if duplicate_count:
        warnings.append(f"Removed {duplicate_count} exact duplicate message record(s) across exports.")
    options = AnalysisOptions(
        session_gap_hours=session_gap,
        timezone=timezone_name,
        censored_intervals=censored,
        stopwords=set(settings.english_stopwords + settings.persian_stopwords),
        service_count=sum(export.service_count for export in exports),
        files=files,
        rules=settings.rules,
    )
    with console.status("Analyzing exports..."):
        result = analyze_chat(messages, sides, options)
        result["audit"]["warnings"].extend(warnings)
        output_root = Path(settings.output_directory).expanduser().resolve()
        output = generate_bundle(result, output_root)
    console.print(Panel.fit(f"Report created:\n[bold green]{output}[/]", title="Analysis complete"))
    console.print("Tip: Send the generated Markdown files to your Telegram Saved Messages for the best reading experience.")


def validate_exports() -> None:
    raw_paths = Prompt.ask("JSON export paths or a directory; separate multiple paths with semicolons")
    exports = load_exports(parse_path_input(raw_paths))
    _show_exports(exports)
    files, warnings = _file_audit(exports)
    console.print(f"[green]Valid:[/] {len(files)} one-to-one Telegram export(s).")
    for warning in warnings:
        console.print(f"[yellow]- {warning}[/]")


def view_reports(settings: AppSettings) -> None:
    root = Path(settings.output_directory).expanduser().resolve()
    reports = sorted((path for path in root.glob("emptiness-scraper-*") if path.is_dir()), reverse=True) if root.exists() else []
    if not reports:
        console.print("No generated reports were found.")
        return
    table = Table(title=f"Reports in {root}")
    table.add_column("#")
    table.add_column("Directory")
    for index, path in enumerate(reports, start=1):
        table.add_row(str(index), str(path))
    console.print(table)


def edit_settings(settings: AppSettings) -> AppSettings:
    while True:
        console.print("\n1. Show settings\n2. Set timezone\n3. Set session gap\n4. Set output directory\n5. Edit stopwords\n6. Edit language rules\n7. Reset defaults\n8. Back")
        choice = IntPrompt.ask("Choose", choices=[str(value) for value in range(1, 9)])
        if choice == 1:
            console.print_json(data={"timezone": settings.timezone, "session_gap_hours": settings.session_gap_hours, "output_directory": settings.output_directory, "english_stopwords": settings.english_stopwords, "persian_stopwords": settings.persian_stopwords, "rules": settings.rules})
        elif choice == 2:
            value = Prompt.ask("Timezone", default=settings.timezone)
            resolve_timezone(value)
            settings.timezone = value
        elif choice == 3:
            value = FloatPrompt.ask("Session gap in hours", default=settings.session_gap_hours)
            if value > 0:
                settings.session_gap_hours = value
        elif choice == 4:
            settings.output_directory = Prompt.ask("Output directory", default=settings.output_directory)
        elif choice == 5:
            language = Prompt.ask("Language", choices=["english", "persian"], default="english")
            current = settings.english_stopwords if language == "english" else settings.persian_stopwords
            updated = [value.strip() for value in Prompt.ask("Comma-separated stopwords", default=", ".join(current)).split(",") if value.strip()]
            if language == "english":
                settings.english_stopwords = updated
            else:
                settings.persian_stopwords = updated
        elif choice == 6:
            category = Prompt.ask("Rule category", default="check_in")
            current = settings.rules.get(category, [])
            settings.rules[category] = [value.strip() for value in Prompt.ask("Patterns separated with semicolons", default="; ".join(current)).split(";") if value.strip()]
        elif choice == 7 and Confirm.ask("Reset every setting to its default?", default=False):
            settings = AppSettings()
        else:
            save_settings(settings)
            return settings
        save_settings(settings)


def main() -> int:
    if os.environ.get("EMPTYNESS_SCRAPER_SMOKE") == "1":
        console.print(BANNER, style="bold cyan", markup=False, soft_wrap=True)
        console.print(CREATOR_NOTE, style="italic", markup=False)
        console.print(about_text())
        return 0
    settings = load_settings()
    console.print(BANNER, style="bold cyan", markup=False, soft_wrap=True)
    console.print(CREATOR_NOTE, style="italic", markup=False)
    console.print()
    console.print(Panel.fit(about_text(), subtitle="Private, offline Telegram chat metrics"))
    while True:
        console.print("\n1. New Analysis\n2. View Previous Reports\n3. Settings and Language Rules\n4. Validate Exports\n5. About\n6. Exit")
        try:
            choice = IntPrompt.ask("Choose", choices=["1", "2", "3", "4", "5", "6"])
            if choice == 1:
                run_analysis(settings)
            elif choice == 2:
                view_reports(settings)
            elif choice == 3:
                settings = edit_settings(settings)
            elif choice == 4:
                validate_exports()
            elif choice == 5:
                console.print(Panel.fit(about_text()))
            else:
                return 0
        except (ExportValidationError, ValueError, OSError, ZoneInfoNotFoundError) as error:
            console.print(f"[bold red]Error:[/] {error}")
        except (KeyboardInterrupt, EOFError):
            console.print("\nCancelled. No input files were changed.")
            return 130
