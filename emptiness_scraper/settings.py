from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

from platformdirs import user_config_dir

from .signals import DEFAULT_RULES


DEFAULT_ENGLISH_STOPWORDS = ["a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from", "in", "is", "it", "of", "on", "or", "that", "the", "this", "to", "was", "we", "with", "you"]
DEFAULT_PERSIAN_STOPWORDS = ["از", "با", "برای", "به", "این", "را", "رو", "که", "من", "ما", "و", "یا", "یک"]


@dataclass(slots=True)
class AppSettings:
    timezone: str = "Asia/Tehran"
    session_gap_hours: float = 6
    output_directory: str = "reports"
    english_stopwords: list[str] = field(default_factory=lambda: list(DEFAULT_ENGLISH_STOPWORDS))
    persian_stopwords: list[str] = field(default_factory=lambda: list(DEFAULT_PERSIAN_STOPWORDS))
    rules: dict[str, list[str]] = field(default_factory=lambda: {key: list(value) for key, value in DEFAULT_RULES.items()})


def settings_path() -> Path:
    return Path(user_config_dir("Emptiness Scraper", "AwraEsh")) / "settings.json"


def load_settings(path: Path | None = None) -> AppSettings:
    target = path or settings_path()
    if not target.exists():
        return AppSettings()
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
        return AppSettings(
            timezone=str(data.get("timezone", "Asia/Tehran")),
            session_gap_hours=float(data.get("session_gap_hours", 6)),
            output_directory=str(data.get("output_directory", "reports")),
            english_stopwords=[str(value) for value in data.get("english_stopwords", DEFAULT_ENGLISH_STOPWORDS)],
            persian_stopwords=[str(value) for value in data.get("persian_stopwords", DEFAULT_PERSIAN_STOPWORDS)],
            rules={str(key): [str(pattern) for pattern in value] for key, value in data.get("rules", DEFAULT_RULES).items()},
        )
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError, ValueError):
        return AppSettings()


def save_settings(settings: AppSettings, path: Path | None = None) -> Path:
    target = path or settings_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(asdict(settings), ensure_ascii=False, indent=2), encoding="utf-8")
    return target

