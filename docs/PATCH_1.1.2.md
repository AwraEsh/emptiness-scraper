# 1.1.2 — Undo forced Persian shaping

Supersedes the shaping approach described in PATCH_1.1.1.md. That version converted logical Persian into reversed presentation-form code points before Textual rendered labels and Markdown cells. This is not portable across terminal renderers and the user's screenshot showed unreadable output. Its tests checked the conversion, not physical-terminal readability.

This patch removes the unconditional conversion. Auto and Native keep Persian in logical Unicode order, with original letters, half-spaces, diacritics, punctuation and emoji preserved. The terminal owns shaping. Control-character sanitation and single-line list labels remain, as does appendix fallback. Layout, analysis and stored reports are unchanged.

Preferences now includes Persian terminal rendering: Auto, Native Unicode and Compatibility. VTE/GNOME environment markers are detected; Auto uses Native. Unrecognized terminals use the same conservative default and show a prompt directing the user to Preferences if Persian is unreadable. Compatibility explicitly opts into application shaping for terminals lacking native support; it is not used on GNOME automatically. Saving applies immediately to newly rendered content; reopen an existing report preview to refresh it. Old preference files default to Auto.

Regression tests assert original Unicode at the native display boundary and in actual Textual Markdown cell content, terminal detection, explicit overrides, mode switching and preference persistence. This verifies that native mode no longer substitutes or reverses Persian; it does not prove correct bidirectional layout in every terminal. Terminal rendering still depends on the emulator and font. The user's original screenshot is private and is not bundled.
