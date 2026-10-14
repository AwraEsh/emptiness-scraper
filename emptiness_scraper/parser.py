from __future__ import annotations

import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Iterable

from .models import ExportFile, Message, message_order
from .calendar_utils import resolve_timezone


class ExportValidationError(ValueError):
    pass


def flatten_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        parts: list[str] = []
        for item in value:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                parts.append(str(item.get("text", "")))
        return "".join(parts)
    return ""


def discover_json_files(inputs: Iterable[str | Path]) -> list[Path]:
    found: list[Path] = []
    for raw in inputs:
        path = Path(str(raw).strip().strip('"')).expanduser().resolve()
        if path.is_dir():
            found.extend(sorted(path.glob("*.json")))
        elif path.suffix.lower() == ".json" and path.is_file():
            found.append(path)
        else:
            raise ExportValidationError(f"Not a readable JSON export: {path}")
    unique = list(dict.fromkeys(found))
    if not unique:
        raise ExportValidationError("No JSON exports were found.")
    return unique


def _timestamp(item: dict[str, Any], timezone_name: str) -> datetime:
    epoch = item.get("date_unixtime")
    if epoch not in (None, ""):
        try:
            return datetime.fromtimestamp(int(epoch), tz=UTC)
        except (TypeError, ValueError, OSError, OverflowError):
            pass
    value = item.get("date")
    if not isinstance(value, str):
        raise ExportValidationError("A message has no valid timestamp.")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ExportValidationError(f"Invalid message timestamp: {value}") from error
    return parsed.replace(tzinfo=parsed.tzinfo or resolve_timezone(timezone_name)).astimezone(UTC)


def _reaction_count(item: dict[str, Any]) -> int:
    total = 0
    for reaction in item.get("reactions", []) or []:
        try:
            total += int(reaction.get("count", 1))
        except (AttributeError, TypeError, ValueError):
            total += 1
    return total


def _media_type(item: dict[str, Any]) -> str:
    for key in ("media_type", "file", "photo", "sticker_emoji", "mime_type"):
        if item.get(key):
            return str(item.get("media_type") or key)
    return ""


def _load_export(path: Path, timezone_name: str) -> ExportFile:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ExportValidationError(f"Cannot read {path.name}: {error}") from error
    if not isinstance(data, dict) or not isinstance(data.get("messages"), list):
        raise ExportValidationError(f"{path.name} is not a Telegram JSON export.")
    if data.get("type") != "personal_chat":
        raise ExportValidationError(f"{path.name} is not a supported one-to-one private chat export.")

    messages: list[Message] = []
    service_count = 0
    for position, item in enumerate(data["messages"], start=1):
        if not isinstance(item, dict):
            raise ExportValidationError(f"{path.name}: record {position} must be an object.")
        if item.get("type") == "service":
            service_count += 1
            continue
        if item.get("type") not in {"message", "rich_message"}:
            raise ExportValidationError(f"{path.name}: unsupported record type at position {position}.")
        if not isinstance(item.get("id"), (int, str)) or not item.get("from_id"):
            raise ExportValidationError(f"{path.name}: record {position} requires id and from_id.")
        sender_id = str(item.get("from_id") or "unknown")
        sender_name = str(item.get("from") or sender_id)
        text = flatten_text(item.get("text", ""))
        messages.append(
            Message(
                source=path.name,
                message_id=item.get("id", ""),
                timestamp=_timestamp(item, timezone_name),
                sender_id=sender_id,
                sender_name=sender_name,
                text=text,
                reply_to_message_id=item.get("reply_to_message_id"),
                media_type=_media_type(item),
                edited=bool(item.get("edited") or item.get("edited_unixtime")),
                forwarded=bool(item.get("forwarded_from") or item.get("saved_from")),
                reactions=_reaction_count(item),
                raw={key: item[key] for key in ("file", "photo", "sticker_emoji", "mime_type") if key in item},
            )
        )
    messages.sort(key=message_order)
    return ExportFile(
        path=path,
        chat_name=str(data.get("name") or path.stem),
        chat_type=str(data.get("type")),
        messages=messages,
        service_count=service_count,
        first_timestamp=messages[0].timestamp if messages else None,
        last_timestamp=messages[-1].timestamp if messages else None,
    )


def load_exports(paths: Iterable[str | Path], timezone_name: str = "Asia/Tehran") -> list[ExportFile]:
    resolve_timezone(timezone_name)
    exports = [_load_export(path, timezone_name) for path in discover_json_files(paths)]
    far_future = datetime.max.replace(tzinfo=UTC)
    exports.sort(key=lambda item: (item.first_timestamp or far_future, item.path.name))
    counts = Counter(item.path.name for item in exports)
    for index, export in enumerate(exports, start=1):
        if counts[export.path.name] > 1:
            for message in export.messages:
                message.source = f"{index}:{export.path.name}"
    return exports


def merge_messages(exports: Iterable[ExportFile]) -> tuple[list[Message], int]:
    merged: list[Message] = []
    maximum_occurrences: Counter[tuple] = Counter()
    duplicate_count = 0
    for export in exports:
        local_occurrences: Counter[tuple] = Counter()
        for message in export.messages:
            fingerprint = (
                message.message_id,
                message.timestamp,
                message.sender_id,
                message.text,
                message.media_type,
                message.reply_to_message_id,
                json.dumps({key: message.raw.get(key) for key in ("file", "photo", "sticker_emoji", "mime_type")}, sort_keys=True, ensure_ascii=False),
            )
            local_occurrences[fingerprint] += 1
            occurrence = local_occurrences[fingerprint]
            if occurrence <= maximum_occurrences[fingerprint]:
                duplicate_count += 1
                continue
            maximum_occurrences[fingerprint] = occurrence
            merged.append(message)
    merged.sort(key=message_order)
    return merged, duplicate_count
