"""✍️ 書き取り（ディクテーション, FR-10）。聞いた英文をタイプして、単語ごとに答え合わせする。"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import assert_never

import streamlit as st

from english_app.content import DOMAIN_LABELS, Domain
from english_app.dictation import DICTATION_DOMAINS, DictationItem, build_dictation_items, grade_for_verdict, hint_for
from english_app.session import DAILY_NEW_CARD_LIMIT, StudyMode, StudySession, make_card_id, pick_next_card
from english_app.text_match import MatchResult, Verdict, compare
from english_app.ui.components import speak_button
from english_app.ui.diff_view import DIFF_LEGEND, VERDICT_LABELS, render_diff_html
from english_app.ui.formatting import SECONDS_PER_MINUTE, escape_markdown, format_percent, format_remaining
from english_app.ui.session_options import DEFAULT_DURATION_MINUTES, render_duration_picker
from english_app.ui.state import AppContext, current_run, flush_progress, record_answer, render_flag_button

ALL_DOMAINS = "all"

_RUN_KEY = "dictation_run"


@dataclass
class DictationRun:
    session: StudySession
    domain: Domain | None
    item: DictationItem | None = None
    card_id: str | None = None
    question_started_at: float = 0.0
    result: MatchResult | None = None
    show_hint: bool = False
    mistakes: list[DictationItem] = field(default_factory=list)
    finished: bool = False


def start_dictation(domain: Domain | None = None, minutes: int = DEFAULT_DURATION_MINUTES) -> None:
    session = StudySession(duration_seconds=minutes * SECONDS_PER_MINUTE, started_at=time.time())
    st.session_state[_RUN_KEY] = DictationRun(session=session, domain=domain)


def render(context: AppContext) -> None:
    run = current_run(_RUN_KEY, DictationRun, "書き取り")
    if run is None:
        _render_setup(context)
        return
    if not run.finished and run.item is None:
        _ask_next_item(context, run)
    if run.finished or run.item is None:
        _render_result(run)
        return
    _render_item(context, run, run.item)


def _candidates(context: AppContext, domain: Domain | None) -> dict[str, DictationItem]:
    items = build_dictation_items(context.library, domain)
    return {make_card_id(StudyMode.DICTATION, item.item_id): item for item in items}


def _render_setup(context: AppContext) -> None:
    st.subheader("✍️ 書き取り", anchor=False)
    st.caption("英文の音声を聞いて、聞こえたとおりにタイプします。大文字・小文字、句読点、縮約形（I'm / I am）、数字の書き方は区別しません。")
    selected_domain = st.pills(
        "出題範囲",
        [ALL_DOMAINS, *(domain.value for domain in DICTATION_DOMAINS)],
        default=ALL_DOMAINS,
        format_func=lambda value: "おまかせ" if value == ALL_DOMAINS else DOMAIN_LABELS[Domain(value)],
        key="dictation_domain",
    )
    domain = None if selected_domain in (None, ALL_DOMAINS) else Domain(selected_domain)
    minutes = render_duration_picker(key="dictation_minutes")
    candidates = _candidates(context, domain)
    due = context.progress.due_count(candidates, context.today)
    new_left = max(0, DAILY_NEW_CARD_LIMIT - context.progress.new_cards_introduced(StudyMode.DICTATION, context.today))
    st.caption(f"復習 {due} 文 ・ 今日の新しい文 あと {new_left} 文 ・ 収録 {len(candidates)} 文")
    st.button("▶ スタート", type="primary", width="stretch", on_click=start_dictation, args=(domain, minutes))


def _ask_next_item(context: AppContext, run: DictationRun) -> None:
    candidates = _candidates(context, run.domain)
    card_id = pick_next_card(
        list(candidates),
        context.progress.cards,
        context.today,
        run.session,
        context.progress.new_cards_introduced(StudyMode.DICTATION, context.today),
        random.Random(),
    )
    if card_id is None:
        run.finished = True
        return
    run.item = candidates[card_id]
    run.card_id = card_id
    run.result = None
    run.show_hint = False
    run.question_started_at = time.time()
    run.session.mark_asked(card_id)


def _render_item(context: AppContext, run: DictationRun, item: DictationItem) -> None:
    number = len(run.session.asked)
    remaining = format_remaining(run.session.remaining_seconds(time.time()))
    st.caption(f"⏱ 残り {remaining} ・ {number} 問目")
    st.markdown("**音声を聞いて、聞こえたとおりに英文を入力してください**")
    speak_button(item.text)
    if run.result is None:
        _render_answer_form(run, item, number)
    else:
        _render_check_result(context, run, item, run.result, number)


def _render_answer_form(run: DictationRun, item: DictationItem, number: int) -> None:
    if run.show_hint:
        st.code(hint_for(item.text), language=None, wrap_lines=True)
        st.caption(f"{len(item.text.split())} 語")
    answer_key = f"dictation_answer_{number}"
    with st.form(key=f"dictation_form_{number}", border=False):
        st.text_input(
            "聞き取った英文",
            key=answer_key,
            placeholder="Type what you heard",
            autocomplete="off",
            label_visibility="collapsed",
        )
        st.form_submit_button("答え合わせ", type="primary", width="stretch", on_click=_check, args=(run, answer_key))
    st.caption("空欄のまま答え合わせすると、正解を表示します（不正解として記録）。")
    with st.container(horizontal=True):
        st.button("💡 ヒント", key=f"dictation_hint_{number}", on_click=_show_hint, args=(run,), disabled=run.show_hint)
        st.button("⏹ ここで終了", key=f"dictation_stop_{number}", on_click=_finish, args=(run,), type="tertiary")


def _render_check_result(
    context: AppContext, run: DictationRun, item: DictationItem, result: MatchResult, number: int
) -> None:
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
    st.markdown(render_diff_html(result), unsafe_allow_html=True)
    st.caption(DIFF_LEGEND)
    st.markdown(f"**正解**: {escape_markdown(item.text)}")
    st.markdown(f"**意味**: {escape_markdown(item.meaning_ja)}")
    with st.expander(f"解説（{item.source_label}）"):
        st.markdown(item.explanation_markdown)
    st.button("次へ ▶", key=f"dictation_next_{number}", on_click=_next, args=(run,), type="primary", width="stretch")
    render_flag_button(context, item.item_id, key=f"dictation_flag_{number}")


def _show_hint(run: DictationRun) -> None:
    run.show_hint = True


def _check(run: DictationRun, answer_key: str) -> None:
    if run.item is None or run.card_id is None:
        return
    result = compare(run.item.text, st.session_state.get(answer_key, ""))
    run.result = result
    record_answer(run.card_id, grade_for_verdict(result.verdict), time.time() - run.question_started_at)
    is_correct = result.verdict != Verdict.INCORRECT
    run.session.record_result(run.card_id, is_correct)
    if not is_correct and run.item not in run.mistakes:
        run.mistakes.append(run.item)


def _next(run: DictationRun) -> None:
    run.item = None
    run.card_id = None
    run.result = None
    if run.session.is_time_up(time.time()):
        _finish(run)


def _finish(run: DictationRun) -> None:
    run.finished = True
    flush_progress()


def _restart(run: DictationRun) -> None:
    start_dictation(run.domain, run.session.duration_seconds // SECONDS_PER_MINUTE)


def _back_to_setup() -> None:
    st.session_state.pop(_RUN_KEY, None)


def _render_result(run: DictationRun) -> None:
    session = run.session
    st.subheader("おつかれさまでした 🎉", anchor=False)
    accuracy = session.correct / session.answered if session.answered else None
    with st.container(horizontal=True):
        st.metric("回答", f"{session.answered} 文")
        st.metric("正解・惜しい", format_percent(accuracy))
    if run.mistakes:
        st.markdown("**聞き取れなかった文**（次回の復習で優先して出ます）")
        for item in run.mistakes:
            st.markdown(f"- {escape_markdown(item.text)}  \n  {escape_markdown(item.meaning_ja)}")
    st.button("▶ もう一度（同じ設定）", type="primary", width="stretch", on_click=_restart, args=(run,))
    st.button("設定を変える", width="stretch", on_click=_back_to_setup)
