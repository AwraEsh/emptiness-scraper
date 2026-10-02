import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).parents[1]


def test_linux_launcher_has_valid_shell_syntax():
    result = subprocess.run(["bash", "-n", str(ROOT / "run.sh")], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def test_windows_launcher_creates_and_reuses_virtual_environment():
    text = (ROOT / "run.bat").read_text(encoding="utf-8")
    assert "py -3" in text
    assert ".venv" in text
    assert "requirements.txt" in text
    assert "emptiness_scraper" in text
    assert "%errorlevel%" not in text.lower()


def test_module_smoke_mode_starts_without_prompting():
    environment = os.environ.copy()
    environment["EMPTYNESS_SCRAPER_SMOKE"] = "1"
    result = subprocess.run(
        [sys.executable, "-m", "emptiness_scraper"],
        cwd=ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0
    assert "Emptiness Scraper" in result.stdout
    assert "this tool is made by @AwraEsh" in result.stdout
    assert "| ____|_ __ ___  _ __ | |_(_)_ __   ___  ___ ___   / ___|  ___ _ __ __ _ _ __   ___ _ __" in result.stdout


def test_source_avoids_python_312_only_fstring_expression():
    source = (ROOT / "emptiness_scraper" / "reporting.py").read_text(encoding="utf-8")
    assert "{'\\n\\n'.join" not in source
