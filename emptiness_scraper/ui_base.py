from __future__ import annotations

from typing import TYPE_CHECKING, cast

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import Screen
from textual.widgets import Footer, LoadingIndicator, OptionList, Static
from textual.widgets.option_list import Option

from . import __version__

if TYPE_CHECKING:
    from .tui import EmptinessApp


NAVIGATION = (
    ("home", "Overview"), ("new", "New analysis"), ("reports", "Report library"),
    ("settings", "Preferences"), ("validate", "Validate exports"), ("about", "About & keys"),
)


class WorkspaceScreen(Screen):
    route = "home"
    heading = "Workspace"
    eyebrow = "EMPTINESS / SCRAPER"

    @property
    def workspace(self) -> EmptinessApp:
        return cast("EmptinessApp", self.app)

    def content(self) -> ComposeResult:
        yield Static("")

    def controls(self) -> ComposeResult:
        yield from ()

    def compose(self) -> ComposeResult:
        yield Static(f"EMPTINESS  /  SCRAPER                                      v{__version__}  ·  LOCAL WORKSPACE", id="topbar", markup=False)
        with Horizontal(id="workspace"):
            with Vertical(id="sidebar"):
                yield Static("[ E S ]\n\nDIALOGUE WORKSPACE", id="side-brand", markup=False)
                yield OptionList(*(Option(label + "\n", id=route) for route, label in NAVIGATION), id="navigation")
                yield Static("LOCAL PROCESSING\nNo uploads. No accounts.\n\nF1–F6  Switch sections\nTab     Move focus\nEnter   Select", id="side-note", markup=False)
            with Vertical(id="main"):
                yield Static(self.eyebrow, id="eyebrow", markup=False)
                yield Static(self.heading, id="page-title", markup=False)
                with VerticalScroll(id="content"):
                    yield from self.content()
                yield LoadingIndicator(id="loading")
                yield Static("", id="notice", markup=False)
                yield from self.controls()
        yield Footer()

    def on_mount(self) -> None:
        self.set_class(self.size.width < 96, "compact")
        self.set_class(self.size.width < 124, "narrow-banner")
        navigation = self.query_one("#navigation", OptionList)
        navigation.highlighted = [item[0] for item in NAVIGATION].index(self.route)
        if self.route == "home":
            navigation.focus()

    def on_resize(self, event) -> None:
        self.set_class(event.size.width < 96, "compact")
        self.set_class(event.size.width < 124, "narrow-banner")

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        if event.option_list.id == "navigation" and event.option.id:
            event.stop()
            self.workspace.navigate(event.option.id)

    def show_notice(self, text: str, error: bool = False, success: bool = False) -> None:
        notice = self.query_one("#notice", Static)
        notice.update(text if len(text) <= 420 else text[:417] + "…")
        notice.set_class(error, "error")
        notice.set_class(success, "success")

    def set_busy(self, busy: bool, stage: str = "") -> None:
        self.workspace.busy = busy
        self.query_one("#loading").display = busy
        for button in self.query(".actions Button"):
            button.disabled = busy
        for field in self.query("Input, Select, TextArea, Checkbox"):
            field.disabled = busy
        if stage:
            self.show_notice(stage)

    def primary(self) -> None:
        pass
