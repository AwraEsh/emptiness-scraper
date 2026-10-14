from __future__ import annotations

import json
import math
import re
import os
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path

from platformdirs import user_config_dir

from .signals import DEFAULT_RULES
from .calendar_utils import resolve_timezone


DEFAULT_ENGLISH_STOPWORDS = ["a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from", "in", "is", "it", "of", "on", "or", "that", "the", "this", "to", "was", "we", "with", "you"]
DEFAULT_PERSIAN_STOPWORDS = ["از", "با", "برای", "به", "این", "را", "رو", "که", "من", "ما", "و", "یا", "یک"]


@dataclass(slots=True)
class AppSettings:
    timezone: str = "Asia/Tehran"
    session_gap_hours: float = 6
    output_directory: str = "reports"
    terminal_rendering: str = "auto"
    english_stopwords: list[str] = field(default_factory=lambda: list(DEFAULT_ENGLISH_STOPWORDS))
    persian_stopwords: list[str] = field(default_factory=lambda: list(DEFAULT_PERSIAN_STOPWORDS))
    rules: dict[str, list[str]] = field(default_factory=lambda: {key: list(value) for key, value in DEFAULT_RULES.items()})


def validate_settings(settings: AppSettings) -> None:
    if settings.terminal_rendering not in {"auto", "native", "compatibility"}:
        raise ValueError("Terminal rendering must be auto, native, or compatibility.")
    resolve_timezone(settings.timezone)
    if not math.isfinite(settings.session_gap_hours) or settings.session_gap_hours <= 0:
        raise ValueError("Session gap must be finite and positive.")
    if not settings.output_directory.strip():
        raise ValueError("Output directory cannot be empty.")
    if not isinstance(settings.rules, dict):
        raise ValueError("Language rules must be a mapping of categories to patterns.")
    for category, patterns in settings.rules.items():
        if not isinstance(patterns, list):
            raise ValueError(f"Rules for {category} must be a list.")
        for pattern in patterns:
            try:
                re.compile(pattern)
            except (re.error, TypeError) as error:
                raise ValueError(f"Invalid rule in {category}: {error}") from error


def settings_path() -> Path:
    return Path(user_config_dir("Emptiness Scraper", "AwraEsh")) / "settings.json"


def load_settings(path: Path | None = None) -> AppSettings:
    target = path or settings_path()
    if not target.exists():
        return AppSettings()
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Settings must be an object.")
        if not isinstance(data.get("rules", DEFAULT_RULES), dict):
            raise ValueError("Rules must be an object.")
        if any(not isinstance(value, list) or any(not isinstance(pattern, str) for pattern in value) for value in data.get("rules", DEFAULT_RULES).values()):
            raise ValueError("Rule categories must contain lists of strings.")
        for key in ("english_stopwords", "persian_stopwords"):
            if key in data and (not isinstance(data[key], list) or any(not isinstance(value, str) for value in data[key])):
                raise ValueError("Stopwords must be lists of strings.")
        settings = AppSettings(
            timezone=str(data.get("timezone", "Asia/Tehran")),
            session_gap_hours=float(data.get("session_gap_hours", 6)),
            output_directory=str(data.get("output_directory", "reports")),
            terminal_rendering=str(data.get("terminal_rendering", "auto")),
            english_stopwords=[str(value) for value in data.get("english_stopwords", DEFAULT_ENGLISH_STOPWORDS)],
            persian_stopwords=[str(value) for value in data.get("persian_stopwords", DEFAULT_PERSIAN_STOPWORDS)],
            rules={str(key): [str(pattern) for pattern in value] for key, value in data.get("rules", DEFAULT_RULES).items()},
        )
        validate_settings(settings)
        return settings
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError, AttributeError, KeyError):
        return AppSettings()


def save_settings(settings: AppSettings, path: Path | None = None) -> Path:
    validate_settings(settings)
    target = path or settings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=target.parent, delete=False) as handle:
            temporary = Path(handle.name)
            json.dump(asdict(settings), handle, ensure_ascii=False, indent=2, allow_nan=False)
        os.replace(temporary, target)
    finally:
        if temporary and temporary.exists():
            temporary.unlink()
    return target

