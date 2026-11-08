"""Streamlit がコード変更時に english_app を読み直しても、学習データの扱いが壊れないことの確認。

Streamlit は変更を検知すると、監視中のモジュールをすべて sys.modules から外して読み直す。
同じことを別プロセスで再現し、他のテストのモジュールの状態を汚さないようにする。
"""

import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SUBPROCESS_TIMEOUT_SECONDS = 60

UNLOAD_MODULES = """
import sys

for name in [name for name in sys.modules if name == "english_app" or name.startswith("english_app.")]:
    del sys.modules[name]
"""

CONTENT_SCRIPT = (
    """
import english_app.ui.state as state

state.load_content()
"""
    + UNLOAD_MODULES
    + """
import english_app.ui.state as reloaded_state
from english_app.explanations import item_audio_text

for item in reloaded_state.load_content().items_by_id.values():
    item_audio_text(item)
print("ok")
"""
)

GRADE_SCRIPT = (
    """
from datetime import date

from english_app.progress import Progress

progress = Progress()
"""
    + UNLOAD_MODULES
    + """
from english_app.srs import Grade

today = date(2026, 11, 8)
state = progress.record_answer("quiz:vocab-001", Grade.AGAIN, today, 5.0)
assert (state.lapses, state.correct, state.total) == (1, 0, 1), state
assert progress.stats_for(today).correct == 0
print("ok")
"""
)


def _run_python(script: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", script],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        timeout=SUBPROCESS_TIMEOUT_SECONDS,
        check=False,
    )


def test_content_still_matches_classes_after_module_reload():
    completed = _run_python(CONTENT_SCRIPT)
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip().endswith("ok")


def test_wrong_answer_graded_with_reloaded_enum_is_still_wrong():
    completed = _run_python(GRADE_SCRIPT)
    assert completed.returncode == 0, completed.stderr
    assert completed.stdout.strip().endswith("ok")
