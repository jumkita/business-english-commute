"""学習履歴の保存状態の表示と、パスコード入力（NFR-06）。"""

from __future__ import annotations

import streamlit as st

from english_app.config import STORAGE_MODE_LABELS, AppSettings, StorageMode
from english_app.ui.state import AppContext, reload_progress, try_login


def render_storage_status(context: AppContext, show_login: bool) -> None:
    if context.load_error:
        st.error(context.load_error)
        st.button("🔄 学習履歴を読み込み直す", on_click=reload_progress)
    if context.save_error:
        st.warning(f"学習履歴を保存できませんでした: {context.save_error}")

    settings = context.settings
    if settings.gist_without_passcode:
        st.error(
            "GIST_ID と GITHUB_TOKEN が設定されていますが、APP_PASSCODE が未設定です。"
            "公開 URL から誰でも学習履歴を書き換えられないよう、保存を止めています。Secrets に APP_PASSCODE を設定してください。"
        )
        return
    if settings.login_required and context.storage_mode == StorageMode.TRIAL:
        if show_login:
            _render_login_form(settings)
        else:
            st.caption("🧪 お試しモード（学習履歴は保存されません）。🏠 今日 でパスコードを入力すると保存されます。")
        return
    if show_login or context.storage_mode == StorageMode.TRIAL:
        st.caption(STORAGE_MODE_LABELS[context.storage_mode])


def _render_login_form(settings: AppSettings) -> None:
    with st.expander("🔒 パスコードを入力すると学習履歴が保存されます（今はお試しモード）", expanded=True):
        st.caption("お試しモードで解いた分は、ログイン後の学習履歴には引き継がれません。")
        with st.form("login_form", border=False):
            passcode = st.text_input("パスコード", type="password", key="login_passcode")
            submitted = st.form_submit_button("ログイン", type="primary", width="stretch")
        if submitted:
            if try_login(settings, passcode):
                st.rerun()
            st.error("パスコードが違います。")
