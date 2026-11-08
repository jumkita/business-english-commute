"""📚 辞書。収録項目を検索して、解説と音声を確認する。"""

from __future__ import annotations

import streamlit as st

from english_app.content import DOMAIN_LABELS, Domain
from english_app.dictionary import build_entries, search_entries
from english_app.ui.components import speak_button
from english_app.ui.formatting import escape_markdown
from english_app.ui.state import AppContext, render_flag_button

ALL_DOMAINS = "all"


def render(context: AppContext) -> None:
    st.subheader("📚 辞書", anchor=False)
    query = st.text_input("検索（英語・日本語）", key="dictionary_query", placeholder="例: leverage / 日程")
    selected_domain = st.pills(
        "種類",
        [ALL_DOMAINS, *(domain.value for domain in Domain)],
        default=ALL_DOMAINS,
        format_func=lambda value: "すべて" if value == ALL_DOMAINS else DOMAIN_LABELS[Domain(value)],
        key="dictionary_domain",
    )
    flagged_only = st.toggle("🚩 要確認の項目だけ表示", key="dictionary_flagged_only")
    results = search_entries(
        build_entries(context.library),
        query=query or "",
        domain=None if selected_domain in (None, ALL_DOMAINS) else Domain(selected_domain),
        flagged_only=flagged_only,
        flagged_item_ids=context.progress.flagged_item_ids,
    )
    st.caption(f"{len(results)} 件")
    if not results:
        st.info("見つかりませんでした。")
        return

    entries_by_id = {entry.item_id: entry for entry in results}
    selected_id = st.selectbox(
        "項目",
        list(entries_by_id),
        format_func=lambda item_id: f"{entries_by_id[item_id].title} — {entries_by_id[item_id].subtitle}",
        key="dictionary_item",
    )
    entry = entries_by_id.get(selected_id or "", results[0])
    with st.container(border=True):
        st.subheader(escape_markdown(entry.title), anchor=False)
        st.markdown(entry.body_markdown)
        speak_button(entry.audio_text)
        render_flag_button(context, entry.item_id, key=f"dictionary_flag_{entry.item_id}")
