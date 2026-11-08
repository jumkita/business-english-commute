"""📊 記録（FR-06 の詳細）。領域別の正答率・学習時間・苦手な項目。"""

from __future__ import annotations

import streamlit as st

from english_app.clock import SECONDS_PER_MINUTE
from english_app.explanations import title_for_item_id
from english_app.session import StudyMode
from english_app.stats import find_weak_cards, recent_daily_minutes, summarize_areas
from english_app.ui.charts import area_table_markdown, daily_minutes_bars_html
from english_app.ui.formatting import escape_markdown, format_percent
from english_app.ui.state import AppContext

MODE_LABELS: dict[StudyMode, str] = {StudyMode.QUIZ: "クイズ", StudyMode.DICTATION: "書き取り"}


def render(context: AppContext) -> None:
    st.subheader("📊 記録", anchor=False)
    progress = context.progress
    today_stats = progress.stats_for(context.today)
    with st.container(horizontal=True):
        st.metric("連続学習", f"{progress.streak_days(context.today)} 日")
        st.metric("今日の回答", f"{today_stats.answers} 問")
        st.metric("今日の学習", f"{today_stats.seconds // SECONDS_PER_MINUTE} 分")

    st.markdown("**領域別の状況**")
    st.caption("書き取り以外はクイズの成績です。「習得」は復習間隔が 3 週間以上に伸びた問題の数です。")
    st.markdown(area_table_markdown(summarize_areas(context.library, progress)))

    daily = recent_daily_minutes(progress, context.today)
    st.markdown(f"**直近{len(daily)}日の学習時間（分）**")
    st.markdown(daily_minutes_bars_html(daily), unsafe_allow_html=True)

    st.markdown("**苦手な項目**（忘れた回数が多い順）")
    weak_cards = find_weak_cards(progress)
    if not weak_cards:
        st.caption("まだありません。")
    for card in weak_cards:
        title = title_for_item_id(context.library, card.item_id) or card.item_id
        st.markdown(
            f"- {escape_markdown(title)}  \n"
            f"  {MODE_LABELS[card.mode]} ・ 忘れた回数 {card.lapses} ・ 正答率 {format_percent(card.accuracy)}"
        )

    st.markdown("**🚩 要確認の項目**")
    if not progress.flagged_item_ids:
        st.caption("内容が怪しい項目に「要確認」を付けると、ここに一覧が出ます。")
    for item_id in sorted(progress.flagged_item_ids):
        title = title_for_item_id(context.library, item_id) or item_id
        st.markdown(f"- {escape_markdown(title)}（{item_id}）")
