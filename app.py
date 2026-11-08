"""通勤ビジネス英語（Streamlit のエントリーポイント）。"""

from typing import assert_never

import streamlit as st

from english_app.content import ContentError
from english_app.ui.components import inject_base_style
from english_app.ui.navigation import Page, render_navigation
from english_app.ui.state import AppContext, get_context
from english_app.views import (
    dictation_view,
    dictionary_view,
    home_view,
    listening_view,
    quiz_view,
    record_view,
    shadowing_view,
    speaking_view,
)
from english_app.views.storage_view import render_storage_status

st.set_page_config(page_title="通勤ビジネス英語", page_icon="🎧", layout="centered", initial_sidebar_state="collapsed")


def render_page(page: Page, context: AppContext) -> None:
    match page:
        case Page.HOME:
            home_view.render(context)
        case Page.QUIZ:
            quiz_view.render(context)
        case Page.DICTATION:
            dictation_view.render(context)
        case Page.LISTENING:
            listening_view.render(context)
        case Page.SPEAKING:
            speaking_view.render(context)
        case Page.SHADOWING:
            shadowing_view.render(context)
        case Page.DICTIONARY:
            dictionary_view.render(context)
        case Page.RECORD:
            record_view.render(context)
        case _:
            assert_never(page)


def main() -> None:
    inject_base_style()
    try:
        context = get_context()
    except ContentError as error:
        st.error(str(error))
        st.stop()
    page = render_navigation()
    render_storage_status(context, show_login=page == Page.HOME)
    render_page(page, context)


main()
