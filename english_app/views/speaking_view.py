"""🗣 発音・シャドーイング（FR-03）。お手本を聞いて読み上げ、Safari 標準の音声認識で照合する。"""

from __future__ import annotations

import random

import streamlit as st

from english_app.content import DOMAIN_LABELS, Domain
from english_app.dictation import DICTATION_DOMAINS, DictationItem, build_dictation_items
from english_app.text_match import compare
from english_app.ui.components import speak_button, speech_recognizer
from english_app.ui.diff_view import DIFF_LEGEND, render_diff_html
from english_app.ui.formatting import escape_markdown, format_percent, prompt_html
from english_app.ui.state import AppContext

ALL_DOMAINS = "all"
SPEECH_ERROR_MESSAGES = {
    "no-speech": "声が聞き取れませんでした。もう一度、はっきり話してみてください。",
    "aborted": "音声認識が中断されました。もう一度お試しください。",
    "audio-capture": "マイクが見つかりませんでした。",
    "network": "通信エラーで音声認識できませんでした。電波の良い場所で再度お試しください。",
    "not-allowed": "マイクの使用が許可されていません。設定アプリの Safari（iOS 18 以降は「アプリ」の中）で、マイクを「確認」か「許可」にしてください。",
    "service-not-allowed": "音声認識が許可されていません。設定アプリ → 一般 → キーボード で「音声入力」がオンになっているか確認してください。",
    "unsupported": "このブラウザは音声認識に対応していません。下の「録音して聞き比べ」を使ってください。",
}
DEFAULT_SPEECH_ERROR_MESSAGE = "音声認識でエラーが発生しました。"

_ITEM_KEY = "speaking_item_id"


def render(context: AppContext) -> None:
    st.subheader("🗣 発音・シャドーイング", anchor=False)
    selected_domain = st.pills(
        "出題範囲",
        [ALL_DOMAINS, *(domain.value for domain in DICTATION_DOMAINS)],
        default=ALL_DOMAINS,
        format_func=lambda value: "おまかせ" if value == ALL_DOMAINS else DOMAIN_LABELS[Domain(value)],
        key="speaking_domain",
    )
    domain = None if selected_domain in (None, ALL_DOMAINS) else Domain(selected_domain)
    items = {item.item_id: item for item in build_dictation_items(context.library, domain)}
    if st.session_state.get(_ITEM_KEY) not in items:
        st.session_state[_ITEM_KEY] = random.choice(list(items))
    item = items[st.session_state[_ITEM_KEY]]

    st.markdown(prompt_html(item.text), unsafe_allow_html=True)
    st.caption(f"{item.meaning_ja}（{item.source_label}）")
    st.markdown("① お手本を聞く")
    speak_button(item.text)
    st.markdown("② ボタンを押して英文を読み上げる")
    _render_recognition(item)
    st.button("次の文 ▶", type="primary", width="stretch", on_click=_next_item, args=(list(items),))
    with st.expander("音声認識が使えないとき（録音して聞き比べ）"):
        recording = st.audio_input("自分の声を録音", key=f"speaking_recording_{item.item_id}")
        if recording is not None:
            st.audio(recording)


def _render_recognition(item: DictationItem) -> None:
    value = speech_recognizer(key=f"speaking_recognizer_{item.item_id}")
    if value is None:
        return
    transcript = value.get("transcript")
    if not transcript:
        error = str(value.get("error", ""))
        st.warning(SPEECH_ERROR_MESSAGES.get(error, DEFAULT_SPEECH_ERROR_MESSAGE))
        return
    result = compare(item.text, str(transcript))
    st.markdown(f"**認識結果**: {escape_markdown(str(transcript))}")
    st.markdown(f"**一致率**: {format_percent(result.accuracy)}")
    st.markdown(render_diff_html(result), unsafe_allow_html=True)
    st.caption(DIFF_LEGEND + "（点線の語は認識されませんでした）")


def _next_item(item_ids: list[str]) -> None:
    current = st.session_state.get(_ITEM_KEY)
    others = [item_id for item_id in item_ids if item_id != current] or item_ids
    st.session_state[_ITEM_KEY] = random.choice(others)
