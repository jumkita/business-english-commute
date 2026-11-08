"""ホーム画面と記録タブに出す学習状況（FR-06）。"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

from english_app.clock import SECONDS_PER_MINUTE
from english_app.content import DOMAIN_LABELS, ContentLibrary
from english_app.dictation import build_dictation_items
from english_app.progress import Progress
from english_app.quiz import QUIZ_DOMAINS, quiz_items
from english_app.session import StudyMode, make_card_id, split_card_id

WEAK_CARD_LIMIT = 10
RECENT_DAYS = 14


@dataclass(frozen=True)
class AreaSummary:
    label: str
    total: int
    studied: int
    mastered: int
    accuracy: float | None


@dataclass(frozen=True)
class WeakCard:
    card_id: str
    mode: StudyMode
    item_id: str
    lapses: int
    accuracy: float | None


@dataclass(frozen=True)
class DailyMinutes:
    day: date
    minutes: float


def all_card_ids(library: ContentLibrary) -> list[str]:
    quiz_card_ids = [make_card_id(StudyMode.QUIZ, item.id) for item in quiz_items(library)]
    dictation_card_ids = [make_card_id(StudyMode.DICTATION, item.item_id) for item in build_dictation_items(library)]
    return [*quiz_card_ids, *dictation_card_ids]


def summarize_areas(library: ContentLibrary, progress: Progress) -> list[AreaSummary]:
    summaries = []
    for domain in QUIZ_DOMAINS:
        card_ids = [make_card_id(StudyMode.QUIZ, item.id) for item in quiz_items(library, domain)]
        summaries.append(_summarize(DOMAIN_LABELS[domain], card_ids, progress))
    dictation_card_ids = [make_card_id(StudyMode.DICTATION, item.item_id) for item in build_dictation_items(library)]
    summaries.append(_summarize("書き取り", dictation_card_ids, progress))
    return summaries


def find_weak_cards(progress: Progress, limit: int = WEAK_CARD_LIMIT) -> list[WeakCard]:
    """一度でも忘れた（もう一度と評価した）問題を、忘れた回数の多い順・正答率の低い順に並べる。"""
    weak_cards = []
    for card_id, state in progress.cards.items():
        if state.lapses == 0:
            continue
        try:
            mode, item_id = split_card_id(card_id)
        except ValueError:
            continue
        accuracy = state.correct / state.total if state.total else None
        weak_cards.append(WeakCard(card_id, mode, item_id, state.lapses, accuracy))
    weak_cards.sort(key=lambda card: (-card.lapses, card.accuracy if card.accuracy is not None else 0.0, card.card_id))
    return weak_cards[:limit]


def recent_daily_minutes(progress: Progress, today: date, days: int = RECENT_DAYS) -> list[DailyMinutes]:
    first_day = today - timedelta(days=days - 1)
    return [
        DailyMinutes(day, progress.stats_for(day).seconds / SECONDS_PER_MINUTE)
        for day in (first_day + timedelta(days=offset) for offset in range(days))
    ]


def _summarize(label: str, card_ids: Iterable[str], progress: Progress) -> AreaSummary:
    card_id_list = list(card_ids)
    studied_states = [progress.cards[card_id] for card_id in card_id_list if card_id in progress.cards]
    total_answers = sum(state.total for state in studied_states)
    correct_answers = sum(state.correct for state in studied_states)
    return AreaSummary(
        label=label,
        total=len(card_id_list),
        studied=len(studied_states),
        mastered=sum(1 for state in studied_states if state.is_mastered),
        accuracy=correct_answers / total_answers if total_answers else None,
    )
