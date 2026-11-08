"""書き取り・発音・シャドーイングの照合結果の表示（判定のラベルと、単語ごとに色分けした HTML）。"""

from __future__ import annotations

import html
from typing import assert_never

import streamlit as st

from english_app.text_match import MatchResult, TokenDiff, TokenStatus, Verdict
from english_app.ui.formatting import format_percent

VERDICT_LABELS: dict[Verdict, str] = {
    Verdict.CORRECT: "⭕ 正解",
    Verdict.CLOSE: "🟡 惜しい（つづりの小さな違いのみ）",
    Verdict.INCORRECT: "❌ 不正解",
}

DIFF_LEGEND = "緑: 正解　黄: つづりの小さな違い　赤: 誤り・余分な語　点線の枠: 抜けた語"

_TOKEN_STYLES: dict[TokenStatus, str] = {
    TokenStatus.CORRECT: "color:#1a7f37;",
    TokenStatus.CLOSE: "color:#9a6700;text-decoration:underline wavy #d4a72c;",
    TokenStatus.WRONG: "color:#cf222e;font-weight:600;",
    TokenStatus.MISSING: "color:#57606a;border:1px dashed #8c959f;border-radius:4px;padding:0 4px;",
    TokenStatus.EXTRA: "color:#cf222e;text-decoration:line-through;",
}


def render_verdict(result: MatchResult) -> None:
    label = f"{VERDICT_LABELS[result.verdict]}（一致率 {format_percent(result.accuracy)}）"
    match result.verdict:
        case Verdict.CORRECT:
            st.success(label)
        case Verdict.CLOSE:
            st.warning(label)
        case Verdict.INCORRECT:
            st.error(label)
        case _:
            assert_never(result.verdict)


def render_diff_html(result: MatchResult) -> str:
    spans = " ".join(_token_html(token) for token in result.tokens)
    return f'<div style="line-height:2.1;font-size:1.1rem;">{spans}</div>'


def _token_html(token: TokenDiff) -> str:
    expected = html.escape(token.expected or "")
    actual = html.escape(token.actual or "")
    match token.status:
        case TokenStatus.CORRECT | TokenStatus.MISSING:
            content = expected
        case TokenStatus.CLOSE:
            content = f'{expected}<small style="color:#57606a;">（{actual}）</small>'
        case TokenStatus.WRONG:
            content = f'<s style="color:#57606a;font-weight:400;">{actual}</s>&nbsp;{expected}'
        case TokenStatus.EXTRA:
            content = actual
        case _:
            assert_never(token.status)
    return f'<span style="{_TOKEN_STYLES[token.status]}">{content}</span>'
