import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.skipif(os.name == "nt", reason="Unix PTY integration; Windows uses Pilot and launcher tests")
def test_real_terminal_uses_alternate_screen_and_restores_it_on_quit(tmp_path):
    import fcntl
    import pty
    import select
    import struct
    import termios
    import time

    master, slave = pty.openpty()
    fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 36, 120, 0, 0))
    environment = os.environ.copy()
    environment.update({"TERM": "xterm-256color", "PYTHONUTF8": "1", "XDG_CONFIG_HOME": str(tmp_path)})
    environment.pop("EMPTYNESS_SCRAPER_SMOKE", None)
    process = subprocess.Popen([sys.executable, "-m", "emptiness_scraper"], cwd=Path(__file__).parents[1], stdin=slave, stdout=slave, stderr=slave, env=environment, start_new_session=True)
    os.close(slave)
    captured = bytearray()

    def collect_until(marker):
        deadline = time.monotonic() + 15
        while marker not in captured and time.monotonic() < deadline:
            readable, _, _ = select.select([master], [], [], 0.1)
            if readable:
                try:
                    captured.extend(os.read(master, 65536))
                except OSError:
                    break
        assert marker in captured, bytes(captured[-3000:]).decode("utf-8", errors="replace")

    try:
        collect_until(b"Choose your interface")
        os.write(master, b"1\n")
        collect_until(b"A quiet workspace")
        assert b"\x1b[?1049h" in captured
        os.write(master, b"\x1bOQ")
        collect_until(b"Bring your conversation")
        os.write(master, b"\x11")
        collect_until(b"Leave Emptiness Scraper?")
        os.write(master, b"\t\r")
        collect_until(b"\x1b[?1049l")
        assert process.wait(timeout=10) == 0
    finally:
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()
        os.close(master)
