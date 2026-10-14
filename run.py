from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path


class StartupView:
    def __init__(self) -> None:
        self.active = sys.stdout.isatty() and os.environ.get("EMPTYNESS_SCRAPER_SMOKE") != "1"

    def __enter__(self):
        if self.active:
            if os.name == "nt":
                self.enable_windows_ansi()
            sys.stdout.write("\x1b[?1049h\x1b[?25l")
            sys.stdout.flush()
        return self

    def __exit__(self, *errors) -> None:
        if self.active:
            sys.stdout.write("\x1b[?25h\x1b[?1049l")
            sys.stdout.flush()

    @staticmethod
    def enable_windows_ansi() -> None:
        import ctypes
        from ctypes import wintypes

        kernel = ctypes.windll.kernel32
        kernel.GetStdHandle.restype = wintypes.HANDLE
        kernel.GetConsoleMode.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel.SetConsoleMode.argtypes = [wintypes.HANDLE, wintypes.DWORD]
        handle = kernel.GetStdHandle(-11)
        mode = wintypes.DWORD()
        if kernel.GetConsoleMode(handle, ctypes.byref(mode)):
            kernel.SetConsoleMode(handle, mode.value | 4)

    def run(self, command: list[str], stage: str) -> subprocess.CompletedProcess:
        with tempfile.TemporaryFile() as output:
            process = subprocess.Popen(command, stdout=output, stderr=subprocess.STDOUT)
            tick = 0
            try:
                while process.poll() is None:
                    if self.active:
                        spinner = "◐◓◑◒"[tick % 4]
                        sys.stdout.write(f"\x1b[H\x1b[2J\n  EMPTINESS / SCRAPER\n\n  {spinner}  {stage}\n\n  Preparing your local workspace.\n")
                        sys.stdout.flush()
                    tick += 1
                    time.sleep(0.12)
            except KeyboardInterrupt:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()
                raise
            size = output.seek(0, 2)
            output.seek(max(0, size - 6000))
            message = output.read().decode("utf-8", errors="replace")
        return subprocess.CompletedProcess(command, process.returncode, message)


def main() -> int:
    if sys.version_info < (3, 11):
        print("Python 3.11 or newer is required. Install it from python.org.", file=sys.stderr)
        return 1
    root = Path(__file__).resolve().parent
    os.chdir(root)
    python = root / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    environment = os.environ.copy()
    environment["PYTHONUTF8"] = "1"
    os.environ["PYTHONUTF8"] = "1"
    try:
        with StartupView() as view:
            if not python.is_file():
                result = view.run([sys.executable, "-m", "venv", str(root / ".venv")], "Creating the Python environment")
                if result.returncode:
                    raise RuntimeError("Could not create .venv. On Debian/Ubuntu install python3-venv.\n" + result.stdout)
            result = view.run([str(python), "-c", "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)"], "Checking Python compatibility")
            if result.returncode:
                raise RuntimeError("The existing .venv is incompatible. Rename it and run again with Python 3.11+.")
            check = [str(python), "-m", "pip", "install", "--no-index", "--dry-run", "--disable-pip-version-check", "--quiet", "-r", str(root / "requirements.txt")]
            result = view.run(check, "Checking installed dependencies offline")
            if result.returncode:
                result = view.run([str(python), "-m", "pip", "install", "--disable-pip-version-check", "-r", str(root / "requirements.txt")], "Installing required dependencies")
                if result.returncode:
                    raise RuntimeError("Dependency setup failed. Check internet access and try again.\n" + result.stdout)
        os.execve(str(python), [str(python), "-m", "emptiness_scraper"], environment)
    except KeyboardInterrupt:
        return 130
    except (OSError, RuntimeError) as error:
        print(str(error), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
