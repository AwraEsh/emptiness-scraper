from __future__ import annotations

from copy import deepcopy

from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Button, Checkbox, DataTable, Input, Select, Static, TextArea

from .calendar_utils import resolve_timezone
from .identity import Side, map_sides, sender_counts, sender_names, suggest_sides
from .models import ExportFile
from .services import analyze_exports, file_audit, load_input, parse_intervals
from .settings import validate_settings
from .ui_base import WorkspaceScreen


class ImportScreen(WorkspaceScreen):
    route = "new"
    heading = "Bring your conversation into focus."
    eyebrow = "01 / IMPORT"

    def __init__(self, validation_only: bool = False) -> None:
        super().__init__()
        self.validation_only = validation_only
        if validation_only:
            self.route = "validate"
            self.heading = "Check your exports before analysis."
            self.eyebrow = "EXPORT VALIDATION"

    def content(self) -> ComposeResult:
        yield Static("Paste JSON file paths or a directory. Use one path per line or separate paths with semicolons. Files are ordered by their internal timestamps.", classes="lead", markup=False)
        yield Static("EXPORT PATHS", classes="field-label")
        yield TextArea(self.workspace.import_text, id="paths", placeholder="/home/you/exports/1.json\n/home/you/exports/2.json")
        yield Static("EXPORT DEVICE TIMEZONE", classes="field-label")
        yield Input(self.workspace.preferences.timezone, id="timezone", placeholder="Asia/Tehran, Europe/Berlin, or +04:00")
        yield Static("Epoch timestamps remain authoritative. This timezone also interprets dates when an epoch is missing.", classes="lead", markup=False)
        yield DataTable(id="export-table", zebra_stripes=True)

    def controls(self) -> ComposeResult:
        with Horizontal(classes="actions"):
            yield Button("Validate exports" if self.validation_only else "Review participants", variant="primary", id="load")
            yield Button("Back", id="back")

    def on_mount(self) -> None:
        super().on_mount()
        self.query_one("#export-table", DataTable).add_columns("File", "Messages", "Service", "First UTC", "Last UTC")
        self.query_one("#export-table").display = False
        self.query_one("#paths", TextArea).focus()

    def on_text_area_changed(self, event: TextArea.Changed) -> None:
        if event.text_area.id == "paths":
            self.workspace.import_text = event.text_area.text

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "load":
            self.primary()
        elif event.button.id == "back":
            self.workspace.navigate("home")

    def primary(self) -> None:
        if self.workspace.busy:
            return
        text = self.query_one("#paths", TextArea).text
        timezone_name = self.query_one("#timezone", Input).value.strip()
        try:
            resolve_timezone(timezone_name)
            if not text.strip():
                raise ValueError("Add at least one JSON export or directory.")
        except (ValueError, KeyError) as error:
            self.show_notice(str(error), error=True)
            return
        self.set_busy(True, "Reading and validating Telegram exports…")
        self.load_exports_worker(text, timezone_name)

    @work(thread=True, exclusive=True)
    def load_exports_worker(self, text: str, timezone_name: str) -> None:
        try:
            exports = load_input(text, timezone_name)
            if not self.validation_only:
                suggest_sides(exports)
            self.app.call_from_thread(self.loaded, exports, timezone_name)
        except Exception as error:
            self.app.call_from_thread(self.failed, str(error))

    def failed(self, message: str) -> None:
        self.set_busy(False)
        self.show_notice(message, error=True)

    def loaded(self, exports: list[ExportFile], timezone_name: str) -> None:
        self.set_busy(False)
        if not self.validation_only:
            self.app.switch_screen(ReviewScreen(exports, timezone_name))
            return
        table = self.query_one("#export-table", DataTable)
        table.clear()
        for export in exports:
            table.add_row(Text(export.path.name), str(len(export.messages)), str(export.service_count), str(export.first_timestamp or "Empty"), str(export.last_timestamp or "Empty"))
        table.display = True
        _, warnings = file_audit(exports)
        self.show_notice(f"Validated {len(exports)} export(s). " + " ".join(warnings), success=True)


class ReviewScreen(WorkspaceScreen):
    route = "new"
    heading = "Two people. One clear timeline."
    eyebrow = "02 / REVIEW & ANALYZE"

    def __init__(self, exports: list[ExportFile], timezone_name: str) -> None:
        super().__init__()
        self.exports = exports
        self.timezone_name = timezone_name
        self.messages = [message for export in exports for message in export.messages]
        self.suggested_a, self.suggested_b, _ = suggest_sides(exports)
        self.senders = sender_counts(self.messages).most_common()

    def content(self) -> ComposeResult:
        yield Static(f"{len(self.exports)} export(s) · {len(self.messages):,} messages · {self.timezone_name}\nAssign every account to one participant or exclude it. Suggestions use message volume and need your review.", classes="lead", markup=False)
        yield Static("PARTICIPANT NAMES", classes="field-label")
        with Horizontal(classes="mapping-row"):
            yield Input(self.suggested_a.label, id="name-a", placeholder="Participant A")
            yield Input(self.suggested_b.label, id="name-b", placeholder="Participant B")
        names = sender_names(self.messages)
        yield Static("ACCOUNT MAPPING", classes="field-label")
        for index, (sender_id, count) in enumerate(self.senders):
            selected = "a" if sender_id in self.suggested_a.ids else "b" if sender_id in self.suggested_b.ids else "exclude"
            with Horizontal(classes="mapping-row"):
                label = Static(Text(f"{sender_id} · {count:,} messages\n{names[sender_id]}", no_wrap=True, overflow="ellipsis"))
                label.tooltip = f"{names[sender_id]}\n{sender_id}\n{count:,} messages"
                yield label
                yield Select([("Participant A", "a"), ("Participant B", "b"), ("Exclude", "exclude")], value=selected, allow_blank=False, id=f"sender-{index}")
        yield Checkbox("I reviewed the participant mapping", id="confirm-mapping")
        yield Static("SESSION GAP / HOURS", classes="field-label")
        yield Input(str(self.workspace.preferences.session_gap_hours), id="gap")
        yield Static("OUTPUT DIRECTORY", classes="field-label")
        yield Input(self.workspace.preferences.output_directory, id="output")
        yield Static("INCOMPLETE INTERVALS / OPTIONAL", classes="field-label")
        yield TextArea(id="intervals", placeholder="2026-01-02 09:00 | 2026-01-03 18:00 | missing messages")
        yield Static("One interval per line: local Gregorian start | end | optional label. Leave empty for a complete timeline.", classes="lead", markup=False)

    def controls(self) -> ComposeResult:
        with Horizontal(classes="actions"):
            yield Button("Create report", variant="primary", id="analyze")
            yield Button("Back to import", id="back")

    def on_mount(self) -> None:
        super().on_mount()
        self.query_one("#name-a", Input).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "analyze":
            self.primary()
        elif event.button.id == "back":
            self.workspace.navigate("new")

    def primary(self) -> None:
        if self.workspace.busy:
            return
        try:
            if not self.query_one("#confirm-mapping", Checkbox).value:
                raise ValueError("Review the accounts and confirm the participant mapping first.")
            groups: dict[str, set[str]] = {"a": set(), "b": set()}
            for index, (sender_id, _) in enumerate(self.senders):
                selection = self.query_one(f"#sender-{index}", Select).value
                if selection in groups:
                    groups[selection].add(sender_id)
            sides = [Side(self.query_one("#name-a", Input).value.strip(), groups["a"]), Side(self.query_one("#name-b", Input).value.strip(), groups["b"])]
            map_sides(self.messages, sides)
            settings = deepcopy(self.workspace.preferences)
            settings.timezone = self.timezone_name
            settings.session_gap_hours = float(self.query_one("#gap", Input).value)
            settings.output_directory = self.query_one("#output", Input).value.strip()
            validate_settings(settings)
            intervals = parse_intervals(self.query_one("#intervals", TextArea).text, self.timezone_name)
        except (ValueError, KeyError) as error:
            self.show_notice(str(error), error=True)
            return
        self.set_busy(True, "Preparing your analysis…")
        self.analyze_worker(sides, settings, intervals)

    @work(thread=True, exclusive=True)
    def analyze_worker(self, sides, settings, intervals) -> None:
        try:
            output, result = analyze_exports(self.exports, sides, settings, intervals, lambda stage: self.app.call_from_thread(self.show_notice, stage))
            self.app.call_from_thread(self.finished, output, result)
        except Exception as error:
            self.app.call_from_thread(self.failed, str(error))

    def failed(self, message: str) -> None:
        self.set_busy(False)
        self.show_notice(message, error=True)

    def finished(self, output, result) -> None:
        self.set_busy(False)
        self.workspace.last_output = output
        self.workspace.last_result = result
        self.workspace.report_root = str(output.parent)
        self.app.switch_screen(ResultScreen())


class ResultScreen(WorkspaceScreen):
    route = "new"
    heading = "Your report is ready."
    eyebrow = "03 / COMPLETE"

    def content(self) -> ComposeResult:
        result = self.workspace.last_result
        with Horizontal(classes="cards"):
            yield Static(f"MESSAGES\n{result['summary']['message_count']:,}", classes="card")
            yield Static(f"SESSIONS\n{len(result['sessions']):,}", classes="card")
            yield Static(f"RESPONSES\n{len(result['responses']):,}", classes="card")
        yield Static("REPORT DIRECTORY / SELECT TO COPY", classes="field-label")
        yield Input(str(self.workspace.last_output), id="report-location")
        yield DataTable(id="participants-table", zebra_stripes=True)
        yield Static("Markdown appendices, CSV tables, and analysis.json were saved together.\n\nTip: Send the generated Markdown files to your Telegram Saved Messages for the best reading experience.", classes="lead", markup=False)
        warnings = result.get("audit", {}).get("warnings", [])
        if warnings:
            yield Static("DATA QUALITY\n" + "\n".join(warnings), classes="card", markup=False)

    def controls(self) -> ComposeResult:
        with Horizontal(classes="actions"):
            yield Button("Read report", variant="primary", id="read-report")
            yield Button("New analysis", id="another")

    def on_mount(self) -> None:
        super().on_mount()
        table = self.query_one("#participants-table", DataTable)
        table.add_columns("Participant", "Messages", "Turns", "Words", "Reactions received")
        for name, values in self.workspace.last_result["participants"].items():
            table.add_row(Text(name), *(str(values[key]) for key in ("messages", "turns", "words", "reactions")))
        self.query_one("#read-report", Button).focus()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.workspace.navigate("reports" if event.button.id == "read-report" else "new")

    def primary(self) -> None:
        self.workspace.navigate("reports")
