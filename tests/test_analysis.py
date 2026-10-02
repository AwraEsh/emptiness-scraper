import json
from datetime import UTC, datetime, timedelta

from emptiness_scraper.analysis import AnalysisOptions, analyze_chat
from emptiness_scraper.identity import Side, suggest_sides
from emptiness_scraper.models import ExportFile, Message


def item(day, minute, sender, name, message_id, text="hello", **extra):
    return Message(
        source=extra.pop("source", "fixture.json"),
        message_id=message_id,
        timestamp=datetime(2026, 1, day, tzinfo=UTC) + timedelta(minutes=minute),
        sender_id=sender,
        sender_name=name,
        text=text,
        **extra,
    )


def export(name, messages):
    return ExportFile(
        path=__import__("pathlib").Path(name),
        chat_name="Synthetic Chat",
        chat_type="personal_chat",
        messages=messages,
        service_count=0,
        first_timestamp=messages[0].timestamp,
        last_timestamp=messages[-1].timestamp,
    )


def test_suggest_sides_groups_changed_account_against_stable_participant():
    first = export("one.json", [item(1, 0, "self-1", "Person One", 1), item(1, 1, "peer", "Person Two", 2)])
    second = export("two.json", [item(2, 0, "self-2", "Person One", 3), item(2, 1, "peer", "Person Two", 4)])

    left, right, excluded = suggest_sides([first, second])

    assert {frozenset(left.ids), frozenset(right.ids)} == {
        frozenset({"self-1", "self-2"}),
        frozenset({"peer"}),
    }
    assert excluded == set()


def test_suggest_sides_excludes_low_volume_additional_sender():
    first_messages = [item(1, index, "self-1", "Person One", index) for index in range(5)]
    first_messages += [item(1, index + 10, "peer", "Person Two", index + 20) for index in range(5)]
    first_messages += [item(1, 30, "assistant", "Helper", 99)]
    second_messages = [item(2, index, "self-2", "Person One", index + 100) for index in range(5)]
    second_messages += [item(2, index + 10, "peer", "Person Two", index + 120) for index in range(5)]

    left, right, excluded = suggest_sides([export("one.json", first_messages), export("two.json", second_messages)])

    assert {frozenset(left.ids), frozenset(right.ids)} == {
        frozenset({"self-1", "self-2"}),
        frozenset({"peer"}),
    }
    assert excluded == {"assistant"}


def test_analysis_produces_consistent_participation_and_sessions():
    messages = [
        item(1, 0, "a", "Alpha", 1, "Hello دنیا 👋"),
        item(1, 2, "a", "Alpha", 2, "How are you?"),
        item(1, 5, "b", "Beta", 3, "خوبم ❤️", reactions=2),
        item(2, 0, "b", "Beta", 4, "صبح بخیر"),
    ]
    result = analyze_chat(
        messages,
        [Side("Alpha", {"a"}), Side("Beta", {"b"})],
        AnalysisOptions(session_gap_hours=6, timezone="UTC"),
    )

    assert result["summary"]["message_count"] == 4
    assert result["participants"]["Alpha"]["messages"] == 2
    assert result["participants"]["Beta"]["reactions"] == 2
    assert len(result["sessions"]) == 2
    assert len(result["responses"]) == 1
    assert result["session_sensitivity"] == {"4": 2, "6": 2, "12": 2}
    assert result["months"][0]["message_count"] == 4
    assert result["months"][0]["median_session_messages"] == 2
    assert "Alpha_share_percent" in result["months"][0]
    assert "session_count" in result["quarters"][0]
    assert result["text"]["emojis"][0][0] in {"👋", "❤️"}
    assert result["participant_text"]["Alpha"]["words"][0][0] in {"hello", "دنیا", "how", "are", "you"}
    assert any(row["participant"] == "Beta" for row in result["participant_activity_hours"])


def test_analysis_result_is_json_serializable():
    messages = [item(1, 0, "a", "Alpha", 1), item(1, 1, "b", "Beta", 2)]
    result = analyze_chat(
        messages,
        [Side("Alpha", {"a"}), Side("Beta", {"b"})],
        AnalysisOptions(timezone="Asia/Tehran"),
    )

    json.dumps(result, ensure_ascii=False)


def test_explicit_reply_age_and_response_breakdowns_are_reported():
    messages = [
        item(1, 0, "a", "Alpha", 1, "older"),
        item(1, 2, "b", "Beta", 2, "quick"),
        item(1, 12, "a", "Alpha", 3, "reply", reply_to_message_id=1),
    ]
    result = analyze_chat(
        messages,
        [Side("Alpha", {"a"}), Side("Beta", {"b"})],
        AnalysisOptions(timezone="UTC"),
    )

    assert result["explicit_reply_ages"][0]["age_seconds"] == 720
    assert result["response_breakdowns"]["bands"]["under_5_minutes"] == 1
    assert result["response_breakdowns"]["hours"]["0"] == 2
    assert result["response_by_participant_hour"][0]["response_count"] >= 1
    assert result["exports"][0]["source"] == "fixture.json"


def test_repeated_sentences_and_longer_phrases_are_counted():
    messages = [
        item(1, 0, "a", "Alpha", 1, "one two three four. Shared sentence!"),
        item(1, 1, "b", "Beta", 2, "one two three four. Shared sentence!"),
    ]
    result = analyze_chat(
        messages,
        [Side("Alpha", {"a"}), Side("Beta", {"b"})],
        AnalysisOptions(timezone="UTC"),
    )

    assert ["one two three four", 2] in result["text"]["phrases"]
    assert ["shared sentence", 2] in result["text"]["repeated_sentences"]


def test_raw_and_normalized_word_forms_are_both_available():
    messages = [item(1, 0, "a", "Alpha", 1, "Hello hello"), item(1, 1, "b", "Beta", 2, "HELLO")]
    result = analyze_chat(
        messages,
        [Side("Alpha", {"a"}), Side("Beta", {"b"})],
        AnalysisOptions(timezone="UTC"),
    )

    assert ["hello", 3] in result["text"]["words"]
    assert ["Hello", 1] in result["text"]["raw_words"]
    assert set(result["text"]["normalized_word_samples"]["hello"]) == {"Hello", "hello", "HELLO"}
