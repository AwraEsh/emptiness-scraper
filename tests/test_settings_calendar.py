from datetime import UTC, datetime

from emptiness_scraper.calendar_utils import dual_date
from emptiness_scraper.settings import AppSettings, load_settings, save_settings


def test_settings_round_trip_without_chat_content(tmp_path):
    settings = AppSettings(
        timezone="Europe/Berlin",
        session_gap_hours=8,
        output_directory=str(tmp_path / "reports"),
        english_stopwords=["the"],
        persian_stopwords=["و"],
        rules={"check_in": ["how is today"]},
    )

    save_settings(settings, tmp_path / "settings.json")
    loaded = load_settings(tmp_path / "settings.json")

    assert loaded == settings
    assert "message" not in (tmp_path / "settings.json").read_text(encoding="utf-8").lower()


def test_invalid_settings_fall_back_to_defaults(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("not json", encoding="utf-8")

    settings = load_settings(path)

    assert settings.timezone == "Asia/Tehran"
    assert settings.session_gap_hours == 6


def test_dual_date_contains_gregorian_and_jalali():
    rendered = dual_date(datetime(2026, 3, 21, 10, 0, tzinfo=UTC), "Asia/Tehran")

    assert "2026-03-21" in rendered
    assert "1405-01-01" in rendered

