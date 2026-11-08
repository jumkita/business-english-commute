"""記録タブ用の軽量な表とグラフ。

st.dataframe や st.bar_chart は pyarrow での変換と大きな描画ライブラリの読み込みが必要で、iPhone では重い
（pyarrow 25 系には Streamlit Cloud でアプリが落ちる不具合もある）。数行の表と 14 本の棒なので Markdown と HTML で描く。
"""

from __future__ import annotations

import html
from collections.abc import Sequence

from english_app.stats import AreaSummary, DailyMinutes
from english_app.ui.formatting import escape_markdown, format_percent

BAR_MAX_HEIGHT_PX = 80
BAR_LABEL_AREA_PX = 32


def area_table_markdown(summaries: Sequence[AreaSummary]) -> str:
    rows = [
        f"| {escape_markdown(summary.label)} | {summary.studied} / {summary.total} | {summary.mastered} "
        f"| {format_percent(summary.accuracy)} |"
        for summary in summaries
    ]
    return "\n".join(["| 領域 | 学習 | 習得 | 正答率 |", "|---|---|---|---|", *rows])


def daily_minutes_bars_html(daily: Sequence[DailyMinutes]) -> str:
    peak = max((entry.minutes for entry in daily), default=0.0) or 1.0
    columns = []
    for entry in daily:
        height = round(entry.minutes / peak * BAR_MAX_HEIGHT_PX)
        value = html.escape(f"{entry.minutes:.0f}") if entry.minutes >= 1 else ""
        columns.append(
            '<div style="flex:1;display:flex;flex-direction:column;align-items:center;justify-content:flex-end;">'
            f'<div style="font-size:10px;color:#57606a;">{value}</div>'
            f'<div style="width:70%;height:{height}px;background:#0969da;border-radius:3px 3px 0 0;"></div>'
            f'<div style="font-size:10px;color:#57606a;margin-top:2px;">{entry.day.day}</div>'
            "</div>"
        )
    total_height = BAR_MAX_HEIGHT_PX + BAR_LABEL_AREA_PX
    return f'<div style="display:flex;gap:2px;align-items:flex-end;height:{total_height}px;">{"".join(columns)}</div>'
