from datetime import date, timedelta

import pytest

from english_app.content import load_library
from english_app.progress import Progress
from english_app.session import StudyMode, make_card_id
from english_app.srs import Grade
from english_app.stats import RECENT_DAYS, all_card_ids, find_weak_cards, recent_daily_minutes, summarize_areas

TODAY = date(2026, 11, 8)


def test_all_card_ids_are_unique():
    card_ids = all_card_ids(load_library())
    assert len(card_ids) == len(set(card_ids))


def test_summarize_areas_counts_studied_and_accuracy():
    library = load_library()
    progress = Progress()
    vocabulary_card = make_card_id(StudyMode.QUIZ, library.vocabulary[0].id)
    progress.record_answer(vocabulary_card, Grade.EASY, TODAY, elapsed_seconds=1)
    progress.record_answer(vocabulary_card, Grade.AGAIN, TODAY, elapsed_seconds=1)
    vocabulary_summary = summarize_areas(library, progress)[0]
    assert vocabulary_summary.total == len(library.vocabulary)
    assert vocabulary_summary.studied == 1
    assert vocabulary_summary.accuracy == pytest.approx(0.5)


def test_weak_cards_sorted_by_lapses():
    progress = Progress()
    once = make_card_id(StudyMode.QUIZ, "vocab-001")
    twice = make_card_id(StudyMode.DICTATION, "cs-001")
    never = make_card_id(StudyMode.QUIZ, "vocab-002")
    progress.record_answer(once, Grade.AGAIN, TODAY, elapsed_seconds=1)
    progress.record_answer(twice, Grade.AGAIN, TODAY, elapsed_seconds=1)
    progress.record_answer(twice, Grade.AGAIN, TODAY, elapsed_seconds=1)
    progress.record_answer(never, Grade.EASY, TODAY, elapsed_seconds=1)
    weak = find_weak_cards(progress)
    assert [card.card_id for card in weak] == [twice, once]
    assert weak[0].mode is StudyMode.DICTATION
    assert weak[0].item_id == "cs-001"


def test_recent_daily_minutes_ends_today():
    progress = Progress()
    progress.record_answer(make_card_id(StudyMode.QUIZ, "vocab-001"), Grade.EASY, TODAY, elapsed_seconds=90)
    daily = recent_daily_minutes(progress, TODAY)
    assert len(daily) == RECENT_DAYS
    assert daily[0].day == TODAY - timedelta(days=RECENT_DAYS - 1)
    assert daily[-1].day == TODAY
    assert daily[-1].minutes == pytest.approx(1.5)
