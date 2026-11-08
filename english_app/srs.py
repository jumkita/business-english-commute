"""SM-2 を簡略化した間隔反復（FR-04）。片手で押せるよう自己評価は 3 段階にしている。"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import date, timedelta
from enum import StrEnum
from typing import Any, assert_never

DEFAULT_EASE = 2.5
MIN_EASE = 1.3
MAX_EASE = 3.0
AGAIN_EASE_PENALTY = 0.2
HARD_EASE_PENALTY = 0.15
EASY_EASE_BONUS = 0.1
HARD_INTERVAL_MULTIPLIER = 1.2
FIRST_HARD_INTERVAL_DAYS = 1
FIRST_EASY_INTERVAL_DAYS = 2
SECOND_EASY_INTERVAL_DAYS = 6
MASTERED_INTERVAL_DAYS = 21
# 間隔は掛け算で伸びるため、上限がないと数十回の正解で日付の範囲を超えてしまう
MAX_INTERVAL_DAYS = 365
EASE_DECIMALS = 3


class Grade(StrEnum):
    AGAIN = "again"
    HARD = "hard"
    EASY = "easy"


@dataclass(frozen=True)
class CardState:
    interval_days: int = 0
    ease: float = DEFAULT_EASE
    repetitions: int = 0
    due: date | None = None
    first_reviewed: date | None = None
    last_reviewed: date | None = None
    lapses: int = 0
    total: int = 0
    correct: int = 0

    @property
    def is_new(self) -> bool:
        return self.last_reviewed is None

    @property
    def is_mastered(self) -> bool:
        return self.interval_days >= MASTERED_INTERVAL_DAYS

    def is_due(self, today: date) -> bool:
        return self.due is not None and self.due <= today

    def to_dict(self) -> dict[str, Any]:
        return {
            "interval_days": self.interval_days,
            "ease": self.ease,
            "repetitions": self.repetitions,
            "due": _date_to_text(self.due),
            "first_reviewed": _date_to_text(self.first_reviewed),
            "last_reviewed": _date_to_text(self.last_reviewed),
            "lapses": self.lapses,
            "total": self.total,
            "correct": self.correct,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CardState:
        return cls(
            interval_days=int(data.get("interval_days", 0)),
            ease=float(data.get("ease", DEFAULT_EASE)),
            repetitions=int(data.get("repetitions", 0)),
            due=_text_to_date(data.get("due")),
            first_reviewed=_text_to_date(data.get("first_reviewed")),
            last_reviewed=_text_to_date(data.get("last_reviewed")),
            lapses=int(data.get("lapses", 0)),
            total=int(data.get("total", 0)),
            correct=int(data.get("correct", 0)),
        )


def schedule(state: CardState, grade: Grade, today: date) -> CardState:
    """回答結果から次回の復習日を決める。間違えた問題は当日中にもう一度出す。"""
    match grade:
        case Grade.AGAIN:
            interval = 0
            repetitions = 0
            ease = max(MIN_EASE, state.ease - AGAIN_EASE_PENALTY)
        case Grade.HARD:
            interval = _hard_interval(state)
            repetitions = state.repetitions + 1
            ease = max(MIN_EASE, state.ease - HARD_EASE_PENALTY)
        case Grade.EASY:
            interval = _easy_interval(state)
            repetitions = state.repetitions + 1
            ease = min(MAX_EASE, state.ease + EASY_EASE_BONUS)
        case _:
            assert_never(grade)

    # is ではなく値で比べる。コード更新でモジュールが読み直されると、同じ AGAIN でも別のオブジェクトになるため
    is_correct = grade != Grade.AGAIN
    return replace(
        state,
        interval_days=interval,
        ease=round(ease, EASE_DECIMALS),
        repetitions=repetitions,
        due=today + timedelta(days=interval),
        first_reviewed=state.first_reviewed or today,
        last_reviewed=today,
        lapses=state.lapses if is_correct else state.lapses + 1,
        total=state.total + 1,
        correct=state.correct + 1 if is_correct else state.correct,
    )


def _hard_interval(state: CardState) -> int:
    if state.repetitions == 0:
        return FIRST_HARD_INTERVAL_DAYS
    grown = max(state.interval_days + 1, round(state.interval_days * HARD_INTERVAL_MULTIPLIER))
    return min(MAX_INTERVAL_DAYS, grown)


def _easy_interval(state: CardState) -> int:
    if state.repetitions == 0:
        return FIRST_EASY_INTERVAL_DAYS
    if state.repetitions == 1:
        return max(SECOND_EASY_INTERVAL_DAYS, state.interval_days + 1)
    grown = max(state.interval_days + 1, round(state.interval_days * state.ease))
    return min(MAX_INTERVAL_DAYS, grown)


def _date_to_text(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None


def _text_to_date(value: Any) -> date | None:
    if value is None:
        return None
    return date.fromisoformat(str(value))
