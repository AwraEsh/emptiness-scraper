from __future__ import annotations

import math
import statistics
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from .identity import Side, map_sides
from .models import CensoredInterval, Message
from .signals import detect_session_signals
from .textstats import extract_emojis, normalize_text, raw_tokens, tokenize
from .timeline import build_responses, build_sessions, build_turns


@dataclass(slots=True)
class AnalysisOptions:
    session_gap_hours: float = 6
    timezone: str = "Asia/Tehran"
    censored_intervals: list[CensoredInterval] = field(default_factory=list)
    stopwords: set[str] = field(default_factory=set)
    service_count: int = 0
    files: list[dict[str, Any]] = field(default_factory=list)
    rules: dict[str, list[str]] | None = None


def _percentile(values: list[float], probability: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return float(ordered[lower])
    return ordered[lower] + (ordered[upper] - ordered[lower]) * (position - lower)


def _statistics(values: list[float]) -> dict[str, float | int]:
    if not values:
        return {"count": 0, "mean_seconds": 0, "median_seconds": 0, "trimmed_mean_seconds": 0, "min_seconds": 0, "max_seconds": 0, "p75_seconds": 0, "p90_seconds": 0, "p95_seconds": 0}
    ordered = sorted(values)
    trim = int(len(ordered) * 0.1)
    trimmed = ordered[trim : len(ordered) - trim] if trim and len(ordered) > trim * 2 else ordered
    return {
        "count": len(values),
        "mean_seconds": statistics.mean(values),
        "median_seconds": statistics.median(values),
        "trimmed_mean_seconds": statistics.mean(trimmed),
        "min_seconds": min(values),
        "max_seconds": max(values),
        "p75_seconds": _percentile(values, 0.75),
        "p90_seconds": _percentile(values, 0.90),
        "p95_seconds": _percentile(values, 0.95),
    }


def _timezone(value: str):
    if value.upper() == "UTC":
        return UTC
    if value.startswith(("+", "-")) and len(value) == 6:
        sign = 1 if value[0] == "+" else -1
        hours, minutes = map(int, value[1:].split(":"))
        return __import__("datetime").timezone(sign * timedelta(hours=hours, minutes=minutes))
    return ZoneInfo(value)


def analyze_chat(messages: list[Message], sides: list[Side], options: AnalysisOptions) -> dict[str, Any]:
    side_map = map_sides(messages, sides)
    retained = [message for message in messages if message.sender_id in side_map]
    retained.sort(key=lambda item: (item.timestamp, str(item.message_id)))
    if not retained:
        raise ValueError("No messages remain after participant selection.")
    zone = _timezone(options.timezone)
    gap = timedelta(hours=options.session_gap_hours)
    sessions = build_sessions(retained, gap, options.censored_intervals)
    turns = build_turns(sessions)
    responses = build_responses(sessions, options.censored_intervals)

    participants: dict[str, dict[str, Any]] = {}
    for side in sides:
        own_messages = [message for message in retained if side_map[message.sender_id] == side.label]
        own_turns = [turn for turn in turns if side_map[turn.sender_id] == side.label]
        words = [word for message in own_messages for word in tokenize(message.text)]
        participants[side.label] = {
            "ids": sorted(side.ids),
            "messages": len(own_messages),
            "message_share_percent": round(len(own_messages) * 100 / len(retained), 2),
            "turns": len(own_turns),
            "words": len(words),
            "characters": sum(len(message.text) for message in own_messages),
            "questions": sum(("?" in message.text or "؟" in message.text) for message in own_messages),
            "media": sum(bool(message.media_type) for message in own_messages),
            "reactions": sum(message.reactions for message in own_messages),
            "multi_message_turns": sum(turn.message_count > 1 for turn in own_turns),
            "median_turn_messages": statistics.median([turn.message_count for turn in own_turns]) if own_turns else 0,
            "longest_turn_messages": max((turn.message_count for turn in own_turns), default=0),
        }

    serialized_sessions: list[dict[str, Any]] = []
    serialized_gaps: list[dict[str, Any]] = []
    for index, session in enumerate(sessions):
        session_turns = [turn for turn in turns if turn.session_index == session.index]
        starter = session.messages[0]
        final = session.messages[-1]
        restart_type = "first_session"
        if index:
            prior = sessions[index - 1].messages[-1]
            restart_type = "same_sender_restart" if prior.sender_id == starter.sender_id else "other_sender_return"
            gap_safe = not any(prior.timestamp <= interval.end and starter.timestamp >= interval.start for interval in options.censored_intervals)
            serialized_gaps.append(
                {
                    "from": prior.timestamp.isoformat(),
                    "to": starter.timestamp.isoformat(),
                    "seconds": (starter.timestamp - prior.timestamp).total_seconds(),
                    "previous_sender": side_map[prior.sender_id],
                    "returning_sender": side_map[starter.sender_id],
                    "same_sender_restart": prior.sender_id == starter.sender_id,
                    "comparison_safe": gap_safe,
                }
            )
        serialized_sessions.append(
            {
                "index": session.index,
                "start": session.start.isoformat(),
                "end": session.end.isoformat(),
                "duration_seconds": (session.end - session.start).total_seconds(),
                "message_count": len(session.messages),
                "turn_count": len(session_turns),
                "initiator": side_map[starter.sender_id],
                "final_sender": side_map[final.sender_id],
                "one_sided": len({message.sender_id for message in session.messages}) == 1,
                "censored": session.censored,
                "restart_type": restart_type,
            }
        )

    serialized_turns = [
        {
            "session_index": turn.session_index,
            "participant": side_map[turn.sender_id],
            "start": turn.start.isoformat(),
            "end": turn.end.isoformat(),
            "message_count": turn.message_count,
            "characters": turn.characters,
        }
        for turn in turns
    ]
    serialized_responses = [
        {
            "session_index": response.session_index,
            "responder": side_map[response.responder_id],
            "previous_sender": side_map[response.previous_sender_id],
            "sent_at": response.sent_at.isoformat(),
            "previous_at": response.previous_at.isoformat(),
            "latency_seconds": response.latency_seconds,
            "comparison_safe": response.comparison_safe,
            "month": response.sent_at.astimezone(zone).strftime("%Y-%m"),
            "weekday": response.sent_at.astimezone(zone).strftime("%A"),
            "hour": response.sent_at.astimezone(zone).hour,
        }
        for response in responses
    ]

    response_statistics = {}
    for side in sides:
        values = [item["latency_seconds"] for item in serialized_responses if item["responder"] == side.label]
        safe_values = [item["latency_seconds"] for item in serialized_responses if item["responder"] == side.label and item["comparison_safe"]]
        response_statistics[side.label] = {"raw": _statistics(values), "comparison_safe": _statistics(safe_values)}

    response_values = [item["latency_seconds"] for item in serialized_responses]
    response_breakdowns = {
        "bands": {
            "under_1_minute": sum(value < 60 for value in response_values),
            "under_5_minutes": sum(value < 300 for value in response_values),
            "under_1_hour": sum(value < 3600 for value in response_values),
            "under_6_hours": sum(value < 21600 for value in response_values),
        },
        "months": dict(Counter(item["month"] for item in serialized_responses)),
        "weekdays": dict(Counter(item["weekday"] for item in serialized_responses)),
        "hours": {str(key): value for key, value in sorted(Counter(item["hour"] for item in serialized_responses).items())},
    }
    response_hour_groups: dict[tuple[str, int], list[float]] = defaultdict(list)
    for item in serialized_responses:
        response_hour_groups[(item["responder"], item["hour"])].append(item["latency_seconds"])
    response_by_participant_hour = [
        {
            "participant": participant,
            "hour": hour,
            "response_count": len(values),
            "median_seconds": statistics.median(values),
            "mean_seconds": statistics.mean(values),
        }
        for (participant, hour), values in sorted(response_hour_groups.items())
    ]

    message_lookup = {(message.source, message.message_id): message for message in retained}
    unique_id_lookup: dict[int | str, Message | None] = {}
    for message in retained:
        if message.message_id in unique_id_lookup:
            unique_id_lookup[message.message_id] = None
        else:
            unique_id_lookup[message.message_id] = message
    explicit_reply_ages = []
    for message in retained:
        if message.reply_to_message_id is None:
            continue
        target = message_lookup.get((message.source, message.reply_to_message_id))
        if target is None:
            target = unique_id_lookup.get(message.reply_to_message_id)
        if target is None or target.timestamp > message.timestamp:
            continue
        explicit_reply_ages.append(
            {
                "source": message.source,
                "message_id": message.message_id,
                "participant": side_map[message.sender_id],
                "timestamp": message.timestamp.isoformat(),
                "target_message_id": target.message_id,
                "target_participant": side_map[target.sender_id],
                "age_seconds": (message.timestamp - target.timestamp).total_seconds(),
            }
        )

    month_messages: dict[str, list[Message]] = defaultdict(list)
    for message in retained:
        month_messages[message.timestamp.astimezone(zone).strftime("%Y-%m")].append(message)
    months = []
    for month, items in sorted(month_messages.items()):
        monthly_sessions = [row for row in serialized_sessions if datetime.fromisoformat(row["start"]).astimezone(zone).strftime("%Y-%m") == month]
        row: dict[str, Any] = {
            "month": month,
            "message_count": len(items),
            "session_count": len(monthly_sessions),
            "active_days": len({message.timestamp.astimezone(zone).date().isoformat() for message in items}),
            "messages_per_active_day": round(len(items) / len({message.timestamp.astimezone(zone).date() for message in items}), 2),
            "median_session_messages": statistics.median([entry["message_count"] for entry in monthly_sessions]) if monthly_sessions else 0,
            "median_session_duration_seconds": statistics.median([entry["duration_seconds"] for entry in monthly_sessions]) if monthly_sessions else 0,
        }
        for side in sides:
            side_messages = sum(side_map[message.sender_id] == side.label for message in items)
            row[f"{side.label}_messages"] = side_messages
            row[f"{side.label}_share_percent"] = round(side_messages * 100 / len(items), 2)
        months.append(row)

    span = max((retained[-1].timestamp - retained[0].timestamp).total_seconds(), 1)
    quarters = []
    for quarter in range(4):
        start = retained[0].timestamp + timedelta(seconds=span * quarter / 4)
        end = retained[0].timestamp + timedelta(seconds=span * (quarter + 1) / 4)
        if quarter == 3:
            selected = [message for message in retained if start <= message.timestamp <= end]
        else:
            selected = [message for message in retained if start <= message.timestamp < end]
        selected_sessions = [entry for entry in serialized_sessions if start <= datetime.fromisoformat(entry["start"]) <= end]
        quarter_row: dict[str, Any] = {
            "quarter": quarter + 1,
            "start": start.isoformat(),
            "end": end.isoformat(),
            "message_count": len(selected),
            "active_days": len({message.timestamp.astimezone(zone).date() for message in selected}),
            "session_count": len(selected_sessions),
            "median_session_messages": statistics.median([entry["message_count"] for entry in selected_sessions]) if selected_sessions else 0,
            "median_session_duration_seconds": statistics.median([entry["duration_seconds"] for entry in selected_sessions]) if selected_sessions else 0,
        }
        for side in sides:
            side_messages = sum(side_map[message.sender_id] == side.label for message in selected)
            quarter_row[f"{side.label}_messages"] = side_messages
            quarter_row[f"{side.label}_share_percent"] = round(side_messages * 100 / len(selected), 2) if selected else 0
        quarters.append(quarter_row)

    all_tokens = [word for message in retained for word in tokenize(message.text)]
    all_raw_tokens = [word for message in retained for word in raw_tokens(message.text)]
    filtered_tokens = [word for word in all_tokens if word not in {normalize_text(word) for word in options.stopwords}]
    normalized_word_samples: dict[str, list[str]] = defaultdict(list)
    for raw_word in all_raw_tokens:
        normalized_word = normalize_text(raw_word)
        if raw_word not in normalized_word_samples[normalized_word]:
            normalized_word_samples[normalized_word].append(raw_word)
    ngrams = Counter()
    for message in retained:
        tokens = [word for word in tokenize(message.text) if word not in options.stopwords]
        for size in (2, 3, 4, 5):
            ngrams.update(" ".join(tokens[index : index + size]) for index in range(len(tokens) - size + 1))
    emoji_counts = Counter(emoji for message in retained for emoji in extract_emojis(message.text))
    repeated_messages = Counter(normalize_text(message.text) for message in retained if normalize_text(message.text))
    sentence_counts = Counter()
    for message in retained:
        for sentence in __import__("re").split(r"[.!?؟\n]+", message.text):
            normalized_sentence = normalize_text(sentence)
            if normalized_sentence:
                sentence_counts[normalized_sentence] += 1
    text = {
        "words": [list(item) for item in Counter(filtered_tokens).most_common()],
        "raw_words": [list(item) for item in Counter(all_raw_tokens).most_common()],
        "normalized_word_samples": dict(normalized_word_samples),
        "emojis": [list(item) for item in emoji_counts.most_common()],
        "phrases": [list(item) for item in ngrams.most_common()],
        "repeated_messages": [[value, count] for value, count in repeated_messages.most_common() if count > 1],
        "repeated_sentences": [[value, count] for value, count in sentence_counts.most_common() if count > 1],
        "hashtags": [list(item) for item in Counter(match for message in retained for match in __import__("re").findall(r"#[\w\u0600-\u06ff]+", message.text)).most_common()],
        "mentions": [list(item) for item in Counter(match for message in retained for match in __import__("re").findall(r"@[A-Za-z0-9_]+", message.text)).most_common()],
        "urls": sum(bool(__import__("re").search(r"https?://|www\.", message.text)) for message in retained),
    }
    normalized_stopwords = {normalize_text(word) for word in options.stopwords}
    participant_text: dict[str, dict[str, list[list[Any]]]] = {}
    participant_word_rows: list[dict[str, Any]] = []
    participant_emoji_rows: list[dict[str, Any]] = []
    activity_groups: Counter[tuple[str, int]] = Counter()
    for message in retained:
        activity_groups[(side_map[message.sender_id], message.timestamp.astimezone(zone).hour)] += 1
    participant_activity_hours = [
        {"participant": participant, "hour": hour, "message_count": count}
        for (participant, hour), count in sorted(activity_groups.items())
    ]
    for side in sides:
        own_messages = [message for message in retained if side_map[message.sender_id] == side.label]
        own_words = Counter(word for message in own_messages for word in tokenize(message.text) if word not in normalized_stopwords)
        own_emojis = Counter(emoji for message in own_messages for emoji in extract_emojis(message.text))
        participant_text[side.label] = {
            "words": [list(item) for item in own_words.most_common()],
            "emojis": [list(item) for item in own_emojis.most_common()],
        }
        participant_word_rows.extend({"participant": side.label, "word": word, "count": count} for word, count in own_words.most_common())
        participant_emoji_rows.extend({"participant": side.label, "emoji": emoji, "count": count} for emoji, count in own_emojis.most_common())

    audit_files = options.files or [{"name": source} for source in sorted({message.source for message in retained})]
    exports = []
    for source in sorted({message.source for message in retained}):
        source_messages = [message for message in retained if message.source == source]
        exports.append(
            {
                "source": source,
                "message_count": len(source_messages),
                "start": source_messages[0].timestamp.isoformat(),
                "end": source_messages[-1].timestamp.isoformat(),
                "active_days": len({message.timestamp.astimezone(zone).date() for message in source_messages}),
            }
        )
    return {
        "schema_version": "1.0",
        "generated_at": datetime.now(UTC).isoformat(),
        "configuration": {
            "timezone": options.timezone,
            "session_gap_hours": options.session_gap_hours,
            "censored_intervals": [{"start": interval.start.isoformat(), "end": interval.end.isoformat(), "label": interval.label} for interval in options.censored_intervals],
        },
        "summary": {
            "message_count": len(retained),
            "start": retained[0].timestamp.isoformat(),
            "end": retained[-1].timestamp.isoformat(),
            "active_days": len({message.timestamp.astimezone(zone).date() for message in retained}),
            "service_count": options.service_count,
            "file_count": len(audit_files),
            "readable_text_messages": sum(bool(message.text.strip()) for message in retained),
            "media_messages": sum(bool(message.media_type) for message in retained),
            "edited_messages": sum(message.edited for message in retained),
            "forwarded_messages": sum(message.forwarded for message in retained),
            "reply_messages": sum(message.reply_to_message_id is not None for message in retained),
        },
        "participants": participants,
        "session_sensitivity": {str(hours): len(build_sessions(retained, timedelta(hours=hours))) for hours in (4, 6, 12)},
        "sessions": serialized_sessions,
        "turns": serialized_turns,
        "responses": serialized_responses,
        "gaps": serialized_gaps,
        "months": months,
        "quarters": quarters,
        "response_statistics": response_statistics,
        "response_breakdowns": response_breakdowns,
        "response_by_participant_hour": response_by_participant_hour,
        "explicit_reply_ages": explicit_reply_ages,
        "exports": exports,
        "text": text,
        "participant_text": participant_text,
        "participant_words": participant_word_rows,
        "participant_emojis": participant_emoji_rows,
        "participant_activity_hours": participant_activity_hours,
        "signals": detect_session_signals(sessions, side_map, options.rules),
        "audit": {"files": audit_files, "warnings": []},
        "definitions": {
            "session": f"Separated by at least {options.session_gap_hours:g} hours of inactivity.",
            "turn": "Consecutive messages by one participant until the other participant sends a message.",
            "response": "First message after the sender changes within one session.",
            "heuristics": "Rule matches are descriptive labels, not evidence of intent, emotion, or relationship meaning.",
        },
    }
