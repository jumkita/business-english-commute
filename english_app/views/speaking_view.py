"""🗣 発音（FR-03）。英文と意味を見ながらお手本をまねして読み上げ、言い回しと発音を身につける。"""

from __future__ import annotations

import streamlit as st

from english_app.ui.components import speak_button
from english_app.ui.formatting import format_percent, prompt_html
from english_app.ui.speech_practice import (
    choose_practice_item,
    listen_and_compare,
    render_attempt_details,
    render_next_item_button,
)
from english_app.ui.state import AppContext

UNSUPPORTED_HINT = "下の「録音して聞き比べ」を使ってください。"

_KEY_PREFIX = "speaking"


def render(context: AppContext) -> None:
    st.subheader("🗣 発音", anchor=False)
    st.caption("英文と意味を確かめながら、お手本をまねして読み上げます。言い回しを覚えて、発音を磨くためのタブです。")
    item, item_ids = choose_practice_item(context, _KEY_PREFIX)

    st.markdown(prompt_html(item.text), unsafe_allow_html=True)
    st.caption(f"{item.meaning_ja}（{item.source_label}）")
    with st.expander("解説"):
        st.markdown(item.explanation_markdown)
    st.markdown("① お手本を聞く")
    speak_button(item.text)
    st.markdown("② ボタンを押して英文を読み上げる")
    attempt = listen_and_compare(
        item.text, key=f"speaking_recognizer_{item.item_id}", unsupported_hint=UNSUPPORTED_HINT
    )
    if attempt is not None:
        st.markdown(f"**一致率**: {format_percent(attempt.result.accuracy)}")
        render_attempt_details(attempt)
    render_next_item_button(item_ids, _KEY_PREFIX)
    with st.expander("音声認識が使えないとき（録音して聞き比べ）"):
        recording = st.audio_input("自分の声を録音", key=f"speaking_recording_{item.item_id}")
        if recording is not None:
            st.audio(recording)
