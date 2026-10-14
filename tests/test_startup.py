import os
from pathlib import Path
import subprocess
import sys


def launch(answers, tmp_path):
    env = os.environ.copy()
    env.pop("EMPTYNESS_SCRAPER_SMOKE", None)
    env.update({"XDG_CONFIG_HOME": str(tmp_path), "PYTHONUTF8": "1"})
    return subprocess.run([sys.executable, "-m", "emptiness_scraper"], input=answers, capture_output=True, text=True, encoding="utf-8", cwd=Path(__file__).parents[1], env=env, timeout=15)


def test_startup_describes_both_interfaces_and_dispatches_classic(tmp_path):
    result = launch("2\n5\n6\n", tmp_path)
    assert result.returncode == 0, result.stderr
    assert "Full-screen" in result.stdout and "Classic text" in result.stdout
    assert "CLASSIC TEXT" in result.stdout and "GitHub: @AwraEsh" in result.stdout
    assert "\x1b[?1049h" not in result.stdout


def test_unavailable_fullscreen_offers_classic_instead_of_crashing(tmp_path):
    result = launch("1\n2\n6\n", tmp_path)
    assert result.returncode == 0, result.stderr
    assert "interactive terminal" in result.stdout
    assert "CLASSIC TEXT" in result.stdout


def test_startup_invalid_choice_eof_and_return_to_chooser(tmp_path):
    result = launch("bad\n2\n0\n0\n", tmp_path)
    assert result.returncode == 0
    assert result.stdout.count("Choose your interface") == 3
    assert launch("", tmp_path).returncode == 0
