"""学習セッション（時間で区切る）と、次に出す問題の選び方（FR-01・FR-04・FR-05）。"""

from __future__ import annotations

import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import date
from enum import StrEnum

from english_app.srs import CardState

DAILY_NEW_CARD_LIMIT = 20
RETRY_GAP_QUESTIONS = 3
CARD_ID_SEPARATOR = ":"


class StudyMode(StrEnum):
    QUIZ = "quiz"
    DICTATION = "dictation"


def make_card_id(mode: StudyMode, item_id: str) -> str:
    return f"{mode}{CARD_ID_SEPARATOR}{item_id}"


def split_card_id(card_id: str) -> tuple[StudyMode, str]:
    mode, separator, item_id = card_id.partition(CARD_ID_SEPARATOR)
    if not separator or not item_id:
        raise ValueError(f"カード ID の形式が不正です: {card_id}")
    return StudyMode(mode), item_id


@dataclass
class StudySession:
    duration_seconds: int
    started_at: float
    asked: list[str] = field(default_factory=list)
    failed_at: dict[str, int] = field(default_factory=dict)
    answered: int = 0
    correct: int = 0

    def elapsed_seconds(self, now: float) -> float:
        return max(0.0, now - self.started_at)

    def remaining_seconds(self, now: float) -> int:
        return max(0, int(self.duration_seconds - self.elapsed_seconds(now)))

    def is_time_up(self, now: float) -> bool:
        return self.elapsed_seconds(now) >= self.duration_seconds

    def mark_asked(self, card_id: str) -> None:
        self.asked.append(card_id)

    def record_result(self, card_id: str, is_correct: bool) -> None:
        self.answered += 1
        if is_correct:
            self.correct += 1
            self.failed_at.pop(card_id, None)
        else:
            self.failed_at[card_id] = len(self.asked)


def pick_next_card(
    candidates: Sequence[str],
    cards: Mapping[str, CardState],
    today: date,
    session: StudySession,
    new_cards_today: int,
    rng: random.Random,
) -> str | None:
    """出題順: このセッションで間違えた問題 → 復習期限の来た問題 → 新しい問題 → 先取り復習。"""
    if not candidates:
        return None

    retry = _retry_card(candidates, session)
    if retry is not None:
        return retry

    asked = set(session.asked)
    fresh = [card_id for card_id in candidates if card_id not in asked]
    due = [card_id for card_id in fresh if card_id in cards and cards[card_id].is_due(today)]
    if due:
        return min(due, key=lambda card_id: (cards[card_id].due, rng.random()))

    new = [card_id for card_id in fresh if card_id not in cards or cards[card_id].is_new]
    if new and new_cards_today < DAILY_NEW_CARD_LIMIT:
        return rng.choice(new)

    if fresh:
        return min(fresh, key=lambda card_id: (_due_sort_key(cards.get(card_id)), rng.random()))
    return min(candidates, key=lambda card_id: (session.asked.count(card_id), rng.random()))


def _retry_card(candidates: Sequence[str], session: StudySession) -> str | None:
    candidate_set = set(candidates)
    asked_count = len(session.asked)
    for card_id, failed_position in session.failed_at.items():
        if card_id in candidate_set and asked_count - failed_position >= RETRY_GAP_QUESTIONS:
            return card_id
    return None


def _due_sort_key(state: CardState | None) -> date:
    if state is None or state.due is None:
        return date.max
    return state.due
