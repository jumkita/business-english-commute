"""📝 クイズ（FR-01）。時間で区切ったセッションで 4 択に答える。"""

from __future__ import annotations

import random
import time
from dataclasses import dataclass, field

import streamlit as st

from english_app.content import DOMAIN_LABELS, Domain
from english_app.explanations import item_markdown, item_title
from english_app.quiz import QUESTION_KIND_LABELS, QUIZ_DOMAINS, Question, QuestionKind, QuizItem, build_question, quiz_items
from english_app.session import DAILY_NEW_CARD_LIMIT, StudyMode, StudySession, make_card_id, pick_next_card
from english_app.srs import Grade
from english_app.ui.components import speak_button
from english_app.ui.formatting import (
    SECONDS_PER_MINUTE,
    escape_markdown,
    format_percent,
    format_remaining,
    prompt_html,
)
from english_app.ui.session_options import DEFAULT_DURATION_MINUTES, render_duration_picker
from english_app.ui.state import AppContext, current_run, flush_progress, record_answer, render_flag_button

ALL_DOMAINS = "all"

_RUN_KEY = "quiz_run"


@dataclass
class QuizRun:
    session: StudySession
    domain: Domain | None
    question: Question | None = None
    card_id: str | None = None
    question_started_at: float = 0.0
    selected_index: int | None = None
    mistakes: list[str] = field(default_factory=list)
    finished: bool = False


def start_quiz(domain: Domain | None = None, minutes: int = DEFAULT_DURATION_MINUTES) -> None:
    session = StudySession(duration_seconds=minutes * SECONDS_PER_MINUTE, started_at=time.time())
    st.session_state[_RUN_KEY] = QuizRun(session=session, domain=domain)


def active_run_remaining_seconds() -> int | None:
    """ホーム画面の「続きから」用。進行中のクイズがなければ None。"""
    run = _current_run()
    if run is None or run.finished:
        return None
    return run.session.remaining_seconds(time.time())


def render(context: AppContext) -> None:
    run = _current_run()
    if run is None:
        _render_setup(context)
        return
    if not run.finished and run.question is None:
        _ask_next_question(context, run)
    if run.finished or run.question is None:
        _render_result(context, run)
        return
    _render_question(context, run, run.question)


def _current_run() -> QuizRun | None:
    return current_run(_RUN_KEY, QuizRun, "クイズ")


def _candidates(context: AppContext, domain: Domain | None) -> dict[str, QuizItem]:
    return {make_card_id(StudyMode.QUIZ, item.id): item for item in quiz_items(context.library, domain)}


def _render_setup(context: AppContext) -> None:
    st.subheader("📝 クイズ", anchor=False)
    domain_options = [ALL_DOMAINS, *(domain.value for domain in QUIZ_DOMAINS)]
    selected_domain = st.pills(
        "出題範囲",
        domain_options,
        default=ALL_DOMAINS,
        format_func=lambda value: "おまかせ" if value == ALL_DOMAINS else DOMAIN_LABELS[Domain(value)],
        key="quiz_domain",
    )
    domain = None if selected_domain in (None, ALL_DOMAINS) else Domain(selected_domain)
    minutes = render_duration_picker(key="quiz_minutes")
    candidates = _candidates(context, domain)
    due = context.progress.due_count(candidates, context.today)
    new_left = max(0, DAILY_NEW_CARD_LIMIT - context.progress.new_cards_introduced(StudyMode.QUIZ, context.today))
    st.caption(f"復習 {due} 問 ・ 今日の新しい問題 あと {new_left} 問 ・ 収録 {len(candidates)} 問")
    st.button(
        "▶ スタート",
        type="primary",
        width="stretch",
        on_click=start_quiz,
        args=(domain, minutes),
    )


def _ask_next_question(context: AppContext, run: QuizRun) -> None:
    candidates = _candidates(context, run.domain)
    card_id = pick_next_card(
        list(candidates),
        context.progress.cards,
        context.today,
        run.session,
        context.progress.new_cards_introduced(StudyMode.QUIZ, context.today),
        random.Random(),
    )
    if card_id is None:
        run.finished = True
        return
    run.question = build_question(candidates[card_id], context.library, random.Random())
    run.card_id = card_id
    run.selected_index = None
    run.question_started_at = time.time()
    run.session.mark_asked(card_id)


def _render_question(context: AppContext, run: QuizRun, question: Question) -> None:
    number = len(run.session.asked)
    remaining = format_remaining(run.session.remaining_seconds(time.time()))
    st.caption(f"⏱ 残り {remaining} ・ {number} 問目 ・ {QUESTION_KIND_LABELS[question.kind]}")
    st.markdown(f"**{question.instruction}**")
    if question.kind == QuestionKind.BETTER_EXPRESSION:
        st.info(escape_markdown(question.prompt))
    elif question.prompt:
        st.markdown(prompt_html(question.prompt), unsafe_allow_html=True)
    if question.audio_text:
        speak_button(question.audio_text)

    if run.selected_index is None:
        for index, choice in enumerate(question.choices):
            st.button(
                escape_markdown(choice),
                key=f"quiz_choice_{number}_{index}",
                on_click=_choose,
                args=(run, index),
                width="stretch",
            )
        st.button("⏹ ここで終了", key=f"quiz_stop_{number}", on_click=_finish, args=(run,), type="tertiary")
        return
    _render_feedback(context, run, question, number)


def _render_feedback(context: AppContext, run: QuizRun, question: Question, number: int) -> None:
    selected_index = run.selected_index
    if selected_index is None:
        return
    is_correct = question.is_correct(selected_index)
    if is_correct:
        st.success(f"⭕ 正解　{escape_markdown(question.correct_choice)}")
    else:
        st.error(f"❌ 不正解　あなたの回答: {escape_markdown(question.choices[selected_index])}")
        st.markdown(f"正解: **{escape_markdown(question.correct_choice)}**")
    if question.review_audio_text != question.audio_text:
        st.caption("🔊 例文を聞く" if question.domain == Domain.VOCABULARY else "🔊 正解の英文を聞く")
        speak_button(question.review_audio_text)
    # 正解したときは解説を畳んで、自己評価のボタンをスクロールせずに押せるようにする
    with st.expander("解説", expanded=not is_correct):
        st.markdown(question.explanation_markdown)

    if is_correct:
        st.caption("覚え具合を選ぶと、次の問題に進みます")
        with st.container(horizontal=True):
            st.button("もう一度", key=f"quiz_again_{number}", on_click=_grade, args=(run, Grade.AGAIN), width="stretch")
            st.button("難しい", key=f"quiz_hard_{number}", on_click=_grade, args=(run, Grade.HARD), width="stretch")
            st.button(
                "簡単",
                key=f"quiz_easy_{number}",
                on_click=_grade,
                args=(run, Grade.EASY),
                type="primary",
                width="stretch",
            )
    else:
        st.button("次へ ▶", key=f"quiz_next_{number}", on_click=_next, args=(run,), type="primary", width="stretch")
    render_flag_button(context, question.item_id, key=f"quiz_flag_{number}")


def _choose(run: QuizRun, index: int) -> None:
    run.selected_index = index
    if run.question is not None and not run.question.is_correct(index):
        _record(run, Grade.AGAIN, is_correct=False)


def _grade(run: QuizRun, grade: Grade) -> None:
    _record(run, grade, is_correct=True)
    _next(run)


def _record(run: QuizRun, grade: Grade, is_correct: bool) -> None:
    if run.card_id is None or run.question is None:
        return
    record_answer(run.card_id, grade, time.time() - run.question_started_at)
    run.session.record_result(run.card_id, is_correct)
    if not is_correct and run.question.item_id not in run.mistakes:
        run.mistakes.append(run.question.item_id)


def _next(run: QuizRun) -> None:
    run.question = None
    run.card_id = None
    if run.session.is_time_up(time.time()):
        _finish(run)


def _finish(run: QuizRun) -> None:
    run.finished = True
    flush_progress()


def _restart(run: QuizRun) -> None:
    start_quiz(run.domain, run.session.duration_seconds // SECONDS_PER_MINUTE)


def _back_to_setup() -> None:
    st.session_state.pop(_RUN_KEY, None)


def _render_result(context: AppContext, run: QuizRun) -> None:
    session = run.session
    st.subheader("おつかれさまでした 🎉", anchor=False)
    accuracy = session.correct / session.answered if session.answered else None
    with st.container(horizontal=True):
        st.metric("回答", f"{session.answered} 問")
        st.metric("正答率", format_percent(accuracy))
    if run.mistakes:
        st.markdown("**間違えた問題**（次回の復習で優先して出ます）")
        for item_id in run.mistakes:
            item = context.library.items_by_id[item_id]
            with st.expander(item_title(item)):
                st.markdown(item_markdown(context.library, item))
    st.button("▶ もう一度（同じ設定）", type="primary", width="stretch", on_click=_restart, args=(run,))
    st.button("設定を変える", width="stretch", on_click=_back_to_setup)
