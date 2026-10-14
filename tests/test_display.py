import unicodedata

from emptiness_scraper.display import display_text, markdown_parser


def test_terminal_detection_and_explicit_overrides():
    from emptiness_scraper.display import resolve_rendering
    assert resolve_rendering("auto", {"VTE_VERSION": "8200"}) == ("native", "VTE / GNOME-compatible terminal")
    assert resolve_rendering("auto", {}) == ("native", "Unknown terminal")
    assert resolve_rendering("compatibility", {"VTE_VERSION": "8200"})[0] == "compatibility"


def test_rendering_mode_switch_has_no_stale_cached_strings():
    from emptiness_scraper.display import configure_rendering
    try:
        configure_rendering("compatibility", {})
        assert display_text("سلام") != "سلام"
        assert "👩🏽‍💻" in display_text("سلام 👩🏽‍💻")
        configure_rendering("native", {})
        assert display_text("سلام") == "سلام"
    finally:
        configure_rendering("native", {})


def test_native_persian_is_not_reversed_or_replaced_by_presentation_forms():
    source = "Example سلام file123.json"
    rendered = display_text(source)
    assert source == "Example سلام file123.json"
    assert "Example" in rendered and "file123.json" in rendered
    assert rendered == source
    assert not any("FORM" in unicodedata.name(c, "") for c in rendered)


def test_native_multiline_preserves_sentence_order_and_half_spaces():
    source = "سلام دنیا، امروز چطور هستید؟\nExample می‌روم 👩🏽‍💻 123"
    assert display_text(source) == source


def test_actual_markdown_content_keeps_logical_persian_order():
    from textual.widgets._markdown import MarkdownBlock
    from textual.widgets import Markdown
    tokens = markdown_parser().parse("| Excerpt | Count |\n| --- | --- |\n| سلام دنیا | 12 |")
    inline = next(token for token in tokens if token.type == "inline" and any(child.content == "سلام دنیا" for child in token.children or []))
    block = MarkdownBlock(Markdown(), inline)
    assert block._token_to_content(inline).plain == "سلام دنیا"


def test_controls_cannot_create_extra_rows_or_escape_sequences():
    assert display_text("one\r\ntwo\t\x1b[31m", single_line=True) == "one two [31m"
    assert display_text("سلام\u2067test\u2069")
    assert display_text("English 👩🏽‍💻") == "English 👩🏽‍💻"
    assert "👩🏽‍💻" in display_text("سلام 👩🏽‍💻")


def test_markdown_keeps_structure_and_shapes_only_content():
    tokens = markdown_parser().parse("| Name | Count |\n| --- | --- |\n| سلام | 12 |\n\n- **سلام** [file](example.md)")
    assert any(token.type == "table_open" for token in tokens)
    children = [child for token in tokens for child in (token.children or [])]
    assert any(child.content == display_text("سلام") for child in children)
    assert next(child for child in children if child.type == "link_open").attrGet("href") == "example.md"
