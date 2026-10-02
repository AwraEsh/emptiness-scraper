# Emptiness Scraper :0

Emptiness Scraper is an offline terminal application for comparing the observable activity of two participants in Telegram one-to-one JSON exports. It measures timing, participation, sessions, responses, gaps, bilingual text, emoji, and transparent rule-based events. It does not infer attraction, intent, personality, or psychological state.

Telegram: @Ou_Rash

## Quick start

### Windows

1. Install Python 3.11 or newer from [python.org](https://www.python.org/downloads/). Enable “Add Python to PATH” during installation.
2. Double-click `run.bat`, or run it from Command Prompt.
3. Paste one or more JSON export paths. Separate multiple paths with semicolons.

### Linux

```bash
chmod +x run.sh
./run.sh
```

The launchers create a private `.venv`, check dependencies, and open the English wizard. Source exports are read-only.

## Telegram export

In Telegram Desktop, export a private chat as machine-readable JSON. Media downloads are optional: timing and message-type statistics still work when media files are absent. Give the wizard either individual JSON files or a directory containing them. Filenames such as `1.json` and `2.json` are supported, but internal timestamps always decide the final order.

The identity screen shows every detected sender ID, display name, and message count. Confirm the suggestion or assign IDs manually. This supports conversations continued from changed accounts and allows bots or additional senders to be excluded.

## Reports

Every run creates a new timestamped directory containing:

- `report.md`
- Markdown appendices for sessions, responses, text, emoji, and rule events
- CSV tables for every derived event
- `analysis.json`, a versioned machine-readable snapshot

The report may contain names and excerpts from the selected chat. Keep it private. For convenient reading, send the Markdown files to your Telegram Saved Messages.

## Settings

The wizard manages timezone, session threshold, output directory, Persian and English stopwords, and editable signal patterns. The default timezone is `Asia/Tehran`. Other IANA names and fixed offsets such as `+04:00` are accepted.

The default session boundary is six hours. Four-hour and twelve-hour sensitivity counts are always included. Advanced analysis can mark intervals where the export is incomplete or another messenger was used; affected timing is retained in raw results and flagged out of comparison-safe metrics.

## Development

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements-dev.txt
.venv/bin/python -m pytest
```

All tests use synthetic conversations. Do not add real exports or generated private reports to the repository.

## Troubleshooting

- If Python is not found, install Python 3.11+ and reopen the terminal.
- If package installation fails, check internet access and run the launcher again.
- If an export is rejected, verify that it is a one-to-one chat exported as JSON, not HTML, a group, or a channel.
- If Persian characters look incorrect, use a modern UTF-8 terminal such as Windows Terminal.

