"""クイズと書き取りで共通の、セッション時間の選択肢。"""

from __future__ import annotations

import streamlit as st

DURATION_MINUTES = (3, 5, 10)
DEFAULT_DURATION_MINUTES = 5


def render_duration_picker(key: str) -> int:
    minutes = st.segmented_control(
        "時間",
        DURATION_MINUTES,
        default=DEFAULT_DURATION_MINUTES,
        format_func=lambda value: f"{value}分",
        key=key,
    )
    return minutes or DEFAULT_DURATION_MINUTES
