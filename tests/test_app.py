"""Streamlit の AppTest で画面を通しで動かすテスト（ブラウザ側の音声機能は対象外）。"""

import re
from datetime import date
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from english_app import config
from english_app.config import StorageMode
from english_app.content import load_library
from english_app.dictation import DictationItem, build_dictation_items
from english_app.progress import Progress
from english_app.srs import Grade
from english_app.ui import speech_practice
from english_app.ui import state as state_module
from english_app.ui.navigation import Page

APP_PATH = Path(__file__).resolve().parents[1] / "app.py"
APP_TIMEOUT_SECONDS = 30
PASSCODE = "test-passcode"
PRACTICE_ITEM_KEYS = {Page.SPEAKING: "speaking_item_id", Page.SHADOWING: "shadowing_item_id"}
# 画面では英文中の記号がエスケープされるため、記号を含まない英文で表示の有無を確かめる
PLAIN_SENTENCE = re.compile(r"[A-Za-z ,.?]+")


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


def _plain_practice_item() -> DictationItem:
    return next(item for item in build_dictation_items(load_library()) if PLAIN_SENTENCE.fullmatch(item.text))


def _open_practice_page(monkeypatch, page: Page, item: DictationItem, recognized: dict | None) -> AppTest:
    """音声認識の部品を、決まった結果（未入力なら None）を返すものに差し替えて画面を開く。"""
    monkeypatch.setattr(speech_practice, "speech_recognizer", lambda key: recognized)
    app = _app()
    app.session_state["page"] = page.value
    app.session_state[PRACTICE_ITEM_KEYS[page]] = item.item_id
    return app.run()


def _visible_text(app: AppTest) -> str:
    elements = [*app.subheader, *app.markdown, *app.caption, *app.success, *app.warning, *app.error]
    labels = [*(button.label for button in app.button), *(expander.label for expander in app.expander)]
    return "\n".join([*(str(element.value) for element in elements), *labels])


def _shows_answer(app: AppTest, item: DictationItem) -> bool:
    return any(markdown.value == f"**英文**: {item.text}" for markdown in app.markdown)


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


def test_speaking_shows_english_meaning_and_explanation(monkeypatch):
    item = _plain_practice_item()
    app = _open_practice_page(monkeypatch, Page.SPEAKING, item, recognized={"transcript": item.text})
    assert not app.exception
    text = _visible_text(app)
    assert item.text in text
    assert item.meaning_ja in text
    assert any(expander.label == "解説" for expander in app.expander)
    assert any(markdown.value == "**一致率**: 100%" for markdown in app.markdown)


def test_speaking_suggests_recording_when_speech_recognition_is_unsupported(monkeypatch):
    item = _plain_practice_item()
    app = _open_practice_page(monkeypatch, Page.SPEAKING, item, recognized={"error": "unsupported"})
    assert not app.exception
    assert any("録音して聞き比べ" in warning.value for warning in app.warning)


def test_shadowing_shows_neither_english_nor_japanese_before_speaking(monkeypatch):
    item = _plain_practice_item()
    app = _open_practice_page(monkeypatch, Page.SHADOWING, item, recognized=None)
    assert not app.exception
    text = _visible_text(app)
    assert item.text not in text
    assert item.meaning_ja not in text
    assert item.source_label not in text
    assert any(button.label == "👀 英文を見る" for button in app.button)


def test_shadowing_judges_speech_and_reveals_english_only(monkeypatch):
    item = _plain_practice_item()
    app = _open_practice_page(monkeypatch, Page.SHADOWING, item, recognized={"transcript": item.text})
    assert not app.exception
    assert any("正解" in success.value for success in app.success)
    assert _shows_answer(app, item)
    assert item.meaning_ja not in _visible_text(app)


def test_shadowing_marks_partly_repeated_sentence_as_incorrect(monkeypatch):
    item = _plain_practice_item()
    first_word = item.text.split()[0]
    app = _open_practice_page(monkeypatch, Page.SHADOWING, item, recognized={"transcript": first_word})
    assert not app.exception
    assert any("不正解" in error.value for error in app.error)
    assert _shows_answer(app, item)


@pytest.mark.parametrize(
    ("error", "message"),
    [("not-allowed", "マイクの使用が許可されていません"), ("unsupported", "「英文を見る」")],
)
def test_shadowing_keeps_english_hidden_when_speech_recognition_fails(monkeypatch, error, message):
    item = _plain_practice_item()
    app = _open_practice_page(monkeypatch, Page.SHADOWING, item, recognized={"error": error})
    assert not app.exception
    assert any(message in warning.value for warning in app.warning)
    assert item.text not in _visible_text(app)


def test_shadowing_reveal_does_not_carry_over_to_other_sentences(monkeypatch):
    item = _plain_practice_item()
    app = _open_practice_page(monkeypatch, Page.SHADOWING, item, recognized=None)
    _button(app, "👀 英文を見る").click().run()
    assert _shows_answer(app, item)
    assert item.meaning_ja not in _visible_text(app)

    _button(app, "次の文").click().run()
    assert not app.exception
    assert app.session_state["shadowing_item_id"] != item.item_id
    assert any(button.label == "👀 英文を見る" for button in app.button)

    # 同じ文がまた出題されたときも、最初から英文は見せない
    app.session_state["shadowing_item_id"] = item.item_id
    app.run()
    assert not _shows_answer(app, item)
