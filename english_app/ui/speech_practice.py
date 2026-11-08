"""発音・シャドーイングで共通の部品。出題する英文の選び方と、音声認識の結果をお手本の英文と照合する処理。"""

from __future__ import annotations

import random
from dataclasses import dataclass

import streamlit as st

from english_app.content import DOMAIN_LABELS, Domain
from english_app.dictation import DICTATION_DOMAINS, DictationItem, build_dictation_items
from english_app.text_match import MatchResult, compare
from english_app.ui.components import speech_recognizer
from english_app.ui.diff_view import DIFF_LEGEND, render_diff_html
from english_app.ui.formatting import escape_markdown
from english_app.ui.state import AppContext

ALL_DOMAINS = "all"
UNSUPPORTED_ERROR = "unsupported"
SPEECH_ERROR_MESSAGES = {
    "no-speech": "声が聞き取れませんでした。もう一度、はっきり話してみてください。",
    "aborted": "音声認識が中断されました。もう一度お試しください。",
    "audio-capture": "マイクが見つかりませんでした。",
    "network": "通信エラーで音声認識できませんでした。電波の良い場所で再度お試しください。",
    "not-allowed": "マイクの使用が許可されていません。設定アプリの Safari（iOS 18 以降は「アプリ」の中）で、マイクを「確認」か「許可」にしてください。",
    "service-not-allowed": "音声認識が許可されていません。設定アプリ → 一般 → キーボード で「音声入力」がオンになっているか確認してください。",
    UNSUPPORTED_ERROR: "このブラウザは音声認識に対応していません。",
}
DEFAULT_SPEECH_ERROR_MESSAGE = "音声認識でエラーが発生しました。"


@dataclass(frozen=True)
class SpeechAttempt:
    transcript: str
    result: MatchResult


def choose_practice_item(context: AppContext, key_prefix: str) -> tuple[DictationItem, list[str]]:
    """出題範囲の選択肢を表示し、表示中の英文と、「次の文」で選べる英文の ID を返す。"""
    selected_domain = st.pills(
        "出題範囲",
        [ALL_DOMAINS, *(domain.value for domain in DICTATION_DOMAINS)],
        default=ALL_DOMAINS,
        format_func=lambda value: "おまかせ" if value == ALL_DOMAINS else DOMAIN_LABELS[Domain(value)],
        key=f"{key_prefix}_domain",
    )
    domain = None if selected_domain in (None, ALL_DOMAINS) else Domain(selected_domain)
    items = {item.item_id: item for item in build_dictation_items(context.library, domain)}
    item_key = _item_key(key_prefix)
    if st.session_state.get(item_key) not in items:
        st.session_state[item_key] = random.choice(list(items))
    return items[st.session_state[item_key]], list(items)


def render_next_item_button(item_ids: list[str], key_prefix: str) -> None:
    st.button("次の文 ▶", type="primary", width="stretch", on_click=_next_item, args=(item_ids, _item_key(key_prefix)))


def listen_and_compare(expected_text: str, *, key: str, unsupported_hint: str) -> SpeechAttempt | None:
    """マイクのボタンを表示し、認識できたらお手本の英文と照合する。認識できなかったときは理由を表示して None を返す。"""
    value = speech_recognizer(key=key)
    if value is None:
        return None
    transcript = str(value.get("transcript") or "").strip()
    if not transcript:
        st.warning(_speech_error_message(str(value.get("error", "")), unsupported_hint))
        return None
    return SpeechAttempt(transcript=transcript, result=compare(expected_text, transcript))


def render_attempt_details(attempt: SpeechAttempt) -> None:
    st.markdown(f"**認識結果**: {escape_markdown(attempt.transcript)}")
    st.markdown(render_diff_html(attempt.result), unsafe_allow_html=True)
    st.caption(DIFF_LEGEND + "（点線の語は認識されませんでした）")


def _item_key(key_prefix: str) -> str:
    return f"{key_prefix}_item_id"


def _next_item(item_ids: list[str], item_key: str) -> None:
    current = st.session_state.get(item_key)
    others = [item_id for item_id in item_ids if item_id != current] or item_ids
    st.session_state[item_key] = random.choice(others)


def _speech_error_message(error: str, unsupported_hint: str) -> str:
    message = SPEECH_ERROR_MESSAGES.get(error, DEFAULT_SPEECH_ERROR_MESSAGE)
    # 音声認識に対応していない端末では、タブごとに用意した代わりの確かめ方を案内する
    return f"{message}{unsupported_hint}" if error == UNSUPPORTED_ERROR else message
