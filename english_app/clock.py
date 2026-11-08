"""日付の基準を日本時間にそろえる（Streamlit Cloud のサーバーは UTC で動くため）。"""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

JST = timezone(timedelta(hours=9), name="JST")
SECONDS_PER_MINUTE = 60


def today_jst() -> date:
    return datetime.now(JST).date()
