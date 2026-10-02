from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class Message:
    source: str
    message_id: int | str
    timestamp: datetime
    sender_id: str
    sender_name: str
    text: str = ""
    message_type: str = "message"
    reply_to_message_id: int | str | None = None
    media_type: str = ""
    edited: bool = False
    forwarded: bool = False
    reactions: int = 0
    raw: dict[str, Any] = field(default_factory=dict, repr=False)


@dataclass(slots=True)
class ExportFile:
    path: Path
    chat_name: str
    chat_type: str
    messages: list[Message]
    service_count: int
    first_timestamp: datetime | None
    last_timestamp: datetime | None


@dataclass(slots=True)
class CensoredInterval:
    start: datetime
    end: datetime
    label: str = "Incomplete interval"


@dataclass(slots=True)
class Session:
    index: int
    messages: list[Message]
    censored: bool = False

    @property
    def start(self) -> datetime:
        return self.messages[0].timestamp

    @property
    def end(self) -> datetime:
        return self.messages[-1].timestamp


@dataclass(slots=True)
class Turn:
    session_index: int
    sender_id: str
    sender_name: str
    start: datetime
    end: datetime
    message_count: int
    characters: int
    message_ids: list[int | str]


@dataclass(slots=True)
class Response:
    session_index: int
    responder_id: str
    responder_name: str
    previous_sender_id: str
    sent_at: datetime
    previous_at: datetime
    latency_seconds: float
    comparison_safe: bool

