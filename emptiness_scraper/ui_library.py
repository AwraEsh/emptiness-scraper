from __future__ import annotations

import json
from copy import deepcopy
from pathlib import Path
from rich.text import Text

from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Markdown, OptionList, Select, Static, TextArea
from textual.widgets.option_list import Option
from textual.worker import get_current_worker

from .branding import BANNER, CREATOR_NOTE, about_text
from .services import ReportPage, list_reports, read_report_page
from .settings import AppSettings, save_settings, validate_settings
from .ui_base import WorkspaceScreen


class ConfirmDialog(ModalScreen[bool]):
    DEFAULT_CSS = """
    ConfirmDialog { align: center middle; background: #111416 85%; }
    ConfirmDialog > Vertical { width: 58; max-width: 90%; height: auto; padding: 2 3; border: round #dfbf83; background: #1d2326; }
    ConfirmDialog Static { height: auto; margin-bottom: 1; }
    """
    BINDINGS = [("escape", "cancel", "Cancel")]

    def __init__(self, message: str, confirm_label: str = "Continue") -> None:
        super().__init__()
        self.message = message
        self.confirm_label = confirm_label

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Static(self.message, markup=False)
            with Horizontal(classes="actions"):
                yield Button("Cancel", id="cancel-dialog")
                yield Button(self.confirm_label, variant="primary", id="confirm-dialog")

    def on_mount(self) -> None:
        self.query_one("#cancel-dialog", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "confirm-dialog")

    def action_cancel(self) -> None:
        self.dismiss(False)


class HomeScreen(WorkspaceScreen):
    heading = "A quiet workspace for your conversations."
    eyebrow = "OVERVIEW / LOCAL FIRST"

    def content(self) -> ComposeResult:
        yield Static(BANNER, id="ascii", markup=False)
        yield Static(CREATOR_NOTE, classes="lead", markup=False)
        with Horizontal(classes="cards"):
            yield Static("01 / IMPORT\nOne chat. Multiple exports.\nOrdered by real timestamps.", classes="card", markup=False)
            yield Static("02 / COMPARE\nSessions, replies, and patterns.\nPersian and English together.", classes="card", markup=False)
            yield Static("03 / READ\nMarkdown, CSV, and JSON.\nKeep a complete local record.", classes="card", markup=False)
        yield Static("Start with Telegram JSON exports. Confirm the two participants, then let the workspace organize the timeline. Your source files stay untouched.", classes="lead", markup=False)
        if self.workspace.last_result:
            summary = self.workspace.last_result["summary"]
            yield Static(f"LAST ANALYSIS\n{summary['message_count']:,} messages · {summary['active_days']} active days", classes="card", markup=False)

    def controls(self) -> ComposeResult:
        with Horizontal(classes="actions"):
            yield Button("Start analysis", variant="primary", id="start")
            yield Button("Browse reports", id="browse")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.workspace.navigate("new" if event.button.id == "start" else "reports")

    def primary(self) -> None:
        self.workspace.navigate("new")


class SettingsScreen(WorkspaceScreen):
    route = "settings"
    heading = "Make the workspace yours."
    eyebrow = "PREFERENCES / SAVED LOCALLY"

    def content(self) -> ComposeResult:
        settings = self.workspace.preferences
        yield Static("Changes are saved only when you choose Save preferences. Language rules use regular expressions; an empty object disables text rules.", classes="lead", markup=False)
        yield Static("DEFAULT TIMEZONE", classes="field-label")
        yield Input(settings.timezone, id="timezone")
        yield Static("SESSION GAP / HOURS", classes="field-label")
        yield Input(str(settings.session_gap_hours), id="gap")
        yield Static("REPORT DIRECTORY", classes="field-label")
        yield Input(settings.output_directory, id="output")
        yield Static("ENGLISH STOPWORDS / COMMA OR LINE SEPARATED", classes="field-label")
        yield TextArea(", ".join(settings.english_stopwords), id="english-stopwords")
        yield Static("PERSIAN STOPWORDS / COMMA OR LINE SEPARATED", classes="field-label")
        yield TextArea(", ".join(settings.persian_stopwords), id="persian-stopwords")
        yield Static("LANGUAGE RULES / JSON", classes="field-label")
        yield TextArea(json.dumps(settings.rules, ensure_ascii=False, indent=2), id="rules-editor")

    def controls(self) -> ComposeResult:
        with Horizontal(classes="actions"):
            yield Button("Save preferences", variant="primary", id="save-settings")
            yield Button("Reset defaults", id="reset-settings")

    def on_mount(self) -> None:
        super().on_mount()
        self.query_one("#timezone", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save-settings":
            self.primary()
        elif event.button.id == "reset-settings":
            self.app.push_screen(ConfirmDialog("Replace the form with default preferences? You can review them before saving.", "Reset"), self.reset_form)

    def reset_form(self, confirmed: bool) -> None:
        if not confirmed:
            return
        defaults = AppSettings()
        self.query_one("#timezone", Input).value = defaults.timezone
        self.query_one("#gap", Input).value = str(defaults.session_gap_hours)
        self.query_one("#output", Input).value = defaults.output_directory
        self.query_one("#english-stopwords", TextArea).load_text(", ".join(defaults.english_stopwords))
        self.query_one("#persian-stopwords", TextArea).load_text(", ".join(defaults.persian_stopwords))
        self.query_one("#rules-editor", TextArea).load_text(json.dumps(defaults.rules, ensure_ascii=False, indent=2))
        self.show_notice("Defaults loaded into the form. Save to apply.")

    def primary(self) -> None:
        try:
            settings = deepcopy(self.workspace.preferences)
            settings.timezone = self.query_one("#timezone", Input).value.strip()
            settings.session_gap_hours = float(self.query_one("#gap", Input).value)
            settings.output_directory = self.query_one("#output", Input).value.strip()
            settings.english_stopwords = [value.strip() for value in self.query_one("#english-stopwords", TextArea).text.replace("\n", ",").split(",") if value.strip()]
            settings.persian_stopwords = [value.strip() for value in self.query_one("#persian-stopwords", TextArea).text.replace("\n", ",").split(",") if value.strip()]
            settings.rules = json.loads(self.query_one("#rules-editor", TextArea).text)
            validate_settings(settings)
            save_settings(settings, self.workspace.config_path)
        except (ValueError, KeyError, OSError, TypeError) as error:
            self.show_notice(str(error), error=True)
            return
        self.workspace.preferences = settings
        self.workspace.report_root = settings.output_directory
        self.show_notice("Preferences saved. New analyses will use these defaults.", success=True)


class ReportsScreen(WorkspaceScreen):
    route = "reports"
    heading = "Every timeline, within reach."
    eyebrow = "REPORT LIBRARY / MARKDOWN PREVIEW"

    def __init__(self) -> None:
        super().__init__()
        self.reports: list[Path] = []
        self.selected_report: Path | None = None
        self.selected_file: Path | None = None
        self.page_number = 0
        self.has_next = False
        self.request_token = 0
        self.library_error = ""

    def content(self) -> ComposeResult:
        try:
            self.reports = list_reports(self.workspace.report_root)
        except OSError as error:
            self.library_error = str(error)
        yield Static("Select a report, then an appendix. Previews are paginated to keep large reports responsive. Use the location field to select and copy the full path.", classes="lead", markup=False)
        yield OptionList(*(Option(Text(path.name), id=str(index)) for index, path in enumerate(self.reports)), id="reports-list")
        yield Select([], prompt="Choose an appendix", id="report-file")
        yield Input("", id="report-location", placeholder="No report selected")
        yield Static("", id="page-number", markup=False)
        with VerticalScroll(id="preview-scroll"):
            yield Markdown("No reports yet. Create an analysis to populate your library.", id="report-body", open_links=False)

    def controls(self) -> ComposeResult:
        with Horizontal(classes="actions"):
            yield Button("Previous page", id="previous-page", disabled=True)
            yield Button("Next page", id="next-page", disabled=True)

    def on_mount(self) -> None:
        super().on_mount()
        self.query_one("#reports-list", OptionList).focus()
        if self.library_error:
            self.show_notice(self.library_error, error=True)
        if self.reports:
            index = self.reports.index(self.workspace.last_output) if self.workspace.last_output in self.reports else 0
            self.query_one("#reports-list", OptionList).highlighted = index
            self.choose_report(index)

    def choose_report(self, index: int) -> None:
        self.selected_report = self.reports[index]
        try:
            files = sorted(self.selected_report.glob("*.md"))
        except OSError as error:
            self.show_notice(str(error), error=True)
            return
        select = self.query_one("#report-file", Select)
        select.set_options([(path.name, path.name) for path in files])
        select.value = "report.md"

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_list.id == "reports-list":
            event.stop()
            self.choose_report(event.option_index)
        else:
            super().on_option_list_option_selected(event)

    def on_select_changed(self, event: Select.Changed) -> None:
        if event.select.id != "report-file" or not isinstance(event.value, str) or self.selected_report is None:
            return
        self.selected_file = self.selected_report / event.value
        self.page_number = 0
        self.query_one("#report-location", Input).value = str(self.selected_file)
        self.request_preview()

    def request_preview(self) -> None:
        if self.selected_file is None:
            return
        self.request_token += 1
        self.query_one("#loading").display = True
        self.show_notice("Loading report preview…")
        self.preview_worker(self.selected_file, self.page_number, self.request_token)

    @work(thread=True, exclusive=True, group="preview")
    def preview_worker(self, path: Path, page_number: int, token: int) -> None:
        worker = get_current_worker()
        try:
            page = read_report_page(path, page_number)
            if not worker.is_cancelled:
                self.app.call_from_thread(self.preview_loaded, page, token)
        except (OSError, UnicodeError, ValueError) as error:
            if not worker.is_cancelled:
                self.app.call_from_thread(self.preview_failed, str(error), token)

    async def preview_loaded(self, page: ReportPage, token: int) -> None:
        if not self.is_mounted or token != self.request_token:
            return
        self.has_next = page.has_next
        await self.query_one("#report-body", Markdown).update(page.text[:200000])
        self.query_one("#preview-scroll", VerticalScroll).scroll_home(animate=False)
        self.query_one("#page-number", Static).update(f"PAGE {page.page + 1} · up to 160 source lines per page")
        self.query_one("#previous-page", Button).disabled = page.page == 0
        self.query_one("#next-page", Button).disabled = not page.has_next
        self.query_one("#loading").display = False
        self.show_notice("Preview ready. Full data remains available in the saved files.")

    def preview_failed(self, message: str, token: int) -> None:
        if self.is_mounted and token == self.request_token:
            self.query_one("#loading").display = False
            self.show_notice(message, error=True)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "previous-page" and self.page_number > 0:
            self.page_number -= 1
        elif event.button.id == "next-page" and self.has_next:
            self.page_number += 1
        else:
            return
        self.request_preview()


class AboutScreen(WorkspaceScreen):
    route = "about"
    heading = "Built with a reason. Shared with you."
    eyebrow = "ABOUT / KEYBOARD GUIDE"

    def content(self) -> ComposeResult:
        yield Static(BANNER, id="ascii", markup=False)
        yield Static(CREATOR_NOTE, classes="lead", markup=False)
        yield Static(about_text(), classes="card", markup=False)
        yield Static("KEYBOARD\n\n↑ / ↓       Navigate menus and choices\nTab          Next control\nShift+Tab    Previous control\nEnter        Activate a button or choice\nSpace        Toggle a checkbox\nCtrl+Enter   Submit the current form\nF1–F6        Switch workspace sections\nEscape       Return to overview\nCtrl+Q       Quit with confirmation", classes="card", markup=False)
        yield Static("OBSERVATION, WITH CONTEXT\n\nThe tool extracts timing, participation, and transparent text patterns. It does not infer feelings, attraction, personality, or intent.", classes="lead", markup=False)
