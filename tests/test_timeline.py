from datetime import UTC, datetime, timedelta

from emptiness_scraper.models import CensoredInterval, Message
from emptiness_scraper.timeline import build_responses, build_sessions, build_turns


def item(minutes, sender, message_id, reply_to=None):
    return Message(
        source="fixture.json",
        message_id=message_id,
        timestamp=datetime(2026, 1, 1, tzinfo=UTC) + timedelta(minutes=minutes),
        sender_id=sender,
        sender_name=sender.upper(),
        text=f"message {message_id}",
        reply_to_message_id=reply_to,
    )


def test_session_boundary_is_inclusive():
    messages = [item(0, "a", 1), item(359, "b", 2), item(719, "a", 3)]

    sessions = build_sessions(messages, gap=timedelta(hours=6))

    assert len(sessions) == 2
    assert [len(session.messages) for session in sessions] == [2, 1]


def test_turns_group_consecutive_messages():
    session = build_sessions(
        [item(0, "a", 1), item(1, "a", 2), item(2, "b", 3)],
        gap=timedelta(hours=6),
    )[0]

    turns = build_turns([session])

    assert [(turn.sender_id, turn.message_count) for turn in turns] == [("a", 2), ("b", 1)]


def test_response_latency_uses_last_message_before_switch():
    session = build_sessions(
        [item(0, "a", 1), item(2, "a", 2), item(5, "b", 3)],
        gap=timedelta(hours=6),
    )[0]

    response = build_responses([session], censored=[])[0]

    assert response.responder_id == "b"
    assert response.latency_seconds == 180
    assert response.comparison_safe is True


def test_response_crossing_censored_interval_is_not_comparison_safe():
    session = build_sessions([item(0, "a", 1), item(5, "b", 2)], gap=timedelta(hours=6))[0]
    interval = CensoredInterval(
        start=datetime(2026, 1, 1, 0, 2, tzinfo=UTC),
        end=datetime(2026, 1, 1, 0, 4, tzinfo=UTC),
        label="missing channel",
    )

    response = build_responses([session], censored=[interval])[0]

    assert response.comparison_safe is False

