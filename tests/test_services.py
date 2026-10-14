from datetime import UTC, datetime

import pytest

from emptiness_scraper.services import parse_intervals, parse_path_input, read_report_page


def test_multiline_paths_preserve_quoted_semicolons():
    assert parse_path_input('"/tmp/one;chat.json"\n"/tmp/two chat.json"') == ["/tmp/one;chat.json", "/tmp/two chat.json"]


def test_report_pages_have_no_overlapping_lines(tmp_path):
    path = tmp_path / "report.md"
    path.write_text("\n".join(f"line {index}" for index in range(161)), encoding="utf-8")
    first = read_report_page(path)
    second = read_report_page(path, page=1)
    assert first.text.splitlines()[-1] == "line 159"
    assert first.has_next
    assert second.text == "line 160"
    assert not second.has_next


def test_incomplete_intervals_use_selected_timezone():
    interval = parse_intervals("2026-01-01 03:30 | 2026-01-01 04:30 | external channel", "Asia/Tehran")[0]
    assert interval.start == datetime(2026, 1, 1, tzinfo=UTC)
    assert interval.label == "external channel"


def test_invalid_interval_stays_a_validation_error():
    with pytest.raises(ValueError, match="end must follow"):
        parse_intervals("2026-01-02 | 2026-01-01", "UTC")


def test_markdown_table_headers_are_repeated_on_continuation_pages(tmp_path):
    path = tmp_path / "table.md"
    path.write_text("| Name | Count |\n| --- | --- |\n" + "\n".join(f"| row {index} | {index} |" for index in range(170)), encoding="utf-8")
    second = read_report_page(path, page=1)
    assert second.text.startswith("| Name | Count |\n| --- | --- |\n| row 158 |")
