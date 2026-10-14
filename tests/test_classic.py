import io
import json

from emptiness_scraper.classic import ClassicInterface
from emptiness_scraper.settings import AppSettings


def run_classic(tmp_path, answers):
    output = io.StringIO()
    interface = ClassicInterface(AppSettings(output_directory=str(tmp_path / "reports")), tmp_path / "settings.json", input_stream=io.StringIO(answers), output_stream=output)
    code = interface.run()
    return code, output.getvalue()


def test_classic_handles_bad_choices_and_exits_without_ansi(tmp_path):
    code, output = run_classic(tmp_path, "invalid\n5\n6\n")
    assert code == 0
    assert "Choose one of" in output
    assert "GitHub: @AwraEsh" in output
    assert "\x1b" not in output


def test_classic_analysis_confirms_mapping_and_preserves_source(tmp_path):
    source = tmp_path / "chat.json"
    source.write_text(json.dumps({"type": "personal_chat", "messages": [
        {"id": 1, "type": "message", "from_id": "a", "from": "Example A", "date_unixtime": "1767225600", "text": "Hello"},
        {"id": 2, "type": "message", "from_id": "b", "from": "Example B", "date_unixtime": "1767225660", "text": "سلام"},
    ]}), encoding="utf-8")
    before = source.read_bytes()
    code, output = run_classic(tmp_path, f"1\n{source}\n\ny\nn\n6\n")
    assert code == 0
    assert "Confirm this mapping" in output
    assert "Analysis complete" in output
    assert source.read_bytes() == before
    report = next((tmp_path / "reports").glob("*/analysis.json"))
    assert json.loads(report.read_text(encoding="utf-8"))["summary"]["message_count"] == 2


def test_classic_invalid_input_returns_to_menu_and_eof_exits(tmp_path):
    code, output = run_classic(tmp_path, "4\nmissing.json\n\n")
    assert code == 0
    assert "Error:" in output
    assert output.count("New Analysis") >= 2


def test_classic_settings_persist_and_reject_invalid_gap(tmp_path):
    code, output = run_classic(tmp_path, "3\n3\nnan\n8\nnative\n0\n6\n")
    assert code == 0
    settings = json.loads((tmp_path / "settings.json").read_text(encoding="utf-8"))
    assert settings["terminal_rendering"] == "native"
    assert settings["session_gap_hours"] == 6
    assert "Error:" in output


def test_classic_report_reader_paginates_without_fullscreen(tmp_path):
    folder = tmp_path / "reports" / "emptiness-scraper-synthetic"
    folder.mkdir(parents=True)
    (folder / "analysis.json").write_text("{}", encoding="utf-8")
    (folder / "report.md").write_text("\n".join(f"Synthetic line {i}" for i in range(100)), encoding="utf-8")
    code, output = run_classic(tmp_path, "2\n1\n1\nn\np\n0\n6\n")
    assert code == 0
    assert "PAGE 2" in output and output.count("PAGE 1") == 2
    assert "\x1b" not in output


def test_classic_custom_alias_mapping_excludes_additional_sender(tmp_path):
    from emptiness_scraper.parser import load_exports
    source = tmp_path / "aliases.json"
    source.write_text(json.dumps({"type": "personal_chat", "messages": [
        {"id": i, "type": "message", "from_id": sender, "from": "Example " + sender, "date_unixtime": str(1767225600 + i), "text": "Synthetic"}
        for i, sender in enumerate(["a", "alias", "b", "extra"], 1)
    ]}), encoding="utf-8")
    output = io.StringIO()
    interface = ClassicInterface(AppSettings(), input_stream=io.StringIO("n\na,alias\nb\nSide A\nSide B\ny\n"), output_stream=output)
    sides = interface.participants(load_exports([str(source)]))
    assert sides[0].ids == {"a", "alias"}
    assert sides[1].ids == {"b"}
    assert "Excluded: extra" in output.getvalue()
