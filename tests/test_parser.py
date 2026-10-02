import json

import pytest

from emptiness_scraper.models import Message
from emptiness_scraper.parser import ExportValidationError, flatten_text, load_exports, merge_messages


def write_export(path, name, messages, chat_type="personal_chat"):
    path.write_text(
        json.dumps({"name": name, "type": chat_type, "id": 1, "messages": messages}),
        encoding="utf-8",
    )


def message(message_id, timestamp, sender, sender_id, text):
    return {
        "id": message_id,
        "type": "message",
        "date": timestamp,
        "date_unixtime": str(int(timestamp.replace("-", "").replace(":", "").replace("T", "")[:10])),
        "from": sender,
        "from_id": sender_id,
        "text": text,
    }


def test_flatten_text_supports_entity_arrays():
    value = ["hello ", {"type": "bold", "text": "دنیا"}, "!"]
    assert flatten_text(value) == "hello دنیا!"


def test_exports_are_sorted_by_internal_timestamp(tmp_path):
    later = tmp_path / "1.json"
    earlier = tmp_path / "99.json"
    write_export(later, "Chat", [message(2, "2026-02-02T10:00:00", "B", "b", "later")])
    write_export(earlier, "Chat", [message(1, "2026-01-01T10:00:00", "A", "a", "earlier")])

    exports = load_exports([later, earlier])

    assert [item.path.name for item in exports] == ["99.json", "1.json"]


def test_group_exports_are_rejected(tmp_path):
    path = tmp_path / "group.json"
    write_export(path, "Group", [], chat_type="private_group")

    with pytest.raises(ExportValidationError, match="one-to-one"):
        load_exports([path])


def test_merge_removes_only_exact_cross_export_duplicates(tmp_path):
    shared = message(1, "2026-01-01T10:00:00", "A", "a", "same")
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"
    write_export(first, "Chat", [shared])
    write_export(second, "Chat", [shared, message(2, "2026-01-01T10:01:00", "B", "b", "new")])

    merged, duplicate_count = merge_messages(load_exports([first, second]))

    assert len(merged) == 2
    assert duplicate_count == 1


def test_merge_preserves_identical_messages_repeated_within_one_export(tmp_path):
    repeated = message(1, "2026-01-01T10:00:00", "A", "a", "same")
    repeated_again = dict(repeated, id=2)
    path = tmp_path / "chat.json"
    write_export(path, "Chat", [repeated, repeated_again])

    merged, duplicate_count = merge_messages(load_exports([path]))

    assert len(merged) == 2
    assert duplicate_count == 0
