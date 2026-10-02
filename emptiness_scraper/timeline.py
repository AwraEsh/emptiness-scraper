from __future__ import annotations

from datetime import timedelta
from typing import Iterable

from .models import CensoredInterval, Message, Response, Session, Turn


def _crosses_interval(start, end, interval: CensoredInterval) -> bool:
    return start <= interval.end and end >= interval.start


def build_sessions(
    messages: Iterable[Message],
    gap: timedelta,
    censored: list[CensoredInterval] | None = None,
) -> list[Session]:
    ordered = sorted(messages, key=lambda item: (item.timestamp, str(item.message_id)))
    if not ordered:
        return []
    groups: list[list[Message]] = [[ordered[0]]]
    for current in ordered[1:]:
        previous = groups[-1][-1]
        if current.timestamp - previous.timestamp >= gap:
            groups.append([])
        groups[-1].append(current)
    intervals = censored or []
    sessions: list[Session] = []
    for index, group in enumerate(groups, start=1):
        affected = any(_crosses_interval(group[0].timestamp, group[-1].timestamp, interval) for interval in intervals)
        sessions.append(Session(index=index, messages=group, censored=affected))
    return sessions


def build_turns(sessions: Iterable[Session]) -> list[Turn]:
    turns: list[Turn] = []
    for session in sessions:
        current: list[Message] = []
        for message in session.messages:
            if current and current[-1].sender_id != message.sender_id:
                turns.append(_make_turn(session.index, current))
                current = []
            current.append(message)
        if current:
            turns.append(_make_turn(session.index, current))
    return turns


def _make_turn(session_index: int, messages: list[Message]) -> Turn:
    return Turn(
        session_index=session_index,
        sender_id=messages[0].sender_id,
        sender_name=messages[0].sender_name,
        start=messages[0].timestamp,
        end=messages[-1].timestamp,
        message_count=len(messages),
        characters=sum(len(item.text) for item in messages),
        message_ids=[item.message_id for item in messages],
    )


def build_responses(
    sessions: Iterable[Session],
    censored: list[CensoredInterval],
) -> list[Response]:
    responses: list[Response] = []
    for session in sessions:
        previous = session.messages[0] if session.messages else None
        for current in session.messages[1:]:
            if previous and current.sender_id != previous.sender_id:
                safe = not session.censored and not any(
                    _crosses_interval(previous.timestamp, current.timestamp, interval) for interval in censored
                )
                responses.append(
                    Response(
                        session_index=session.index,
                        responder_id=current.sender_id,
                        responder_name=current.sender_name,
                        previous_sender_id=previous.sender_id,
                        sent_at=current.timestamp,
                        previous_at=previous.timestamp,
                        latency_seconds=(current.timestamp - previous.timestamp).total_seconds(),
                        comparison_safe=safe,
                    )
                )
            previous = current
    return responses

