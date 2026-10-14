import unicodedata

from emptiness_scraper.display import display_text, markdown_parser


def test_persian_is_shaped_without_changing_latin_or_source():
    source = "Example سلام file123.json"
    rendered = display_text(source)
    assert source == "Example سلام file123.json"
    assert "Example" in rendered and "file123.json" in rendered
    assert rendered != source
    assert any("ARABIC LETTER" in unicodedata.name(c, "") and "FORM" in unicodedata.name(c, "") for c in rendered)


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
