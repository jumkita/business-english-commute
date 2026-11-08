"""🏠 今日。復習件数などの要約と、2 タップ以内で学習を始めるためのショートカット（NFR-02）。"""

from __future__ import annotations

import streamlit as st

from english_app.clock import SECONDS_PER_MINUTE
from english_app.stats import all_card_ids
from english_app.ui.formatting import format_remaining
from english_app.ui.navigation import Page, go_to
from english_app.ui.state import AppContext
from english_app.views import dictation_view, quiz_view


def render(context: AppContext) -> None:
    progress = context.progress
    today_stats = progress.stats_for(context.today)
    due = progress.due_count(all_card_ids(context.library), context.today)
    with st.container(horizontal=True):
        st.metric("今日の復習", f"{due} 問")
        st.metric("連続学習", f"{progress.streak_days(context.today)} 日")
        st.metric("今日の学習", f"{today_stats.seconds // SECONDS_PER_MINUTE} 分")

    remaining = quiz_view.active_run_remaining_seconds()
    if remaining is not None:
        st.button(
            f"▶ クイズの続きから（残り {format_remaining(remaining)}）",
            type="primary",
            width="stretch",
            on_click=go_to,
            args=(Page.QUIZ,),
        )
    st.button(
        "📝 5分クイズ（おまかせ）",
        type="primary" if remaining is None else "secondary",
        width="stretch",
        on_click=_start_quick_quiz,
    )
    st.button("✍️ 5分書き取り（おまかせ）", width="stretch", on_click=_start_quick_dictation)
    st.button("🎧 聞き流し", width="stretch", on_click=go_to, args=(Page.LISTENING,))
    st.caption(
        "座れるときはクイズと書き取り、満員電車や徒歩のときは聞き流しがおすすめです。"
        "復習期限の来た問題から優先して出ます。"
    )


def _start_quick_quiz() -> None:
    quiz_view.start_quiz()
    go_to(Page.QUIZ)


def _start_quick_dictation() -> None:
    dictation_view.start_dictation()
    go_to(Page.DICTATION)
