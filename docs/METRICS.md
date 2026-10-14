# Metric definitions

## Sessions and turns

A session is separated from the preceding session when the silence between two messages is greater than or equal to the selected threshold. The default is six hours. A turn contains consecutive messages by one participant until the other participant sends a message or the session ends.

## Responses

A response is the first message after the sender changes inside a session. Its latency starts at the previous participant’s last message, not their first message in the turn. Mean, median, trimmed mean, minimum, maximum, p75, p90, and p95 are reported.

## Restarts and gaps

A same-sender restart occurs when the participant who sent the final message before a session gap also sends the first message after it. An other-sender return changes participant across the gap. These categories describe message order only.

## Incomplete intervals

Messages remain in raw totals. Sessions, gaps, or responses overlapping a user-declared incomplete interval are marked as not comparison-safe. This prevents known missing communication opportunities from silently shaping trend claims.

## Text processing

English is case-folded. Arabic Yeh/Kaf variants are normalized to Persian forms, half-spaces are treated as token boundaries, and editable stopwords are removed from frequency tables. Emoji joined by zero-width joiners and skin-tone modifiers are counted as complete grapheme sequences.

Persian diacritics and tatweel are removed from normalized forms. Flags and keycap emoji remain complete sequences. Phrase tables use contiguous two-to-five-word sequences within a sentence; stopwords are not removed from the middle of phrases, and phrases consisting entirely of stopwords are omitted.

## Account aliases and reply targets

Confirmed aliases are a single sender for all timing metrics. Numeric IDs order messages within one export when timestamps are equal; equal timestamps across exports use the source namespace as a deterministic tie breaker and do not prove a real-world event order.

Reply targets are resolved in the same source namespace. Missing targets are counted as unresolved. This includes references to messages absent from the export or removed during conservative overlap deduplication.

## Periods and reactions

Calendar months include inactive months. Quarters use equal elapsed duration, with an exclusive upper boundary except for the final quarter. Sessions belong to the period in which they start; median session size/duration includes the full session even if it continues into another period.

Reaction totals measure reactions received on each participant's messages. CSV prefixes formula-like string cells with an apostrophe to keep spreadsheet applications from executing them; JSON preserves the unmodified content.

## Rule events

Greeting, goodbye, check-in, question, follow-up, revival, content-after-silence, and possible-callback events use documented deterministic rules. They are not semantic or psychological conclusions.

