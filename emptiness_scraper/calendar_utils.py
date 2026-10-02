from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import jdatetime


def resolve_timezone(value: str):
    cleaned = value.strip()
    if cleaned.upper() == "UTC":
        return UTC
    if cleaned.startswith(("+", "-")) and len(cleaned) == 6:
        sign = 1 if cleaned[0] == "+" else -1
        hours, minutes = map(int, cleaned[1:].split(":"))
        return timezone(sign * timedelta(hours=hours, minutes=minutes))
    return ZoneInfo(cleaned)


def dual_date(value: datetime, timezone_name: str) -> str:
    localized = value.astimezone(resolve_timezone(timezone_name))
    jalali = jdatetime.datetime.fromgregorian(datetime=localized.replace(tzinfo=None))
    return f"{localized:%Y-%m-%d %H:%M:%S} / {jalali:%Y-%m-%d %H:%M:%S}"


def parse_local_datetime(value: str, timezone_name: str) -> datetime:
    parsed = datetime.fromisoformat(value.strip())
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=resolve_timezone(timezone_name))
    return parsed.astimezone(UTC)

