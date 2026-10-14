from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from itertools import islice
from pathlib import Path
import re
from typing import Callable

from .analysis import AnalysisOptions, analyze_chat
from .calendar_utils import parse_local_datetime
from .identity import Side
from .models import CensoredInterval, ExportFile
from .parser import load_exports, merge_messages
from .reporting import generate_bundle
from .settings import AppSettings, validate_settings


def parse_path_input(value: str) -> list[str]:
    paths: list[str] = []
    current: list[str] = []
    quote = None
    for character in value:
        if character in {'"', "'"} and (quote is None or quote == character):
            quote = None if quote else character
        elif character in {";", "\n"} and quote is None:
            if "".join(current).strip():
                paths.append("".join(current).strip())
            current = []
        else:
            current.append(character)
    if quote:
        raise ValueError("Unclosed quote in export path.")
    if "".join(current).strip():
        paths.append("".join(current).strip())
    return paths


def load_input(value: str, timezone_name: str) -> list[ExportFile]:
    return load_exports(parse_path_input(value), timezone_name=timezone_name)


def file_audit(exports: list[ExportFile]) -> tuple[list[dict], list[str]]:
    rows = []
    warnings = []
    previous_end = None
    for export in exports:
        rows.append({
            "name": export.path.name,
            "source": export.messages[0].source if export.messages else export.path.name,
            "messages": len(export.messages),
            "service_records": export.service_count,
            "first_timestamp": export.first_timestamp.isoformat() if export.first_timestamp else None,
            "last_timestamp": export.last_timestamp.isoformat() if export.last_timestamp else None,
        })
        if previous_end and export.first_timestamp:
            difference = export.first_timestamp - previous_end
            if difference < timedelta(0):
                warnings.append(f"{export.path.name} overlaps the preceding timeline by {abs(difference)}.")
            else:
                warnings.append(f"Gap before {export.path.name}: {difference}.")
        if export.last_timestamp:
            previous_end = max(previous_end, export.last_timestamp) if previous_end else export.last_timestamp
    return rows, warnings


def parse_intervals(value: str, timezone_name: str) -> list[CensoredInterval]:
    intervals = []
    for index, line in enumerate(value.splitlines(), start=1):
        if not line.strip():
            continue
        parts = [part.strip() for part in line.split("|", 2)]
        if len(parts) < 2:
            raise ValueError(f"Interval line {index}: use start | end | optional label.")
        start = parse_local_datetime(parts[0], timezone_name)
        end = parse_local_datetime(parts[1], timezone_name)
        if end <= start:
            raise ValueError(f"Interval line {index}: the end must follow the start.")
        intervals.append(CensoredInterval(start, end, parts[2] if len(parts) == 3 else "Incomplete interval"))
    return intervals


def analyze_exports(
    exports: list[ExportFile], sides: list[Side], settings: AppSettings,
    intervals: list[CensoredInterval], progress: Callable[[str], None] = lambda stage: None,
) -> tuple[Path, dict]:
    validate_settings(settings)
    progress("Merging exports and calculating metrics")
    messages, duplicates = merge_messages(exports)
    files, warnings = file_audit(exports)
    if duplicates:
        warnings.append(f"Removed {duplicates} exact duplicate records across exports.")
    result = analyze_chat(messages, sides, AnalysisOptions(
        session_gap_hours=settings.session_gap_hours,
        timezone=settings.timezone,
        censored_intervals=intervals,
        stopwords=set(settings.english_stopwords + settings.persian_stopwords),
        service_count=sum(export.service_count for export in exports),
        files=files,
        rules=settings.rules,
    ))
    result["audit"]["warnings"].extend(warnings)
    progress("Writing Markdown, CSV, and JSON reports")
    output = generate_bundle(result, Path(settings.output_directory).expanduser().resolve())
    return output, result


def list_reports(root: str) -> list[Path]:
    directory = Path(root).expanduser().resolve()
    if not directory.is_dir():
        return []
    return sorted((path for path in directory.glob("emptiness-scraper-*") if (path / "report.md").is_file() and (path / "analysis.json").is_file()), reverse=True)


@dataclass(frozen=True)
class ReportPage:
    text: str
    page: int
    has_next: bool


def read_report_page(path: Path, page: int = 0, page_size: int = 160) -> ReportPage:
    if page < 0 or page_size < 1:
        raise ValueError("Invalid report page.")
    with path.open(encoding="utf-8") as handle:
        previous_line = ""
        table_header: list[str] = []
        for line in islice(handle, page * page_size):
            if previous_line.lstrip().startswith("|") and "-" in line and re.fullmatch(r"[\s|:\-]+", line):
                table_header = [previous_line, line]
            elif not line.lstrip().startswith("|"):
                table_header = []
            previous_line = line
        lines = list(islice(handle, page_size + 1))
    prefix = []
    if lines and lines[0].lstrip().startswith("|"):
        prefix = table_header
        if not prefix and previous_line.lstrip().startswith("|") and "-" in lines[0] and re.fullmatch(r"[\s|:\-]+", lines[0]):
            prefix = [previous_line]
    return ReportPage("".join(prefix + lines[:page_size]), page, len(lines) > page_size)
