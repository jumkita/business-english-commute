from datetime import date, timedelta

from english_app.srs import MAX_EASE, MAX_INTERVAL_DAYS, MIN_EASE, CardState, Grade, schedule

TODAY = date(2026, 11, 8)


def _review_on_due_dates(grades):
    state = CardState()
    day = TODAY
    for grade in grades:
        state = schedule(state, grade, day)
        day = state.due
    return state


def test_new_card_is_new_and_not_due():
    state = CardState()
    assert state.is_new
    assert not state.is_due(TODAY)


def test_again_is_due_today_and_counts_lapse():
    state = schedule(CardState(), Grade.AGAIN, TODAY)
    assert state.due == TODAY
    assert state.interval_days == 0
    assert state.repetitions == 0
    assert state.lapses == 1
    assert state.ease < CardState().ease
    assert state.is_due(TODAY)


def test_first_hard_is_one_day_later():
    state = schedule(CardState(), Grade.HARD, TODAY)
    assert state.due == TODAY + timedelta(days=1)


def test_easy_intervals_grow():
    state = _review_on_due_dates([Grade.EASY])
    assert state.interval_days == 2
    state = _review_on_due_dates([Grade.EASY, Grade.EASY])
    assert state.interval_days == 6
    state = _review_on_due_dates([Grade.EASY, Grade.EASY, Grade.EASY])
    assert state.interval_days == 16


def test_hard_grows_slower_than_easy():
    base = _review_on_due_dates([Grade.EASY, Grade.EASY])
    hard = schedule(base, Grade.HARD, base.due)
    easy = schedule(base, Grade.EASY, base.due)
    assert base.interval_days < hard.interval_days < easy.interval_days


def test_again_after_progress_resets_interval():
    base = _review_on_due_dates([Grade.EASY, Grade.EASY, Grade.EASY])
    state = schedule(base, Grade.AGAIN, base.due)
    assert state.interval_days == 0
    assert state.repetitions == 0


def test_ease_stays_within_bounds():
    assert _review_on_due_dates([Grade.AGAIN] * 20).ease == MIN_EASE
    assert _review_on_due_dates([Grade.EASY] * 20).ease == MAX_EASE


def test_interval_is_capped_after_many_correct_answers():
    assert _review_on_due_dates([Grade.EASY] * 50).interval_days == MAX_INTERVAL_DAYS
    assert _review_on_due_dates([Grade.EASY] * 3 + [Grade.HARD] * 50).interval_days == MAX_INTERVAL_DAYS


def test_mastered_after_long_interval():
    assert _review_on_due_dates([Grade.EASY] * 4).is_mastered


def test_counts_answers():
    state = _review_on_due_dates([Grade.EASY, Grade.AGAIN, Grade.HARD])
    assert (state.total, state.correct, state.lapses) == (3, 2, 1)
    assert state.first_reviewed == TODAY


def test_dict_round_trip():
    state = _review_on_due_dates([Grade.EASY, Grade.HARD])
    assert CardState.from_dict(state.to_dict()) == state
