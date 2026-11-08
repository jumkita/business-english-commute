"""🔁 シャドーイング（FR-11）。英語の音声だけを聞いて聞こえたとおりに言い、正しく言えたかを音声認識で確かめる。

聞き取りの確認が目的のため、英文は話し終えるまで表示せず、日本語訳は出さない。
"""

from __future__ import annotations

import streamlit as st

from english_app.dictation import DictationItem
from english_app.ui.components import speak_button
from english_app.ui.diff_view import render_verdict
from english_app.ui.formatting import escape_markdown
from english_app.ui.speech_practice import (
    SpeechAttempt,
    choose_practice_item,
    listen_and_compare,
    render_attempt_details,
    render_next_item_button,
)
from english_app.ui.state import AppContext

UNSUPPORTED_HINT = "音声を聞いて声に出したあと、「英文を見る」で答えを確かめてください。"

_KEY_PREFIX = "shadowing"
_REVEALED_KEY = "shadowing_revealed_item_id"


def render(context: AppContext) -> None:
    st.subheader("🔁 シャドーイング", anchor=False)
    st.caption("英語の音声だけを聞いて、聞こえたとおりに声に出します。英文は話し終えてから表示し、日本語訳は出しません。")
    item, item_ids = choose_practice_item(context, _KEY_PREFIX)
    if st.session_state.get(_REVEALED_KEY) != item.item_id:
        # 別の文に移ったら記録を消す。残したままだと、同じ文がまた出たときに最初から英文が見えてしまう
        st.session_state.pop(_REVEALED_KEY, None)

    st.markdown("① 音声を聞く")
    speak_button(item.text)
    st.markdown("② ボタンを押して、聞こえたとおりに言う")
    attempt = listen_and_compare(
        item.text, key=f"shadowing_recognizer_{item.item_id}", unsupported_hint=UNSUPPORTED_HINT
    )
    if attempt is not None:
        _render_attempt(item, attempt)
    elif _REVEALED_KEY in st.session_state:
        _render_answer(item)
    else:
        st.button("👀 英文を見る", type="tertiary", on_click=_reveal, args=(item.item_id,))
    render_next_item_button(item_ids, _KEY_PREFIX)


def _render_attempt(item: DictationItem, attempt: SpeechAttempt) -> None:
    render_verdict(attempt.result)
    render_attempt_details(attempt)
    _render_answer(item)


def _render_answer(item: DictationItem) -> None:
    st.markdown(f"**英文**: {escape_markdown(item.text)}")


def _reveal(item_id: str) -> None:
    st.session_state[_REVEALED_KEY] = item_id
