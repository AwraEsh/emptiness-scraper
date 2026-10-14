# Full-screen terminal workspace — 1.1.0

## Interface contract

The application now runs in the terminal's alternate screen buffer. Navigation replaces the existing screen; it does not append menus or prompts to scrollback. Textual owns input, focus, redraws, resize events, and terminal restoration. All screens use the same charcoal, ivory, and amber palette. `NO_COLOR` is respected.

The sidebar offers Overview, New analysis, Report library, Preferences, Validate exports, and About & keys. F1 through F6 access these sections directly, including on narrow terminals where the sidebar is hidden. Tab and Shift+Tab move focus, arrow keys change selections, Enter activates controls, Space toggles confirmation, and Ctrl+Enter submits forms. Ctrl+Q opens an exit confirmation.

The ASCII banner, creator note, and public author contacts are retained. No previous private conversation data is bundled.

## Workflow

1. Paste one path per line, or use semicolon-separated paths, and select the export-device timezone.
2. Review account assignments with keyboard-operable selects. Account aliases can share one participant; extra senders can be excluded. Explicitly confirm the mapping.
3. Set participant labels, session threshold, output directory, and optional incomplete intervals.
4. Run analysis. Background workers keep the interface responsive while reading exports and generating reports. Stage labels and an indeterminate activity indicator report real work without fabricated percentages.
5. Review participant metrics and open the report library. Markdown appendices are previewed in pages of 160 source lines; continuation pages preserve table headers, and oversized preview content is bounded. Original output files remain complete.

Preferences are edited in forms and validated before atomic saving. Resetting requires confirmation and fills the form without silently saving. Invalid input stays on the same screen with a recoverable error. Leaving an unsaved preferences form discards those edits; use Save preferences to persist them.

## Modules

- `tui.py`: application lifecycle and global keyboard bindings.
- `ui_base.py` and `ui.tcss`: shared layout, statuses, and responsive styling.
- `ui_analysis.py`: input, identity review, workers, and completed analyses.
- `ui_library.py`: overview, report preview, preferences, help, and confirmations.
- `services.py`: UI-independent loading, analysis, interval parsing, and paginated report reading.
- `branding.py`: public artwork and attribution.
- `run.py`: dependency-free Python bootstrap, local environment setup, offline dependency checks, and quiet startup screen.

`run.sh` and `run.bat` are compatibility wrappers around the same Python launcher. Package metadata includes the Textual stylesheet. The analysis engine and report formats are shared with the previous version.

## Stability and limits

Navigation and quitting are held while an analysis is running so output generation can finish cleanly. Report previews use request tokens and cancelled-worker checks to prevent older loads from replacing a newer selection. The interface uses an existing terminal window's full area; it does not forcibly maximize an operating-system window. An interactive TTY is required for the UI. Explicit smoke mode remains available to CI without opening a full-screen terminal.

Custom text rules use the existing Unicode regex dependency with a 50 ms per-match time limit. Pathological expressions produce a recoverable validation error rather than blocking a background thread indefinitely. Report read errors stay in the library view.

Keyboard interaction is tested through Textual's headless Pilot API at multiple terminal sizes. Launcher tests verify installed-dependency reuse without an accessible package index. All end-to-end data is synthetic. A Unix PTY check verifies alternate-screen entry and restoration on exit. Windows and Linux CI remain required before releasing.

Local verification for the completed interface: 78 passed, one Windows-only launcher test skipped. Tests include real PTY keyboard input, alternate-buffer restoration, identity confirmation, analysis output, invalid input recovery, settings persistence, responsive resizing, report pagination with table headers, and confirmation dialogs. The packaged wheel was loaded separately to verify that its UI modules and stylesheet are included. The overview and import screens were rendered and visually inspected in both monochrome and true-color modes.
