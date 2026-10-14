from __future__ import annotations

import re
import unicodedata

import regex


_TRANSLATION = str.maketrans({"ي": "ی", "ى": "ی", "ك": "ک", "ۀ": "ه", "ة": "ه"})
_TOKEN = re.compile(r"[\w]+", re.UNICODE)
_GRAPHEMES = regex.compile(r"\X")
_EMOJI_COMPONENT = regex.compile(r"\p{Extended_Pictographic}|\p{Emoji_Presentation}|\p{Regional_Indicator}|\u20E3")


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).translate(_TRANSLATION).casefold()
    value = re.sub(r"[\u0640\u064b-\u065f\u0670]", "", value)
    value = value.replace("\u200c", " ").replace("\u200d", " ")
    return " ".join(value.split())


def tokenize(value: str) -> list[str]:
    return _TOKEN.findall(normalize_text(value))


def raw_tokens(value: str) -> list[str]:
    return _TOKEN.findall(unicodedata.normalize("NFKC", value))


def extract_emojis(value: str) -> list[str]:
    return [
        cluster for cluster in _GRAPHEMES.findall(value)
        if _EMOJI_COMPONENT.search(cluster)
    ]
