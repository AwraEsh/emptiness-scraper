from emptiness_scraper.textstats import extract_emojis, normalize_text, tokenize


def test_persian_and_english_normalization():
    assert normalize_text("  كی  HELLO\u200cWorld  ") == "کی hello world"


def test_tokenize_handles_bilingual_text():
    assert tokenize("Hello دنیا! 123") == ["hello", "دنیا", "123"]


def test_emoji_sequences_remain_whole():
    assert extract_emojis("Hi 👩🏽‍💻! ❤️") == ["👩🏽‍💻", "❤️"]
