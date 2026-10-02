import csv
import json
from datetime import UTC, datetime, timedelta

from emptiness_scraper.reporting import generate_bundle


def sample_result():
    return {
        "schema_version": "1.0",
        "generated_at": "2026-01-02T00:00:00+00:00",
        "configuration": {"timezone": "Asia/Tehran", "session_gap_hours": 6},
        "summary": {
            "message_count": 3,
            "start": "2026-01-01T00:00:00+00:00",
            "end": "2026-01-01T01:00:00+00:00",
            "active_days": 1,
            "service_count": 0,
            "file_count": 1,
        },
        "participants": {
            "Alpha": {"messages": 2, "turns": 1, "words": 4, "characters": 20, "reactions": 0},
            "Beta": {"messages": 1, "turns": 1, "words": 2, "characters": 10, "reactions": 1},
        },
        "session_sensitivity": {"4": 1, "6": 1, "12": 1},
        "sessions": [
            {
                "index": 1,
                "start": "2026-01-01T00:00:00+00:00",
                "end": "2026-01-01T01:00:00+00:00",
                "duration_seconds": 3600,
                "message_count": 3,
                "turn_count": 2,
                "initiator": "Alpha",
                "final_sender": "Beta",
                "censored": False,
                "restart_type": "first_session",
            }
        ],
        "turns": [],
        "responses": [{"responder": "Beta", "latency_seconds": 60, "comparison_safe": True}],
        "gaps": [],
        "months": [{"month": "2026-01", "message_count": 3, "session_count": 1, "active_days": 1}],
        "quarters": [],
        "response_statistics": {"Beta": {"count": 1, "median_seconds": 60}},
        "text": {"words": [["hello", 2]], "emojis": [["🙂", 1]], "phrases": []},
        "signals": [],
        "audit": {"files": [{"name": "fixture.json"}], "warnings": ["Synthetic overlap warning."]},
        "definitions": {"session": "Separated by at least six hours of inactivity."},
    }


def test_generate_bundle_writes_consistent_markdown_csv_and_json(tmp_path):
    output = generate_bundle(sample_result(), tmp_path)

    expected = {
        "report.md",
        "appendix_sessions_and_gaps.md",
        "appendix_responses.md",
        "appendix_text_and_emoji.md",
        "appendix_rule_events.md",
        "analysis.json",
    }
    assert expected.issubset({path.name for path in output.iterdir()})
    assert "GitHub: @AwraEsh" in (output / "report.md").read_text(encoding="utf-8")
    assert "Telegram Saved Messages" in (output / "report.md").read_text(encoding="utf-8")
    data = json.loads((output / "analysis.json").read_text(encoding="utf-8"))
    with (output / "csv" / "sessions.csv").open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    assert data["summary"]["message_count"] == 3
    assert int(rows[0]["message_count"]) == 3
    assert "Jalali" in (output / "report.md").read_text(encoding="utf-8")
    assert "█" in (output / "report.md").read_text(encoding="utf-8")
    assert "Synthetic overlap warning" in (output / "report.md").read_text(encoding="utf-8")


def test_generate_bundle_never_overwrites_a_previous_run(tmp_path):
    first = generate_bundle(sample_result(), tmp_path)
    second = generate_bundle(sample_result(), tmp_path)

    assert first != second
    assert first.exists() and second.exists()
