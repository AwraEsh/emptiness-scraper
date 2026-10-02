from __future__ import annotations

from collections import Counter
from dataclasses import dataclass

from .models import ExportFile, Message


@dataclass(slots=True)
class Side:
    label: str
    ids: set[str]


def sender_counts(messages: list[Message]) -> Counter[str]:
    return Counter(message.sender_id for message in messages)


def sender_names(messages: list[Message]) -> dict[str, str]:
    names: dict[str, str] = {}
    for message in messages:
        names[message.sender_id] = message.sender_name
    return names


def suggest_sides(exports: list[ExportFile]) -> tuple[Side, Side, set[str]]:
    all_messages = [message for export in exports for message in export.messages]
    counts = sender_counts(all_messages)
    names = sender_names(all_messages)
    meaningful = {sender for sender, count in counts.items() if count > 0 and sender != "unknown"}
    if len(meaningful) < 2:
        raise ValueError("At least two message senders are required.")

    present_sets = []
    for export in exports:
        ranked = sender_counts(export.messages).most_common(2)
        present_sets.append({sender for sender, _ in ranked if sender != "unknown"})
    stable = set.intersection(*present_sets) if present_sets else set()
    if len(exports) > 1 and len(stable) == 1:
        stable_id = next(iter(stable))
        primary_ids = set().union(*present_sets)
        other_ids = primary_ids - {stable_id}
        left = Side(names.get(next(iter(other_ids)), "Participant A"), other_ids)
        right = Side(names.get(stable_id, "Participant B"), {stable_id})
        return left, right, meaningful - primary_ids

    ranked = [sender for sender, _ in counts.most_common() if sender in meaningful]
    first, second = ranked[:2]
    excluded = meaningful - {first, second}
    return Side(names.get(first, "Participant A"), {first}), Side(names.get(second, "Participant B"), {second}), excluded


def map_sides(messages: list[Message], sides: list[Side]) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for side in sides:
        for sender_id in side.ids:
            if sender_id in mapping:
                raise ValueError(f"Sender {sender_id} was assigned to more than one participant.")
            mapping[sender_id] = side.label
    return mapping
