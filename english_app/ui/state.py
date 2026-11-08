"""Streamlit のセッション状態（ログイン・学習履歴・保存）をまとめて扱う。

Gist への保存は 1 回あたり 1 秒前後かかるため、数問ごと・セッション終了時・タブ切替時にまとめて保存する（R-03b）。
"""

from __future__ import annotations

import functools
import os
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import TypeVar, assert_never

import streamlit as st

from english_app.clock import today_jst
from english_app.config import AppSettings, StorageMode, decide_storage_mode, load_settings, passcode_matches
from english_app.content import ContentError, ContentLibrary, load_library, validate_library
from english_app.progress import Progress, ProgressFormatError
from english_app.progress_store import (
    FileProgressStore,
    GistProgressStore,
    MemoryProgressStore,
    ProgressStore,
    ProgressStoreError,
)
from english_app.srs import Grade

SAVE_EVERY_ANSWERS = 5
LOGIN_QUERY_KEY = "key"

_AUTHENTICATED_KEY = "authenticated"
_PROGRESS_KEY = "progress"
_STORE_KEY = "progress_store"
_STORAGE_MODE_KEY = "storage_mode"
_LOAD_ERROR_KEY = "progress_load_error"
_SAVE_ERROR_KEY = "progress_save_error"
_UNSAVED_CHANGES_KEY = "unsaved_changes"

RunT = TypeVar("RunT")


@dataclass(frozen=True)
class AppContext:
    library: ContentLibrary
    settings: AppSettings
    progress: Progress
    storage_mode: StorageMode
    today: date
    load_error: str | None
    save_error: str | None


def get_secret(key: str) -> str | None:
    """Streamlit の Secrets を優先し、なければ環境変数を見る。空文字は未設定として扱う。"""
    try:
        value = st.secrets.get(key)
    except FileNotFoundError:
        value = None
    if value is None:
        value = os.environ.get(key)
    if value is None or str(value).strip() == "":
        return None
    return str(value).strip()


# st.cache_resource は使わない。Streamlit はコード変更時に english_app のモジュールを読み直すが、
# st.cache_resource の中身は残るため、古いクラスのインスタンスが新しいクラスとの match に一致しなくなる。
@functools.cache
def load_content() -> ContentLibrary:
    library = load_library()
    errors = validate_library(library)
    if errors:
        raise ContentError("学習データに誤りがあります:\n" + "\n".join(errors))
    return library


def get_context() -> AppContext:
    settings = load_settings(get_secret)
    mode = decide_storage_mode(settings, _is_authenticated(settings))
    if st.session_state.get(_STORAGE_MODE_KEY) != mode or _PROGRESS_KEY not in st.session_state:
        _load_progress(settings, mode)
    elif not isinstance(st.session_state[_PROGRESS_KEY], Progress):
        _rebuild_objects_from_previous_code(settings, mode)
    return AppContext(
        library=load_content(),
        settings=settings,
        progress=st.session_state[_PROGRESS_KEY],
        storage_mode=mode,
        today=today_jst(),
        load_error=st.session_state.get(_LOAD_ERROR_KEY),
        save_error=st.session_state.get(_SAVE_ERROR_KEY),
    )


def try_login(settings: AppSettings, passcode: str) -> bool:
    if not passcode_matches(settings, passcode):
        return False
    st.session_state[_AUTHENTICATED_KEY] = True
    return True


def current_run(key: str, run_type: type[RunT], mode_label: str) -> RunT | None:
    """セッションに保存した途中経過を返す。コード更新前のクラスのまま残っていれば終了扱いにする。"""
    run = st.session_state.get(key)
    if run is None or isinstance(run, run_type):
        return run
    # 古い途中経過には古いクラスの問題データが入っており、今のコードの match に一致しない
    st.session_state.pop(key, None)
    st.toast(f"アプリが更新されたため、途中の{mode_label}を終了しました。回答済みの分は記録に反映されています。")
    return None


def reload_progress() -> None:
    """読み込みに失敗したときの再試行用。次の get_context() で読み直す。"""
    st.session_state.pop(_PROGRESS_KEY, None)


def record_answer(card_id: str, grade: Grade, elapsed_seconds: float) -> None:
    progress: Progress = st.session_state[_PROGRESS_KEY]
    progress.record_answer(card_id, grade, today_jst(), elapsed_seconds)
    _mark_changed()
    if st.session_state[_UNSAVED_CHANGES_KEY] >= SAVE_EVERY_ANSWERS:
        flush_progress()


def toggle_flag(item_id: str) -> None:
    progress: Progress = st.session_state[_PROGRESS_KEY]
    progress.toggle_flag(item_id)
    _mark_changed()


def flush_progress() -> None:
    """未保存の変更があれば保存する。失敗しても学習は続けられるよう、例外は画面表示用に記録するだけにする。"""
    if not st.session_state.get(_UNSAVED_CHANGES_KEY) or _PROGRESS_KEY not in st.session_state:
        return
    store: ProgressStore = st.session_state[_STORE_KEY]
    try:
        store.save(st.session_state[_PROGRESS_KEY].to_dict())
    except ProgressStoreError as error:
        st.session_state[_SAVE_ERROR_KEY] = f"{error}。次の保存のタイミングで再試行します。"
        return
    st.session_state[_UNSAVED_CHANGES_KEY] = 0
    st.session_state[_SAVE_ERROR_KEY] = None


def render_flag_button(context: AppContext, item_id: str, key: str) -> None:
    flagged = item_id in context.progress.flagged_item_ids
    label = "🚩 要確認を外す" if flagged else "🏳️ 内容が怪しい（要確認）"
    st.button(label, key=key, on_click=toggle_flag, args=(item_id,), width="stretch")


def _is_authenticated(settings: AppSettings) -> bool:
    if st.session_state.get(_AUTHENTICATED_KEY):
        return True
    if passcode_matches(settings, st.query_params.get(LOGIN_QUERY_KEY)):
        st.session_state[_AUTHENTICATED_KEY] = True
        return True
    return False


def _mark_changed() -> None:
    st.session_state[_UNSAVED_CHANGES_KEY] = st.session_state.get(_UNSAVED_CHANGES_KEY, 0) + 1


def _load_progress(settings: AppSettings, mode: StorageMode) -> None:
    load_error = None
    try:
        store = _create_store(settings, mode)
        progress = Progress.from_dict(store.load())
    except (ProgressStoreError, ProgressFormatError, ValueError) as error:
        # 読めなかった履歴を空の履歴で上書きしないよう、保存しないモードに切り替える
        load_error = f"学習履歴を読み込めませんでした（{error}）。履歴を上書きしないよう、この間の学習は保存しません。"
        store = MemoryProgressStore()
        progress = Progress()
    st.session_state[_STORE_KEY] = store
    st.session_state[_PROGRESS_KEY] = progress
    st.session_state[_STORAGE_MODE_KEY] = mode
    st.session_state[_LOAD_ERROR_KEY] = load_error
    st.session_state[_SAVE_ERROR_KEY] = None
    st.session_state[_UNSAVED_CHANGES_KEY] = 0


def _rebuild_objects_from_previous_code(settings: AppSettings, mode: StorageMode) -> None:
    """コード更新前のクラスのまま残った学習履歴と保存先を、今のクラスで作り直す。

    Streamlit はコードが変わるとモジュールを読み直すが、st.session_state の中身はそのまま残る。
    古いオブジェクトのメソッドは古いコードのまま動き、送出する例外も今の ProgressStoreError とは別のクラスになる。
    学習履歴と保存先は _load_progress で同時に作るため、学習履歴のクラスだけを見れば判定できる。
    """
    st.session_state[_PROGRESS_KEY] = Progress.from_dict(st.session_state[_PROGRESS_KEY].to_dict())
    if st.session_state.get(_LOAD_ERROR_KEY):
        # 読み込みに失敗していた履歴を空の履歴で上書きしないよう、保存しない状態を保つ
        st.session_state[_STORE_KEY] = MemoryProgressStore()
    else:
        st.session_state[_STORE_KEY] = _create_store(settings, mode)


def _create_store(settings: AppSettings, mode: StorageMode) -> ProgressStore:
    match mode:
        case StorageMode.GIST:
            return GistProgressStore(settings.gist_id or "", settings.github_token or "")
        case StorageMode.LOCAL_FILE:
            return FileProgressStore(Path(settings.progress_file or ""))
        case StorageMode.TRIAL:
            return MemoryProgressStore()
        case _:
            assert_never(mode)
