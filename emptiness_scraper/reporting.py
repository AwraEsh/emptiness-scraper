from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .calendar_utils import dual_date


AUTHOR = "GitHub: @AwraEsh  |  Telegram: @Ou_Rash"


def _table(headers: list[str], rows: list[list[Any]]) -> str:
    def clean(value: Any) -> str:
        return str(value).replace("|", "\\|").replace("\n", " ")
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    lines.extend("| " + " | ".join(clean(value) for value in row) + " |" for row in rows)
    return "\n".join(lines)


def _bars(rows: list[dict[str, Any]], label_key: str, value_key: str, width: int = 28) -> str:
    if not rows:
        return "No data."
    maximum = max(float(row.get(value_key, 0)) for row in rows) or 1
    lines = []
    for row in rows:
        value = float(row.get(value_key, 0))
        bar = "█" * max(1, round(value / maximum * width)) if value else ""
        lines.append(f"`{row.get(label_key, '')}` {bar} {value:g}")
    return "  \n".join(lines)


def _unique_directory(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    base = datetime.now().strftime("emptiness-scraper-%Y%m%d-%H%M%S")
    candidate = root / base
    suffix = 2
    while candidate.exists():
        candidate = root / f"{base}-{suffix}"
        suffix += 1
    candidate.mkdir()
    return candidate


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _main_report(result: dict[str, Any]) -> str:
    summary = result["summary"]
    timezone_name = result.get("configuration", {}).get("timezone", "Asia/Tehran")
    start_dual = dual_date(datetime.fromisoformat(summary["start"]), timezone_name)
    end_dual = dual_date(datetime.fromisoformat(summary["end"]), timezone_name)
    participant_rows = [[name, values.get("messages", 0), values.get("turns", 0), values.get("words", 0), values.get("characters", 0), values.get("reactions", 0)] for name, values in result["participants"].items()]
    month_rows = [[row.get("month"), row.get("message_count"), row.get("session_count"), row.get("active_days"), row.get("messages_per_active_day", "")] for row in result["months"]]
    warning_lines = "\n".join(f"- {warning}" for warning in result.get("audit", {}).get("warnings", [])) or "- No structural warnings."
    return f"""# Emptiness Scraper Report

{AUTHOR}

> Privacy notice: this report can contain participant names and excerpts from the selected private chat. Store and share it carefully.

## Summary

- Messages: **{summary['message_count']}**
- Active days: **{summary['active_days']}**
- Gregorian / Jalali start: `{start_dual}`
- Gregorian / Jalali end: `{end_dual}`
- Files: **{summary['file_count']}**
- Service records excluded: **{summary['service_count']}**

## Participant comparison

{_table(['Participant', 'Messages', 'Turns', 'Words', 'Characters', 'Reactions'], participant_rows)}

## Session sensitivity

{_table(['Gap threshold', 'Sessions'], [[f'{hours} hours', count] for hours, count in result['session_sensitivity'].items()])}

## Monthly timeline

{_table(['Month', 'Messages', 'Sessions', 'Active days', 'Messages / active day'], month_rows)}

{_bars(result['months'], 'month', 'message_count')}

## Data-quality warnings

{warning_lines}

## Appendices

- [Sessions and gaps](appendix_sessions_and_gaps.md)
- [Responses](appendix_responses.md)
- [Text and emoji](appendix_text_and_emoji.md)
- [Rule-based events](appendix_rule_events.md)

## Interpretation boundary

This software reports observable timing, participation, and text patterns. It does not infer attraction, intent, personality, or psychological state. Rule-based signals are heuristics whose exact definitions are included in the report data.

Tip: Send the generated Markdown files to your Telegram Saved Messages for the best reading experience.
"""


def generate_bundle(result: dict[str, Any], output_root: Path) -> Path:
    output = _unique_directory(Path(output_root))
    (output / "report.md").write_text(_main_report(result), encoding="utf-8")
    session_rows = [[row.get("index"), row.get("start"), row.get("end"), row.get("message_count"), row.get("turn_count"), row.get("initiator"), row.get("final_sender"), row.get("restart_type"), row.get("censored")] for row in result["sessions"]]
    gap_rows = [[row.get("from"), row.get("to"), round(row.get("seconds", 0) / 3600, 3), row.get("previous_sender"), row.get("returning_sender"), row.get("same_sender_restart"), row.get("comparison_safe")] for row in result["gaps"]]
    sessions_md = f"# Sessions and gaps\n\n{AUTHOR}\n\n## Sessions\n\n{_table(['#', 'Start', 'End', 'Messages', 'Turns', 'Initiator', 'Final sender', 'Restart type', 'Censored'], session_rows)}\n\n## Gaps\n\n{_table(['From', 'To', 'Hours', 'Previous', 'Returning', 'Same sender', 'Safe'], gap_rows)}\n"
    (output / "appendix_sessions_and_gaps.md").write_text(sessions_md, encoding="utf-8")
    response_rows = [[row.get("sent_at"), row.get("responder"), row.get("previous_sender"), row.get("latency_seconds"), row.get("comparison_safe"), row.get("month"), row.get("weekday"), row.get("hour")] for row in result["responses"]]
    statistics_rows = []
    for participant, modes in result.get("response_statistics", {}).items():
        if "raw" not in modes:
            statistics_rows.append([participant, modes.get("count", 0), modes.get("mean_seconds", ""), modes.get("median_seconds", ""), modes.get("p90_seconds", "")])
            continue
        for mode, values in modes.items():
            statistics_rows.append([f"{participant} — {mode}", values.get("count", 0), round(values.get("mean_seconds", 0), 3), round(values.get("median_seconds", 0), 3), round(values.get("p90_seconds", 0), 3)])
    band_rows = [[name, count] for name, count in result.get("response_breakdowns", {}).get("bands", {}).items()]
    reply_rows = [[row.get("timestamp"), row.get("participant"), row.get("target_participant"), row.get("age_seconds"), row.get("message_id"), row.get("target_message_id")] for row in result.get("explicit_reply_ages", [])]
    hourly_rows = [[row.get("participant"), row.get("hour"), row.get("response_count"), row.get("median_seconds"), row.get("mean_seconds")] for row in result.get("response_by_participant_hour", [])]
    responses_md = f"# Responses\n\n{AUTHOR}\n\n## Summary\n\n{_table(['Participant / mode', 'Count', 'Mean seconds', 'Median seconds', 'P90 seconds'], statistics_rows)}\n\n## Cumulative latency bands\n\n{_table(['Band', 'Count'], band_rows)}\n\n## Response hours by participant\n\n{_table(['Participant', 'Hour', 'Responses', 'Median seconds', 'Mean seconds'], hourly_rows)}\n\n## Every sender switch\n\n{_table(['Time', 'Responder', 'Previous', 'Seconds', 'Safe', 'Month', 'Weekday', 'Hour'], response_rows)}\n\n## Explicit reply ages\n\n{_table(['Time', 'Participant', 'Target participant', 'Age seconds', 'Message ID', 'Target ID'], reply_rows)}\n"
    (output / "appendix_responses.md").write_text(responses_md, encoding="utf-8")
    text = result["text"]
    participant_sections = []
    for participant, values in result.get("participant_text", {}).items():
        participant_sections.append(f"## {participant}: words\n\n{_table(['Word', 'Count'], values.get('words', []))}\n\n## {participant}: emoji\n\n{_table(['Emoji', 'Count'], values.get('emojis', []))}")
    sample_rows = [[word, ", ".join(samples)] for word, samples in text.get("normalized_word_samples", {}).items()]
    participant_block = "\n\n".join(participant_sections)
    text_md = f"# Text and emoji\n\n{AUTHOR}\n\n## Combined normalized words\n\n{_table(['Word', 'Count'], text.get('words', []))}\n\n## Raw word forms\n\n{_table(['Raw form', 'Count'], text.get('raw_words', []))}\n\n## Normalized word samples\n\n{_table(['Normalized', 'Observed raw forms'], sample_rows)}\n\n## Combined phrases\n\n{_table(['Phrase', 'Count'], text.get('phrases', []))}\n\n## Combined emoji\n\n{_table(['Emoji', 'Count'], text.get('emojis', []))}\n\n{participant_block}\n\n## Repeated sentences\n\n{_table(['Normalized sentence', 'Count'], text.get('repeated_sentences', []))}\n\n## Repeated messages\n\n{_table(['Normalized text', 'Count'], text.get('repeated_messages', []))}\n"
    (output / "appendix_text_and_emoji.md").write_text(text_md, encoding="utf-8")
    signal_rows = [[row.get("timestamp"), row.get("participant"), row.get("category"), row.get("excerpt"), row.get("rule")] for row in result["signals"]]
    events_md = f"# Rule-based events\n\n{AUTHOR}\n\nThese events are transparent heuristic matches, not interpretations of intent.\n\n{_table(['Time', 'Participant', 'Category', 'Excerpt', 'Rule'], signal_rows)}\n"
    (output / "appendix_rule_events.md").write_text(events_md, encoding="utf-8")
    (output / "analysis.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    csv_dir = output / "csv"
    for name in ("sessions", "turns", "responses", "response_by_participant_hour", "explicit_reply_ages", "gaps", "months", "quarters", "exports", "participant_words", "participant_emojis", "participant_activity_hours", "signals"):
        _write_csv(csv_dir / f"{name}.csv", result.get(name, []))
    return output
