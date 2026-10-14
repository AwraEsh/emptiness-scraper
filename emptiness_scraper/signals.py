from __future__ import annotations

import re

from .models import Message, Session
from .textstats import normalize_text


DEFAULT_RULES = {
    "greeting": [r"\bhello\b", r"\bhi\b", r"\bgood morning\b", r"سلام", r"صبح بخیر"],
    "goodbye": [r"\bbye\b", r"\bgood night\b", r"خداحافظ", r"شب بخیر"],
    "check_in": [r"how are you", r"what'?s up", r"حالت چطوره", r"خوبی", r"چه خبر", r"زنده.?ای"],
}


def detect_text_signals(message: Message, rules: dict[str, list[str]] | None = None) -> list[dict]:
    normalized = normalize_text(message.text)
    events: list[dict] = []
    for category, patterns in (DEFAULT_RULES if rules is None else rules).items():
        try:
            matched = next((pattern for pattern in patterns if re.search(pattern, normalized, re.IGNORECASE)), None)
        except re.error as error:
            raise ValueError(f"Invalid pattern in {category}: {error}") from error
        if matched is not None:
            events.append(_event(category, message, f"Matched text pattern: {matched}"))
    if "?" in message.text or "؟" in message.text:
        events.append(_event("question", message, "Message contains a question mark."))
    return events


def detect_session_signals(
    sessions: list[Session],
    side_map: dict[str, str],
    rules: dict[str, list[str]] | None = None,
) -> list[dict]:
    events: list[dict] = []
    for index, session in enumerate(sessions):
        for message in session.messages:
            events.extend(detect_text_signals(message, rules))
        for previous, current in zip(session.messages, session.messages[1:]):
            if previous.sender_id == current.sender_id:
                events.append(
                    _event(
                        "follow_up",
                        current,
                        "Same participant sent another message before the other participant replied.",
                    )
                )
        if index > 0:
            previous_session = sessions[index - 1]
            starter = session.messages[0]
            prior_final = previous_session.messages[-1]
            if starter.sender_id == prior_final.sender_id:
                events.append(_event("session_revival", starter, "Same participant returned after the session gap."))
            if starter.media_type:
                events.append(_event("content_after_silence", starter, "Session starts with shared media or a file."))
            if starter.reply_to_message_id is not None:
                events.append(_event("possible_callback", starter, "Session starts with an explicit reply to an earlier message."))
    for event in events:
        event["participant"] = side_map.get(event.pop("sender_id"), "Excluded sender")
    return events


def _event(category: str, message: Message, rule: str) -> dict:
    excerpt = " ".join(message.text.split())[:160]
    return {
        "category": category,
        "sender_id": message.sender_id,
        "timestamp": message.timestamp.isoformat(),
        "source": message.source,
        "message_id": message.message_id,
        "excerpt": excerpt,
        "rule": rule,
    }
