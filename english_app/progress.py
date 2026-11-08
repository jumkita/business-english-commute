"""学習履歴（カードの状態・日別の記録・要確認フラグ）の集計と保存形式。"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Any

from english_app.session import StudyMode, make_card_id
from english_app.srs import CardState, Grade, schedule

PROGRESS_SCHEMA_VERSION = 1
# 電車を降りて放置した時間まで学習時間に数えないための上限
MAX_SECONDS_PER_ANSWER = 90


class ProgressFormatError(ValueError):
    """保存されていた学習履歴の形式が読めないときに送出する。"""


@dataclass
class DailyStats:
    answers: int = 0
    correct: int = 0
    seconds: int = 0

    def to_dict(self) -> dict[str, int]:
        return {"answers": self.answers, "correct": self.correct, "seconds": self.seconds}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> DailyStats:
        return cls(
            answers=int(data.get("answers", 0)),
            correct=int(data.get("correct", 0)),
            seconds=int(data.get("seconds", 0)),
        )


@dataclass
class Progress:
    cards: dict[str, CardState] = field(default_factory=dict)
    daily: dict[date, DailyStats] = field(default_factory=dict)
    flagged_item_ids: set[str] = field(default_factory=set)

    def card(self, card_id: str) -> CardState:
        return self.cards.get(card_id, CardState())

    def record_answer(self, card_id: str, grade: Grade, today: date, elapsed_seconds: float) -> CardState:
        updated = schedule(self.card(card_id), grade, today)
        self.cards[card_id] = updated
        stats = self.daily.setdefault(today, DailyStats())
        stats.answers += 1
        if grade != Grade.AGAIN:
            stats.correct += 1
        stats.seconds += int(min(max(elapsed_seconds, 0.0), MAX_SECONDS_PER_ANSWER))
        return updated

    def due_count(self, card_ids: Iterable[str], today: date) -> int:
        return sum(1 for card_id in card_ids if card_id in self.cards and self.cards[card_id].is_due(today))

    def new_cards_introduced(self, mode: StudyMode, today: date) -> int:
        prefix = make_card_id(mode, "")
        return sum(
            1 for card_id, state in self.cards.items() if card_id.startswith(prefix) and state.first_reviewed == today
        )

    def stats_for(self, day: date) -> DailyStats:
        return self.daily.get(day, DailyStats())

    def streak_days(self, today: date) -> int:
        """今日まだ学習していなくても、昨日まで続いていれば連続記録として数える。"""
        day = today if self._studied_on(today) else today - timedelta(days=1)
        streak = 0
        while self._studied_on(day):
            streak += 1
            day -= timedelta(days=1)
        return streak

    def toggle_flag(self, item_id: str) -> bool:
        if item_id in self.flagged_item_ids:
            self.flagged_item_ids.remove(item_id)
            return False
        self.flagged_item_ids.add(item_id)
        return True

    def _studied_on(self, day: date) -> bool:
        return self.stats_for(day).answers > 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "version": PROGRESS_SCHEMA_VERSION,
            "cards": {card_id: state.to_dict() for card_id, state in sorted(self.cards.items())},
            "daily": {day.isoformat(): stats.to_dict() for day, stats in sorted(self.daily.items())},
            "flagged_item_ids": sorted(self.flagged_item_ids),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> Progress:
        try:
            return cls(
                cards={str(card_id): CardState.from_dict(state) for card_id, state in data.get("cards", {}).items()},
                daily={
                    date.fromisoformat(day): DailyStats.from_dict(stats)
                    for day, stats in data.get("daily", {}).items()
                },
                flagged_item_ids={str(item_id) for item_id in data.get("flagged_item_ids", [])},
            )
        except (AttributeError, TypeError, ValueError) as error:
            raise ProgressFormatError(f"学習履歴の形式が不正です: {error}") from error
