from emptiness_scraper.app import BANNER, CREATOR_NOTE, about_text, parse_path_input


def test_about_text_contains_product_and_author():
    text = about_text()
    assert "Emptiness Scraper" in text
    assert "@AwraEsh" in text
    assert "@Ou_Rash" in text


def test_startup_branding_contains_ascii_banner_and_creator_note():
    assert "Emptiness Scraper" in BANNER
    assert "@AwraEsh" in CREATOR_NOTE
    assert "i made this outa heart so. yea enjoy!" in CREATOR_NOTE


def test_path_input_accepts_quoted_semicolon_separated_paths():
    assert parse_path_input('"C:\\Chat One\\1.json"; /tmp/2.json') == [
        "C:\\Chat One\\1.json",
        "/tmp/2.json",
    ]
