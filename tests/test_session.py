import random
from datetime import date, timedelta

import pytest

from english_app.session import (
    DAILY_NEW_CARD_LIMIT,
    RETRY_GAP_QUESTIONS,
    StudyMode,
    StudySession,
    make_card_id,
    pick_next_card,
    split_card_id,
)
from english_app.srs import CardState, Grade, schedule

TODAY = date(2026, 11, 8)


def _session(duration_seconds=300):
    return StudySession(duration_seconds=duration_seconds, started_at=1000.0)


def _pick(candidates, cards=None, session=None, new_cards_today=0):
    return pick_next_card(
        candidates, cards or {}, TODAY, session or _session(), new_cards_today, random.Random(0)
    )


def _due_card(due):
    return CardState(interval_days=1, repetitions=1, due=due, first_reviewed=due, last_reviewed=due, total=1)


class TestCardId:
    def test_round_trip(self):
        card_id = make_card_id(StudyMode.DICTATION, "dlg-001-2")
        assert split_card_id(card_id) == (StudyMode.DICTATION, "dlg-001-2")

    @pytest.mark.parametrize("card_id", ["quiz", "quiz:", "unknown:vocab-001"])
    def test_invalid_card_id(self, card_id):
        with pytest.raises(ValueError):
            split_card_id(card_id)


class TestStudySession:
    def test_time_up(self):
        session = _session(duration_seconds=180)
        assert session.remaining_seconds(1000.0 + 60) == 120
        assert not session.is_time_up(1000.0 + 179)
        assert session.is_time_up(1000.0 + 180)

    def test_correct_retry_clears_failure(self):
        session = _session()
        session.mark_asked("a")
        session.record_result("a", is_correct=False)
        assert "a" in session.failed_at
        session.record_result("a", is_correct=True)
        assert "a" not in session.failed_at
        assert (session.answered, session.correct) == (2, 1)


class TestPickNextCard:
    def test_no_candidates(self):
        assert _pick([]) is None

    def test_failed_card_comes_back_after_gap(self):
        session = _session()
        session.mark_asked("a")
        session.record_result("a", is_correct=False)
        for card_id in ["b", "c"][: RETRY_GAP_QUESTIONS - 1]:
            session.mark_asked(card_id)
        assert _pick(["a", "d"], session=session) == "d"
        session.mark_asked("d")
        assert _pick(["a", "e"], session=session) == "a"

    def test_due_cards_before_new_cards(self):
        cards = {"due-later": _due_card(TODAY - timedelta(days=1)), "due-first": _due_card(TODAY - timedelta(days=3))}
        assert _pick(["new", "due-later", "due-first"], cards=cards) == "due-first"

    def test_new_card_when_nothing_due(self):
        cards = {"studied": _due_card(TODAY + timedelta(days=3))}
        assert _pick(["studied", "new"], cards=cards) == "new"

    def test_daily_new_limit_prefers_studied_cards(self):
        cards = {"studied": _due_card(TODAY + timedelta(days=3))}
        assert _pick(["studied", "new"], cards=cards, new_cards_today=DAILY_NEW_CARD_LIMIT) == "studied"

    def test_does_not_repeat_until_all_asked(self):
        session = _session()
        session.mark_asked("a")
        assert _pick(["a", "b"], session=session) == "b"

    def test_least_asked_when_all_asked(self):
        session = _session()
        for card_id in ["a", "b", "a"]:
            session.mark_asked(card_id)
        assert _pick(["a", "b"], session=session) == "b"

    def test_card_failed_today_is_due_again(self):
        cards = {"lapsed": schedule(CardState(), Grade.AGAIN, TODAY)}
        assert _pick(["new", "lapsed"], cards=cards) == "lapsed"
