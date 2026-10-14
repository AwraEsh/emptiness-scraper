import os
import ast
import shutil
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).parents[1]


@pytest.mark.skipif(os.name == "nt", reason="run.sh is validated on Unix runners")
def test_linux_launcher_has_valid_shell_syntax():
    result = subprocess.run(["bash", "-n", str(ROOT / "run.sh")], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr


def prepare_launcher_directory(directory):
    for name in ("run.sh", "run.bat", "requirements.txt"):
        shutil.copy2(ROOT / name, directory / name)
    shutil.copytree(ROOT / "emptiness_scraper", directory / "emptiness_scraper", ignore=shutil.ignore_patterns("__pycache__"))


@pytest.mark.skipif(os.name != "nt", reason="The Windows launcher runs on Windows")
def test_windows_launcher_creates_environment_and_reuses_it_offline(tmp_path):
    prepare_launcher_directory(tmp_path)
    environment = os.environ.copy()
    environment["EMPTYNESS_SCRAPER_SMOKE"] = "1"
    environment["PYTHONUTF8"] = "1"
    for attempt in range(2):
        if attempt:
            environment["PIP_INDEX_URL"] = "http://127.0.0.1:9/simple"
            environment["PIP_RETRIES"] = "0"
        result = subprocess.run(["cmd", "/c", "run.bat"], cwd=tmp_path, env=environment, capture_output=True, text=True, encoding="utf-8", timeout=240)
        assert result.returncode == 0, result.stdout + result.stderr
        assert "Emptiness Scraper" in result.stdout
    assert (tmp_path / ".venv" / "Scripts" / "python.exe").exists()


@pytest.mark.skipif(os.name == "nt", reason="The Unix launcher runs on Unix")
def test_linux_launcher_reuses_installed_dependencies_without_network(tmp_path):
    prepare_launcher_directory(tmp_path)
    (tmp_path / ".venv").symlink_to(sys.prefix, target_is_directory=True)
    environment = os.environ.copy()
    environment.update({"EMPTYNESS_SCRAPER_SMOKE": "1", "PIP_INDEX_URL": "http://127.0.0.1:9/simple", "PIP_RETRIES": "0"})
    result = subprocess.run(["bash", "run.sh"], cwd=tmp_path, env=environment, capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Emptiness Scraper" in result.stdout


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


def test_all_modules_parse_as_python_311():
    for path in (ROOT / "emptiness_scraper").glob("*.py"):
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path), feature_version=(3, 11))
