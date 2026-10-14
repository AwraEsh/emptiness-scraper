# Implementation ledger

- Ruling: The approved plan exists in the conversation rather than a repository plan file. The project is not a Git repository, so no worktree or commit-based execution workspace is created.
- Ruling: The product is isolated in this directory. Existing workspace exports and relationship-analysis documents are neither imported nor bundled.
- Ruling: “Maximum detail” means all derived events in split Markdown appendices plus complete CSV and JSON data, never a duplicate of every source message.
- Verification evidence is recorded through the synthetic automated test suite and launcher smoke checks.

## 2026-10-14 audit

- The Git checkout is the authoritative source for this audit. See `AUDIT_2026-10-14.md` for findings, corrections, regression coverage, and limits.
- Regression tests reproduced alias errors, numeric ordering errors, duplicate quarter counts, hidden inactive months, cross-source reply guesses, configuration crashes, incomplete emoji extraction, and media deduplication collisions before the relevant fixes.
- Version is 1.0.1; the published 1.0.0 archive and tag are preserved.

## 1.1.0 full-screen interface

- User requested a keyboard-controlled, full-screen UI that redraws in place, a Python launcher if useful, improved interface quality, and a release after completion.
- Applied the local `terminal-ui-design` skill. Design: charcoal/ivory/amber, persistent sidebar, responsive single-workspace screens, fixed action buttons and keyboard footer.
- Replaced sequential console prompts with Textual. Analysis and export loading use workers; report previews are paginated and validated preferences are saved atomically.
- `run.py` is the shared bootstrap; shell/batch launchers delegate to it. Python package data explicitly includes `ui.tcss`.
- Local verification: 78 tests passed, one Windows-only skip. Unix PTY verified alternate-screen entry, F2 navigation, confirmed exit, and terminal restoration. Detailed continuation information is in `TUI_1.1.0.md`.
- Release gate: commit and push, confirm all four CI jobs, archive the verified commit without local data, publish v1.1.0 with checksum and verify uploaded assets.

