import subprocess
import sys


def test_pathological_custom_rule_returns_error_instead_of_freezing_ui():
    code = """
from datetime import UTC, datetime
from emptiness_scraper.models import Message
from emptiness_scraper.signals import detect_text_signals
message = Message('synthetic.json', 1, datetime.now(UTC), 'a', 'Example', 'a' * 10000 + '!')
try:
    detect_text_signals(message, {'custom': [r'(a+)+$']})
except ValueError as error:
    assert 'time limit' in str(error)
    print('handled')
"""
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, timeout=3)
    assert result.returncode == 0, result.stderr
    assert "handled" in result.stdout
