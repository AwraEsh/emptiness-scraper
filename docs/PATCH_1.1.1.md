# 1.1.1 — Persian display stability

This patch preserves the existing full-screen workflow and English interface.

- Persian read-only labels are shaped and reordered for terminal cells rather than left to terminal-dependent bidirectional rendering.
- Mixed English/Persian labels, participant tables, report lists, notices and Markdown preview text use a shared display boundary.
- Markdown structure, links, original filenames, input values and saved report content remain unchanged. Preview text is prepared only after Markdown parsing.
- Single-line list labels cannot inject extra rows or terminal control characters. Joined emoji remain intact.
- Report folders with a surviving Markdown appendix can still be opened when the main report is missing. The first available appendix is selected automatically.

Editable text still uses logical Unicode order so cursor positions, copying and file access remain accurate. Terminal fonts need Persian/Arabic glyph coverage; software cannot supply glyphs missing from the selected font. Long wrapped paragraphs and rich inline spans are not a full bidirectional document editor.

Regression coverage includes mixed-script display, controls, Markdown table/link integrity, Persian filenames, appendix fallback and terminal resizing. All fixtures are synthetic. Analysis definitions and exported metrics are unchanged.
