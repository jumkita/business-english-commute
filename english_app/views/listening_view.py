"""🎧 聞き流し（FR-02）。英語だけを「英語 → ポーズ → 英語」の順で連続再生する。"""

from __future__ import annotations

import streamlit as st

from english_app.listening import build_listening_units, build_review_unit
from english_app.ui.components import listening_player
from english_app.ui.state import AppContext

REPEAT_OPTIONS = (1, 2, 3)
DEFAULT_REPEAT = 2
PAUSE_MILLISECONDS = {"短い": 1500, "普通": 3000, "長い": 5000}
DEFAULT_PAUSE = "普通"
RATE_OPTIONS = (0.8, 1.0, 1.2)
DEFAULT_RATE = 1.0


def render(context: AppContext) -> None:
    st.subheader("🎧 聞き流し", anchor=False)
    units = build_listening_units(context.library)
    review_unit = build_review_unit(context.library, context.progress, context.today)
    if review_unit is not None:
        units = [review_unit, *units]
    units_by_id = {unit.id: unit for unit in units}
    unit_id = st.selectbox(
        "単元",
        list(units_by_id),
        format_func=lambda value: f"{units_by_id[value].label}（{len(units_by_id[value].tracks)}文）",
        key="listening_unit",
    )
    unit = units_by_id.get(unit_id or "", units[0])

    repeat = st.segmented_control(
        "繰り返し", REPEAT_OPTIONS, default=DEFAULT_REPEAT, format_func=lambda value: f"{value}回", key="listening_repeat"
    )
    pause = st.segmented_control("ポーズ", list(PAUSE_MILLISECONDS), default=DEFAULT_PAUSE, key="listening_pause")
    rate = st.segmented_control(
        "速さ", RATE_OPTIONS, default=DEFAULT_RATE, format_func=lambda value: f"{value:.1f}倍", key="listening_rate"
    )
    keep_awake = st.toggle("再生中は画面を消さない", value=True, key="listening_keep_awake")

    listening_player(
        unit.tracks,
        repeat=repeat or DEFAULT_REPEAT,
        pause_ms=PAUSE_MILLISECONDS[pause or DEFAULT_PAUSE],
        rate=rate or DEFAULT_RATE,
        keep_awake=keep_awake,
    )
    st.caption(
        "音声は iPhone 内蔵の読み上げ（米国英語）です。画面をロックすると再生が止まるため、"
        "「再生中は画面を消さない」をオンにしてください。"
    )
    if review_unit is None:
        st.caption("復習期限の来た問題があると、単元の先頭に「今日の復習」が出ます。")
