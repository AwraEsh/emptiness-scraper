import asyncio
import json

from textual.widgets import Checkbox, Input, TextArea

from emptiness_scraper.settings import AppSettings
from emptiness_scraper.tui import EmptinessApp, HomeScreen, ImportScreen, ReviewScreen, ResultScreen, SettingsScreen
from emptiness_scraper.ui_library import ConfirmDialog, ReportsScreen


def fixture_export(path):
    path.write_text(json.dumps({"type": "personal_chat", "messages": [
        {"id": 1, "type": "message", "from_id": "a", "from": "Example A", "date_unixtime": "1767225600", "text": "Hello"},
        {"id": 2, "type": "message", "from_id": "b", "from": "Example B", "date_unixtime": "1767225660", "text": "سلام"},
    ]}), encoding="utf-8")


def test_keyboard_navigation_replaces_screen_instead_of_stacking_menus(tmp_path):
    async def scenario():
        app = EmptinessApp(settings=AppSettings(), config_path=tmp_path / "settings.json")
        async with app.run_test(size=(110, 36)) as pilot:
            assert isinstance(app.screen, HomeScreen)
            navigation = app.screen.query_one("#navigation")
            assert "Overview" in "".join(navigation.render_line(index).text for index in range(navigation.size.height))
            await pilot.press("down", "enter")
            assert isinstance(app.screen, ImportScreen)
            await pilot.press("escape")
            assert isinstance(app.screen, HomeScreen)
            await pilot.press("f4")
            assert isinstance(app.screen, SettingsScreen)
            assert len(app.screen_stack) == 2
    asyncio.run(scenario())


def test_invalid_export_stays_in_form_and_shows_recoverable_error(tmp_path):
    async def scenario():
        app = EmptinessApp(settings=AppSettings(), config_path=tmp_path / "settings.json")
        async with app.run_test(size=(110, 36)) as pilot:
            await pilot.press("f2")
            app.screen.query_one("#paths", TextArea).load_text(str(tmp_path / "missing.json"))
            await pilot.press("ctrl+enter")
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert isinstance(app.screen, ImportScreen)
            assert "readable JSON" in str(app.screen.query_one("#notice").render())
            assert not app.busy
    asyncio.run(scenario())


def test_tui_analyzes_only_after_mapping_confirmation(tmp_path):
    path = tmp_path / "chat.json"
    fixture_export(path)
    before = path.read_bytes()
    async def scenario():
        app = EmptinessApp(settings=AppSettings(output_directory=str(tmp_path / "reports")), config_path=tmp_path / "settings.json")
        async with app.run_test(size=(120, 45)) as pilot:
            await pilot.press("f2")
            app.screen.query_one("#paths", TextArea).load_text(str(path))
            await pilot.press("ctrl+enter")
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert isinstance(app.screen, ReviewScreen)
            await pilot.press("ctrl+enter")
            assert isinstance(app.screen, ReviewScreen)
            app.screen.query_one("#confirm-mapping", Checkbox).value = True
            await pilot.press("ctrl+enter")
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert isinstance(app.screen, ResultScreen)
            assert app.last_result["summary"]["message_count"] == 2
            assert (app.last_output / "report.md").exists()
    asyncio.run(scenario())
    assert path.read_bytes() == before


def test_settings_validation_preserves_existing_file(tmp_path):
    async def scenario():
        config = tmp_path / "settings.json"
        app = EmptinessApp(settings=AppSettings(), config_path=config)
        async with app.run_test(size=(110, 40)) as pilot:
            await pilot.press("f4")
            app.screen.query_one("#gap", Input).value = "6"
            await pilot.press("ctrl+enter")
            before = config.read_bytes()
            app.screen.query_one("#gap", Input).value = "nan"
            await pilot.press("ctrl+enter")
            assert config.read_bytes() == before
            assert app.preferences.session_gap_hours == 6
    asyncio.run(scenario())


def test_small_terminal_and_resize_keep_navigation_accessible(tmp_path):
    async def scenario():
        app = EmptinessApp(settings=AppSettings(), config_path=tmp_path / "settings.json")
        async with app.run_test(size=(70, 22)) as pilot:
            await pilot.press("f2")
            assert isinstance(app.screen, ImportScreen)
            await pilot.resize_terminal(130, 45)
            await pilot.press("f1")
            assert isinstance(app.screen, HomeScreen)
            assert app.screen.query_one("#content").region.width > 80
    asyncio.run(scenario())


def test_saved_report_preview_is_paginated_and_navigation_can_leave_it(tmp_path):
    folder = tmp_path / "emptiness-scraper-synthetic"
    folder.mkdir()
    (folder / "report.md").write_text("\n".join(f"Synthetic line {index}" for index in range(400)), encoding="utf-8")
    (folder / "analysis.json").write_text("{}", encoding="utf-8")
    async def scenario():
        app = EmptinessApp(settings=AppSettings(output_directory=str(tmp_path)), config_path=tmp_path / "settings.json")
        async with app.run_test(size=(120, 42)) as pilot:
            await pilot.press("f3")
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert isinstance(app.screen, ReportsScreen)
            assert app.screen.has_next
            await pilot.click("#next-page")
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert app.screen.page_number == 1
            assert "PAGE 2" in str(app.screen.query_one("#page-number").render())
            await pilot.press("f1")
            assert isinstance(app.screen, HomeScreen)
    asyncio.run(scenario())


def test_quit_is_confirmed_and_cannot_interrupt_active_analysis(tmp_path):
    async def scenario():
        app = EmptinessApp(settings=AppSettings(), config_path=tmp_path / "settings.json")
        async with app.run_test(size=(100, 35)) as pilot:
            app.busy = True
            await pilot.press("ctrl+q")
            assert isinstance(app.screen, HomeScreen)
            app.busy = False
            await pilot.press("ctrl+q")
            assert isinstance(app.screen, ConfirmDialog)
            await pilot.press("escape")
            assert isinstance(app.screen, HomeScreen)
    asyncio.run(scenario())


def test_persian_report_names_and_tables_keep_rows_and_raw_paths(tmp_path):
    from emptiness_scraper.display import display_text
    from textual.widgets import Markdown, OptionList

    folder = tmp_path / "emptiness-scraper-نمونه"
    folder.mkdir()
    appendix = folder / "واژه‌ها.md"
    appendix.write_text("| Name | Count |\n| --- | --- |\n| سلام Example | 12 |", encoding="utf-8")
    (folder / "analysis.json").write_text("{}", encoding="utf-8")

    async def scenario():
        app = EmptinessApp(settings=AppSettings(output_directory=str(tmp_path)), config_path=tmp_path / "settings.json")
        async with app.run_test(size=(90, 35)) as pilot:
            await pilot.press("f3")
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert app.screen.selected_file == appendix
            assert app.screen.query_one("#report-location", Input).value == str(appendix)
            options = app.screen.query_one("#reports-list", OptionList)
            assert options.get_option_at_index(0).prompt.plain == display_text(folder.name)
            assert len(app.screen.query_one("#report-body", Markdown).query("MarkdownTable")) == 1
            await pilot.resize_terminal(130, 45)
            await pilot.press("f1")
            assert isinstance(app.screen, HomeScreen)
    asyncio.run(scenario())
