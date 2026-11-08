"""ディクテーション（FR-10）の出題データと採点結果の扱い。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import assert_never

from english_app.content import SCENE_LABELS, ContentLibrary, Domain, dialogue_line_id
from english_app.explanations import connected_speech_markdown, dialogue_markdown, phrase_markdown
from english_app.srs import Grade
from english_app.text_match import Verdict

DICTATION_DOMAINS = (Domain.CONNECTED_SPEECH, Domain.PHRASE, Domain.DIALOGUE)
HINT_MASK = "_"


@dataclass(frozen=True)
class DictationItem:
    item_id: str
    domain: Domain
    text: str
    meaning_ja: str
    source_label: str
    explanation_markdown: str


def build_dictation_items(library: ContentLibrary, domain: Domain | None = None) -> list[DictationItem]:
    items = [
        *_connected_speech_items(library),
        *_phrase_items(library),
        *_dialogue_items(library),
    ]
    if domain is None:
        return items
    return [item for item in items if item.domain == domain]


def _connected_speech_items(library: ContentLibrary) -> list[DictationItem]:
    items = []
    for entry in library.connected_speech:
        rule = library.rule_by_id(entry.rule_id)
        items.append(
            DictationItem(
                item_id=entry.id,
                domain=Domain.CONNECTED_SPEECH,
                text=entry.sentence,
                meaning_ja=entry.meaning_ja,
                source_label=f"音声変化：{rule.name_ja}",
                explanation_markdown=connected_speech_markdown(entry, rule),
            )
        )
    return items


def _phrase_items(library: ContentLibrary) -> list[DictationItem]:
    return [
        DictationItem(
            item_id=entry.id,
            domain=Domain.PHRASE,
            text=entry.phrase_en,
            meaning_ja=entry.meaning_ja,
            source_label=f"ビジネス表現：{SCENE_LABELS[entry.scene]}",
            explanation_markdown=phrase_markdown(entry),
        )
        for entry in library.phrases
    ]


def _dialogue_items(library: ContentLibrary) -> list[DictationItem]:
    items = []
    for dialogue in library.dialogues:
        context = dialogue_markdown(dialogue)
        for index, line in enumerate(dialogue.lines):
            items.append(
                DictationItem(
                    item_id=dialogue_line_id(dialogue.id, index),
                    domain=Domain.DIALOGUE,
                    text=line.text,
                    meaning_ja=line.meaning_ja,
                    source_label=f"会話：{dialogue.title}（{index + 1}/{len(dialogue.lines)}）",
                    explanation_markdown=context,
                )
            )
    return items


def grade_for_verdict(verdict: Verdict) -> Grade:
    match verdict:
        case Verdict.CORRECT:
            return Grade.EASY
        case Verdict.CLOSE:
            return Grade.HARD
        case Verdict.INCORRECT:
            return Grade.AGAIN
        case _:
            assert_never(verdict)


def hint_for(text: str) -> str:
    """各単語の頭文字だけを残したヒント。例: "Let's meet." → "L__'_ m___." """
    return " ".join(_mask_word(word) for word in text.split())


def _mask_word(word: str) -> str:
    masked = []
    seen_first_letter = False
    for char in word:
        if char.isalnum():
            masked.append(HINT_MASK if seen_first_letter else char)
            seen_first_letter = True
        else:
            masked.append(char)
    return "".join(masked)
