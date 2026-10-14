import json
from datetime import UTC, datetime, timedelta

import pytest

from emptiness_scraper.analysis import AnalysisOptions, analyze_chat
from emptiness_scraper.calendar_utils import resolve_timezone
from emptiness_scraper.identity import Side
from emptiness_scraper.models import Message
from emptiness_scraper.models import CensoredInterval
from emptiness_scraper.parser import ExportValidationError, load_exports, merge_messages
from emptiness_scraper.settings import load_settings
from emptiness_scraper.signals import detect_text_signals
from emptiness_scraper.textstats import extract_emojis


def msg(hour, sender, number, text="hello"):
    return Message("fixture.json", number, datetime(2026, 1, 1, tzinfo=UTC) + timedelta(hours=hour), sender, sender, text)


def analyze(messages, **options):
    return analyze_chat(messages, [Side("Alpha", {"a", "a2"}), Side("Beta", {"b"})], AnalysisOptions(timezone="UTC", **options))


def test_account_alias_change_does_not_create_response_or_turn():
    result = analyze([msg(0, "a", 1), msg(1, "a2", 2), msg(2, "b", 3)])
    assert len(result["turns"]) == 2
    assert len(result["responses"]) == 1
    assert result["responses"][0]["latency_seconds"] == 3600
    assert any(event["category"] == "follow_up" for event in result["signals"])


def test_same_second_message_ids_are_ordered_numerically():
    result = analyze([msg(0, "b", 10), msg(0, "a", 2)])
    assert result["sessions"][0]["initiator"] == "Alpha"


def test_quarter_session_boundaries_are_not_counted_twice():
    result = analyze([msg(0, "a", 1), msg(24, "b", 2), msg(96, "a", 3)])
    assert sum(row["session_count"] for row in result["quarters"]) == 3


def test_inactive_calendar_month_is_preserved():
    result = analyze([msg(0, "a", 1), msg(24 * 70, "b", 2)])
    assert [row["month"] for row in result["months"]] == ["2026-01", "2026-02", "2026-03"]
    assert result["months"][1]["message_count"] == 0


@pytest.mark.parametrize("value", [0, -1, float("nan"), float("inf")])
def test_invalid_session_threshold_is_rejected(value):
    with pytest.raises(ValueError, match="finite|positive"):
        analyze([msg(0, "a", 1), msg(1, "b", 2)], session_gap_hours=value)


def test_disabled_text_rules_stay_disabled():
    assert detect_text_signals(msg(0, "a", 1, "hello"), {}) == []


def test_flag_and_keycap_emoji_count_as_whole_sequences():
    assert extract_emojis("🇮🇷 1️⃣ 👩🏽‍💻 ❤️") == ["🇮🇷", "1️⃣", "👩🏽‍💻", "❤️"]


@pytest.mark.parametrize("offset", ["+03:99", "+24:00", "-01:80"])
def test_invalid_timezone_offsets_are_rejected(offset):
    with pytest.raises(ValueError):
        resolve_timezone(offset)


@pytest.mark.parametrize("content", [[], {"rules": []}, {"session_gap_hours": -1}, {"timezone": "No/SuchZone"}])
def test_corrupt_settings_fall_back_to_valid_defaults(tmp_path, content):
    path = tmp_path / "settings.json"
    path.write_text(json.dumps(content), encoding="utf-8")
    settings = load_settings(path)
    assert settings.session_gap_hours == 6
    assert settings.timezone == "Asia/Tehran"


def test_duplicate_basenames_keep_distinct_reply_namespaces(tmp_path):
    paths = []
    for folder in ("first", "second"):
        directory = tmp_path / folder
        directory.mkdir()
        path = directory / "result.json"
        path.write_text(json.dumps({"type": "personal_chat", "messages": [{"type": "message", "id": 1, "date_unixtime": "1767225600", "from_id": "a", "text": "hi"}]}), encoding="utf-8")
        paths.append(path)
    exports = load_exports(paths)
    assert exports[0].messages[0].source != exports[1].messages[0].source


def test_missing_epoch_uses_selected_timezone(tmp_path):
    path = tmp_path / "chat.json"
    path.write_text(json.dumps({"type": "personal_chat", "messages": [{"type": "message", "id": 1, "date": "2026-01-01T03:30:00", "from_id": "a", "text": "hi"}]}), encoding="utf-8")
    exports = load_exports([path], timezone_name="Asia/Tehran")
    assert exports[0].messages[0].timestamp == datetime(2026, 1, 1, tzinfo=UTC)


def test_malformed_message_is_not_silently_discarded(tmp_path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"type": "personal_chat", "messages": [42]}), encoding="utf-8")
    with pytest.raises(ExportValidationError):
        load_exports([path])


def test_reply_id_from_another_export_is_not_guessed():
    first = msg(0, "a", 1)
    second = msg(1, "b", 2)
    second.source = "another-account.json"
    second.reply_to_message_id = 1
    result = analyze([first, second])
    assert result["explicit_reply_ages"] == []
    assert result["summary"]["unresolved_replies"] == 1


def test_restart_rate_has_opportunity_denominator_and_censoring():
    result = analyze([msg(0, "a", 1), msg(8, "a2", 2), msg(16, "b", 3)])
    assert result["restart_statistics"]["Alpha"]["eligible_transitions"] == 2
    assert result["restart_statistics"]["Alpha"]["same_sender_restarts"] == 1
    assert result["restart_statistics"]["Alpha"]["rate_percent"] == 50


def test_monthly_comparison_safe_metrics_exclude_affected_sessions():
    interval = CensoredInterval(datetime(2026, 1, 1, 1, tzinfo=UTC), datetime(2026, 1, 1, 2, tzinfo=UTC))
    result = analyze([msg(0, "a", 1), msg(3, "b", 2), msg(10, "a", 3)], censored_intervals=[interval])
    assert result["months"][0]["comparison_safe_messages"] == 1
    assert result["months"][0]["comparison_safe_sessions"] == 1


def test_phrase_counts_do_not_bridge_stopwords_or_sentence_boundaries():
    result = analyze([msg(0, "a", 1, "red and blue. next sentence"), msg(1, "b", 2)], stopwords={"and"})
    phrases = dict(result["text"]["phrases"])
    assert "red blue" not in phrases
    assert "blue next" not in phrases


def test_distinct_media_in_same_second_are_not_deduplicated(tmp_path):
    paths = []
    for index in (1, 2):
        path = tmp_path / f"{index}.json"
        path.write_text(json.dumps({"type": "personal_chat", "messages": [{"type": "message", "id": index, "date_unixtime": "1767225600", "from_id": "a", "text": "", "photo": f"photo{index}.jpg"}]}), encoding="utf-8")
        paths.append(path)
    merged, duplicates = merge_messages(load_exports(paths))
    assert len(merged) == 2
    assert duplicates == 0
