"""画面上部のメニュー。表示中の画面だけを描画し、切り替えたときに学習履歴を保存する（R-03b）。"""

from __future__ import annotations

from enum import StrEnum

import streamlit as st

from english_app.ui.state import flush_progress


class Page(StrEnum):
    HOME = "home"
    QUIZ = "quiz"
    DICTATION = "dictation"
    LISTENING = "listening"
    SPEAKING = "speaking"
    SHADOWING = "shadowing"
    DICTIONARY = "dictionary"
    RECORD = "record"


PAGE_LABELS: dict[Page, str] = {
    Page.HOME: "🏠 今日",
    Page.QUIZ: "📝 クイズ",
    Page.DICTATION: "✍️ 書き取り",
    Page.LISTENING: "🎧 聞き流し",
    Page.SPEAKING: "🗣 発音",
    Page.SHADOWING: "🔁 シャドーイング",
    Page.DICTIONARY: "📚 辞書",
    Page.RECORD: "📊 記録",
}

_PAGE_KEY = "page"
_LAST_PAGE_KEY = "last_page"


def render_navigation() -> Page:
    st.session_state.setdefault(_PAGE_KEY, Page.HOME.value)
    st.session_state.setdefault(_LAST_PAGE_KEY, Page.HOME.value)
    st.pills(
        "メニュー",
        [page.value for page in Page],
        format_func=lambda value: PAGE_LABELS[Page(value)],
        key=_PAGE_KEY,
        on_change=_on_page_change,
        label_visibility="collapsed",
    )
    return Page(st.session_state[_PAGE_KEY])


def go_to(page: Page) -> None:
    """ボタンの on_click から呼ぶ。メニューを描画した後に値を変えると Streamlit がエラーにするため。"""
    st.session_state[_PAGE_KEY] = page.value
    _on_page_change()


def _on_page_change() -> None:
    if st.session_state.get(_PAGE_KEY) is None:
        # 選択中のメニューをもう一度タップすると選択が外れるので、元の画面に戻す
        st.session_state[_PAGE_KEY] = st.session_state[_LAST_PAGE_KEY]
        return
    st.session_state[_LAST_PAGE_KEY] = st.session_state[_PAGE_KEY]
    flush_progress()
