"""聞き流し（FR-02）の単元とプレイリスト。音声は英語のみ。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from english_app.content import SCENE_LABELS, TAG_LABELS, ContentLibrary
from english_app.explanations import text_for_item_id
from english_app.progress import Progress
from english_app.session import split_card_id

REVIEW_UNIT_ID = "review"


@dataclass(frozen=True)
class Track:
    text: str
    voice: int = 0


@dataclass(frozen=True)
class ListeningUnit:
    id: str
    label: str
    tracks: tuple[Track, ...]


def build_listening_units(library: ContentLibrary) -> list[ListeningUnit]:
    units: list[ListeningUnit] = []
    for rule in library.rules:
        tracks = tuple(Track(item.sentence) for item in library.connected_speech if item.rule_id == rule.id)
        units.append(ListeningUnit(f"connected_speech:{rule.id}", f"音声変化：{rule.name_ja}", tracks))
    for scene, label in SCENE_LABELS.items():
        tracks = tuple(Track(item.phrase_en) for item in library.phrases if item.scene == scene)
        units.append(ListeningUnit(f"phrase:{scene}", f"ビジネス表現：{label}", tracks))
    for tag, label in TAG_LABELS.items():
        tracks = tuple(Track(item.example_en) for item in library.vocabulary if tag in item.tags)
        units.append(ListeningUnit(f"vocabulary:{tag}", f"単語の例文：{label}", tracks))
    for dialogue in library.dialogues:
        speakers = list(dict.fromkeys(line.speaker for line in dialogue.lines))
        tracks = tuple(Track(line.text, voice=speakers.index(line.speaker)) for line in dialogue.lines)
        units.append(ListeningUnit(f"dialogue:{dialogue.id}", f"会話：{dialogue.title}", tracks))
    return [unit for unit in units if unit.tracks]


def build_review_unit(library: ContentLibrary, progress: Progress, today: date) -> ListeningUnit | None:
    """復習期限の来た問題の英文を集める。クイズと書き取りで同じ英文が重なっても1回だけ流す。"""
    texts: list[str] = []
    for card_id, state in sorted(progress.cards.items(), key=lambda entry: entry[1].due or today):
        if not state.is_due(today):
            continue
        try:
            _, item_id = split_card_id(card_id)
        except ValueError:
            continue
        text = text_for_item_id(library, item_id)
        if text is not None and text not in texts:
            texts.append(text)
    if not texts:
        return None
    return ListeningUnit(REVIEW_UNIT_ID, "今日の復習", tuple(Track(text) for text in texts))
