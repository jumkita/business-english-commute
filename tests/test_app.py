"""Streamlit の AppTest で画面を通しで動かすテスト（ブラウザ側の音声機能は対象外）。"""

from datetime import date
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from english_app import config
from english_app.config import StorageMode
from english_app.progress import Progress
from english_app.srs import Grade
from english_app.ui import state as state_module
from english_app.ui.navigation import Page

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
APP_TIMEOUT_SECONDS = 30
PASSCODE = "test-passcode"


class FakeGistStore:
    saved: list[dict] = []

    def __init__(self, gist_id: str, token: str) -> None:
        self.gist_id = gist_id

    def load(self) -> dict:
        return {}

    def save(self, data) -> None:
        FakeGistStore.saved.append(dict(data))


class ProgressLeftByPreviousCode:
    """コード更新前のクラスのまま session_state に残った学習履歴の代わり。to_dict だけを持つ。"""

    def __init__(self, data: dict) -> None:
        self._data = data

    def to_dict(self) -> dict:
        return self._data


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch):
    for key in (config.PASSCODE_KEY, config.GIST_ID_KEY, config.GITHUB_TOKEN_KEY, config.PROGRESS_FILE_KEY):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setattr(state_module, "GistProgressStore", FakeGistStore)
    FakeGistStore.saved = []


def _app(secrets: dict | None = None) -> AppTest:
    app = AppTest.from_file(str(APP_PATH), default_timeout=APP_TIMEOUT_SECONDS)
    # 開発者の ~/.streamlit/secrets.toml を読まないよう、常にテスト用の Secrets に差し替える
    app.secrets["TEST"] = "1"
    for key, value in (secrets or {}).items():
        app.secrets[key] = value
    return app


def _button(app: AppTest, label_prefix: str):
    return next(button for button in app.button if button.label.startswith(label_prefix))


def _choice_buttons(app: AppTest):
    return [button for button in app.button if button.key and button.key.startswith("quiz_choice_")]


def test_home_renders_in_trial_mode():
    app = _app().run()
    assert not app.exception
    assert [metric.label for metric in app.metric] == ["今日の復習", "連続学習", "今日の学習"]
    assert any("お試しモード" in caption.value for caption in app.caption)


@pytest.mark.parametrize("page", list(Page))
def test_every_page_renders(page):
    app = _app()
    app.session_state["page"] = page.value
    app.run()
    assert not app.exception


def test_quick_quiz_answers_and_moves_to_next_question():
    app = _app().run()
    _button(app, "📝 5分クイズ").click().run()
    assert not app.exception
    choices = _choice_buttons(app)
    assert 2 <= len(choices) <= 4

    choices[0].click().run()
    assert not app.exception
    assert not _choice_buttons(app)
    if app.success:
        _button(app, "簡単").click().run()
    else:
        _button(app, "次へ").click().run()
    assert not app.exception
    assert any("2 問目" in caption.value for caption in app.caption)


def test_quiz_can_be_stopped_and_shows_result():
    app = _app().run()
    _button(app, "📝 5分クイズ").click().run()
    _button(app, "⏹ ここで終了").click().run()
    assert not app.exception
    assert any("おつかれさまでした" in header.value for header in app.subheader)


def test_dictation_checks_typed_answer():
    app = _app().run()
    _button(app, "✍️ 5分書き取り").click().run()
    assert not app.exception
    app.text_input[0].input("this is a test answer")
    _button(app, "答え合わせ").click().run()
    assert not app.exception
    assert app.error or app.warning or app.success
    assert any(button.label.startswith("次へ") for button in app.button)


def test_login_with_passcode_switches_to_gist():
    secrets = {"APP_PASSCODE": PASSCODE, "GIST_ID": "abc123", "GITHUB_TOKEN": "dummy-token"}
    app = _app(secrets).run()
    assert any("パスコード" in expander.label for expander in app.expander)

    app.text_input(key="login_passcode").input("wrong")
    _button(app, "ログイン").click().run()
    assert any("パスコードが違います" in error.value for error in app.error)

    app.text_input(key="login_passcode").input(PASSCODE)
    _button(app, "ログイン").click().run()
    assert not app.exception
    assert not any("パスコード" in expander.label for expander in app.expander)
    assert any("GitHub Gist に保存" in caption.value for caption in app.caption)


def test_login_with_query_parameter():
    secrets = {"APP_PASSCODE": PASSCODE, "GIST_ID": "abc123", "GITHUB_TOKEN": "dummy-token"}
    app = _app(secrets)
    app.query_params["key"] = PASSCODE
    app.run()
    assert not app.exception
    assert not any("パスコード" in expander.label for expander in app.expander)


def test_gist_without_passcode_disables_saving():
    app = _app({"GIST_ID": "abc123", "GITHUB_TOKEN": "dummy-token"}).run()
    assert any("APP_PASSCODE が未設定" in error.value for error in app.error)


def test_progress_left_by_previous_code_is_rebuilt_with_current_class():
    previous = Progress()
    previous.record_answer("quiz:vocab-001", Grade.AGAIN, date(2026, 11, 8), 5.0)
    app = _app()
    app.session_state["storage_mode"] = StorageMode.TRIAL.value
    app.session_state["progress"] = ProgressLeftByPreviousCode(previous.to_dict())
    app.session_state["progress_store"] = object()
    app.session_state["progress_load_error"] = None
    app.session_state["unsaved_changes"] = 0
    app.run()
    assert not app.exception
    rebuilt = app.session_state["progress"]
    assert isinstance(rebuilt, Progress)
    assert rebuilt.cards["quiz:vocab-001"].lapses == 1


@pytest.mark.parametrize(("page", "run_key"), [(Page.QUIZ, "quiz_run"), (Page.DICTATION, "dictation_run")])
def test_run_left_by_previous_code_is_discarded(page, run_key):
    app = _app()
    app.session_state["page"] = page.value
    app.session_state[run_key] = object()
    app.run()
    assert not app.exception
    assert run_key not in app.session_state
    assert any(button.label == "▶ スタート" for button in app.button)
