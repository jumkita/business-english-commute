"""画面表示用の文字列整形。"""

from __future__ import annotations

import html

from english_app.clock import SECONDS_PER_MINUTE

# ボタンのラベルなどは Markdown として解釈されるため、英文中の記号を文字として表示させる
_MARKDOWN_SPECIAL_CHARACTERS = frozenset("\\`*_[]<>#~|$")


def escape_markdown(text: str) -> str:
    return "".join(f"\\{char}" if char in _MARKDOWN_SPECIAL_CHARACTERS else char for char in text)


def prompt_html(text: str) -> str:
    """問題文や読み上げる英文を、見出しより控えめな大きさで目立たせる（長い日本語文でも数行に収まるように）。"""
    return (
        '<div style="font-size:1.25rem;font-weight:600;line-height:1.5;margin:0.25rem 0 0.5rem;">'
        f"{html.escape(text)}</div>"
    )


def format_remaining(seconds: int) -> str:
    minutes, rest = divmod(max(seconds, 0), SECONDS_PER_MINUTE)
    return f"{minutes}:{rest:02d}"


def format_percent(ratio: float | None) -> str:
    return "—" if ratio is None else f"{ratio:.0%}"
