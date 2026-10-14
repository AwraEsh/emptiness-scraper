from __future__ import annotations

from pathlib import Path

from textual.app import App
from textual.binding import Binding

from .settings import AppSettings, load_settings
from .ui_analysis import ImportScreen, ResultScreen, ReviewScreen
from .ui_base import WorkspaceScreen
from .ui_library import AboutScreen, ConfirmDialog, HomeScreen, ReportsScreen, SettingsScreen


class EmptinessApp(App[None]):
    TITLE = "Emptiness Scraper"
    CSS_PATH = "ui.tcss"
    ENABLE_COMMAND_PALETTE = False
    BINDINGS = [
        Binding("f1", "home", "Overview"),
        Binding("f2", "new_analysis", "New"),
        Binding("f3", "reports", "Reports"),
        Binding("f4", "settings", "Preferences"),
        Binding("f5", "validate", "Validate"),
        Binding("f6", "about", "About", show=False),
        Binding("escape", "home", "Back", show=False),
        Binding("ctrl+enter", "primary", "Submit"),
        Binding("ctrl+q", "request_quit", "Quit", priority=True),
        Binding("ctrl+c", "request_quit", "Quit", show=False),
    ]

    def __init__(self, settings: AppSettings | None = None, config_path: Path | None = None) -> None:
        super().__init__()
        self.config_path = config_path
        self.preferences = settings if settings is not None else load_settings(config_path)
        self.busy = False
        self.import_text = ""
        self.last_result: dict = {}
        self.last_output: Path | None = None
        self.report_root = self.preferences.output_directory

    def on_mount(self) -> None:
        self.theme = "textual-dark"
        self.push_screen(HomeScreen())

    def navigate(self, route: str) -> None:
        if self.busy:
            self.notify("Please let the current task finish before changing sections.", severity="warning")
            return
        if not isinstance(self.screen, WorkspaceScreen):
            return
        screens = {
            "home": HomeScreen, "new": ImportScreen, "reports": ReportsScreen,
            "settings": SettingsScreen, "validate": lambda: ImportScreen(validation_only=True), "about": AboutScreen,
        }
        self.switch_screen(screens[route]())

    def action_home(self) -> None:
        self.navigate("home")

    def action_new_analysis(self) -> None:
        self.navigate("new")

    def action_reports(self) -> None:
        self.navigate("reports")

    def action_settings(self) -> None:
        self.navigate("settings")

    def action_validate(self) -> None:
        self.navigate("validate")

    def action_about(self) -> None:
        self.navigate("about")

    def action_primary(self) -> None:
        if isinstance(self.screen, WorkspaceScreen):
            self.screen.primary()

    def action_request_quit(self) -> None:
        if self.busy:
            self.notify("The current task is still writing or reading data. You can quit when it finishes.", severity="warning")
        elif isinstance(self.screen, WorkspaceScreen):
            self.push_screen(ConfirmDialog("Leave Emptiness Scraper? Saved reports and preferences remain on disk.", "Quit"), self.quit_confirmed)

    def quit_confirmed(self, confirmed: bool) -> None:
        if confirmed:
            self.exit()
