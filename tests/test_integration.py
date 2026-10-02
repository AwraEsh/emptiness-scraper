import json
from pathlib import Path

from emptiness_scraper.analysis import AnalysisOptions, analyze_chat
from emptiness_scraper.identity import suggest_sides
from emptiness_scraper.parser import load_exports, merge_messages
from emptiness_scraper.reporting import generate_bundle


def write_export(path, messages):
    path.write_text(
        json.dumps({"name": "Synthetic Chat", "type": "personal_chat", "id": 7, "messages": messages}),
        encoding="utf-8",
    )


def row(message_id, epoch, sender_id, sender_name, text, **extra):
    return {
        "id": message_id,
        "type": "message",
        "date": "2026-01-01T00:00:00",
        "date_unixtime": str(epoch),
        "from": sender_name,
        "from_id": sender_id,
        "text": text,
        **extra,
    }


def test_multiple_exports_flow_from_json_to_report_bundle(tmp_path):
    later = tmp_path / "1.json"
    earlier = tmp_path / "2.json"
    write_export(
        earlier,
        [
            row(1, 1767225600, "account-a", "Example A", "Hello"),
            row(2, 1767225660, "peer", "Example B", "سلام 👋"),
            {"id": 3, "type": "service", "date": "2026-01-01T00:02:00", "date_unixtime": "1767225720", "action": "phone_call"},
        ],
    )
    write_export(
        later,
        [
            row(4, 1767312000, "account-b", "Example A", "How are you?"),
            row(5, 1767312060, "peer", "Example B", "", photo="(File not included.)"),
        ],
    )

    exports = load_exports([later, earlier])
    messages, duplicates = merge_messages(exports)
    first, second, excluded = suggest_sides(exports)
    result = analyze_chat(
        messages,
        [first, second],
        AnalysisOptions(
            timezone="Asia/Tehran",
            service_count=sum(export.service_count for export in exports),
            files=[{"name": export.path.name} for export in exports],
        ),
    )
    output = generate_bundle(result, tmp_path / "reports")

    assert [export.path.name for export in exports] == ["2.json", "1.json"]
    assert duplicates == 0
    assert excluded == set()
    assert result["summary"]["message_count"] == 4
    assert result["summary"]["service_count"] == 1
    assert (output / "report.md").exists()
    assert (output / "csv" / "responses.csv").exists()
