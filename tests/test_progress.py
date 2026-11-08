from datetime import date, timedelta

import pytest

from english_app.progress import MAX_SECONDS_PER_ANSWER, Progress, ProgressFormatError
from english_app.session import StudyMode, make_card_id
from english_app.srs import Grade

TODAY = date(2026, 11, 8)
QUIZ_CARD = make_card_id(StudyMode.QUIZ, "vocab-001")
DICTATION_CARD = make_card_id(StudyMode.DICTATION, "cs-001")


def test_record_answer_updates_card_and_daily_stats():
    progress = Progress()
    progress.record_answer(QUIZ_CARD, Grade.EASY, TODAY, elapsed_seconds=12.7)
    progress.record_answer(DICTATION_CARD, Grade.AGAIN, TODAY, elapsed_seconds=20)
    stats = progress.stats_for(TODAY)
    assert (stats.answers, stats.correct, stats.seconds) == (2, 1, 32)
    assert progress.card(QUIZ_CARD).total == 1


def test_elapsed_seconds_are_capped():
    progress = Progress()
    progress.record_answer(QUIZ_CARD, Grade.EASY, TODAY, elapsed_seconds=MAX_SECONDS_PER_ANSWER * 10)
    progress.record_answer(DICTATION_CARD, Grade.EASY, TODAY, elapsed_seconds=-5)
    assert progress.stats_for(TODAY).seconds == MAX_SECONDS_PER_ANSWER


def test_due_count_counts_only_due_cards():
    progress = Progress()
    progress.record_answer(QUIZ_CARD, Grade.AGAIN, TODAY, elapsed_seconds=1)
    progress.record_answer(DICTATION_CARD, Grade.EASY, TODAY, elapsed_seconds=1)
    unknown_card = make_card_id(StudyMode.QUIZ, "vocab-999")
    assert progress.due_count([QUIZ_CARD, DICTATION_CARD, unknown_card], TODAY) == 1


def test_new_cards_introduced_counts_per_mode_and_day():
    progress = Progress()
    progress.record_answer(QUIZ_CARD, Grade.EASY, TODAY - timedelta(days=1), elapsed_seconds=1)
    progress.record_answer(make_card_id(StudyMode.QUIZ, "vocab-002"), Grade.EASY, TODAY, elapsed_seconds=1)
    progress.record_answer(DICTATION_CARD, Grade.EASY, TODAY, elapsed_seconds=1)
    assert progress.new_cards_introduced(StudyMode.QUIZ, TODAY) == 1
    assert progress.new_cards_introduced(StudyMode.DICTATION, TODAY) == 1


class TestStreakDays:
    def _studied_on(self, *days):
        progress = Progress()
        for day in days:
            progress.record_answer(QUIZ_CARD, Grade.EASY, day, elapsed_seconds=1)
        return progress

    def test_counts_consecutive_days_including_today(self):
        progress = self._studied_on(TODAY, TODAY - timedelta(days=1), TODAY - timedelta(days=2))
        assert progress.streak_days(TODAY) == 3

    def test_keeps_streak_until_today_is_studied(self):
        progress = self._studied_on(TODAY - timedelta(days=1), TODAY - timedelta(days=2))
        assert progress.streak_days(TODAY) == 2

    def test_gap_resets_streak(self):
        progress = self._studied_on(TODAY, TODAY - timedelta(days=2))
        assert progress.streak_days(TODAY) == 1

    def test_no_history_is_zero(self):
        assert Progress().streak_days(TODAY) == 0


def test_toggle_flag():
    progress = Progress()
    assert progress.toggle_flag("vocab-001") is True
    assert "vocab-001" in progress.flagged_item_ids
    assert progress.toggle_flag("vocab-001") is False
    assert not progress.flagged_item_ids


def test_dict_round_trip():
    progress = Progress()
    progress.record_answer(QUIZ_CARD, Grade.HARD, TODAY, elapsed_seconds=8)
    progress.toggle_flag("ph-001")
    restored = Progress.from_dict(progress.to_dict())
    assert restored == progress


def test_empty_dict_is_empty_progress():
    assert Progress.from_dict({}) == Progress()


def test_invalid_data_raises_format_error():
    with pytest.raises(ProgressFormatError):
        Progress.from_dict({"cards": {QUIZ_CARD: {"due": "not-a-date"}}})
    with pytest.raises(ProgressFormatError):
        Progress.from_dict({"daily": []})
