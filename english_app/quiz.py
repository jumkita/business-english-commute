"""タップ式クイズの問題生成（FR-01）。"""

from __future__ import annotations

import random
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import TypeVar, assert_never

from english_app.content import (
    ConnectedSpeechItem,
    ContentLibrary,
    Domain,
    GrammarItem,
    PhraseItem,
    VocabularyItem,
)
from english_app.explanations import (
    connected_speech_markdown,
    grammar_markdown,
    phrase_markdown,
    vocabulary_markdown,
)

NUM_CHOICES = 4
QUIZ_DOMAINS = (Domain.VOCABULARY, Domain.CONNECTED_SPEECH, Domain.PHRASE, Domain.GRAMMAR)

QuizItem = VocabularyItem | PhraseItem | ConnectedSpeechItem | GrammarItem
PoolItem = TypeVar("PoolItem")


class QuestionKind(StrEnum):
    MEANING_FROM_ENGLISH = "meaning_from_english"
    ENGLISH_FROM_MEANING = "english_from_meaning"
    MEANING_FROM_AUDIO = "meaning_from_audio"
    SENTENCE_FROM_AUDIO = "sentence_from_audio"
    BETTER_EXPRESSION = "better_expression"


QUESTION_KIND_LABELS: dict[QuestionKind, str] = {
    QuestionKind.MEANING_FROM_ENGLISH: "英→日",
    QuestionKind.ENGLISH_FROM_MEANING: "日→英",
    QuestionKind.MEANING_FROM_AUDIO: "音声→意味",
    QuestionKind.SENTENCE_FROM_AUDIO: "聞き取り",
    QuestionKind.BETTER_EXPRESSION: "自然さ・丁寧さ",
}

_WORD_AND_PHRASE_KINDS = (
    QuestionKind.MEANING_FROM_ENGLISH,
    QuestionKind.ENGLISH_FROM_MEANING,
    QuestionKind.MEANING_FROM_AUDIO,
)


@dataclass(frozen=True)
class Question:
    item_id: str
    domain: Domain
    kind: QuestionKind
    instruction: str
    prompt: str
    audio_text: str | None
    choices: tuple[str, ...]
    answer_index: int
    explanation_markdown: str
    review_audio_text: str

    @property
    def correct_choice(self) -> str:
        return self.choices[self.answer_index]

    def is_correct(self, choice_index: int) -> bool:
        return choice_index == self.answer_index


def quiz_items(library: ContentLibrary, domain: Domain | None = None) -> list[QuizItem]:
    items: list[QuizItem] = [*library.vocabulary, *library.connected_speech, *library.phrases, *library.grammar]
    if domain is None:
        return items
    return [item for item in items if item.domain == domain]


def build_question(item: QuizItem, library: ContentLibrary, rng: random.Random) -> Question:
    match item:
        case VocabularyItem():
            return _vocabulary_question(item, library, rng)
        case PhraseItem():
            return _phrase_question(item, library, rng)
        case ConnectedSpeechItem():
            return _connected_speech_question(item, library, rng)
        case GrammarItem():
            return _grammar_question(item, rng)
        case _:
            assert_never(item)


def _vocabulary_question(item: VocabularyItem, library: ContentLibrary, rng: random.Random) -> Question:
    # 同じ confusable_group の語は意味が近く正解が2つに見えるため、誤答の候補から外す
    pool = [
        other
        for other in library.vocabulary
        if other.id != item.id and (item.confusable_group is None or other.confusable_group != item.confusable_group)
    ]

    def same_part_of_speech(other: VocabularyItem) -> bool:
        return other.part_of_speech == item.part_of_speech

    kind = rng.choice(_WORD_AND_PHRASE_KINDS)
    match kind:
        case QuestionKind.MEANING_FROM_ENGLISH | QuestionKind.MEANING_FROM_AUDIO:
            correct = item.meaning_ja
            distractors = _pick_distractors(correct, pool, lambda other: other.meaning_ja, same_part_of_speech, rng)
        case QuestionKind.ENGLISH_FROM_MEANING:
            correct = item.headword
            distractors = _pick_distractors(correct, pool, lambda other: other.headword, same_part_of_speech, rng)
        case QuestionKind.SENTENCE_FROM_AUDIO | QuestionKind.BETTER_EXPRESSION:
            raise ValueError(f"単語では使わない出題形式です: {kind}")
        case _:
            assert_never(kind)
    choices, answer_index = _shuffle_choices(correct, distractors, rng)
    instruction, prompt, audio_text = _word_or_phrase_presentation(kind, item.headword, item.meaning_ja)
    return Question(
        item_id=item.id,
        domain=item.domain,
        kind=kind,
        instruction=instruction,
        prompt=prompt,
        audio_text=audio_text,
        choices=choices,
        answer_index=answer_index,
        explanation_markdown=vocabulary_markdown(item),
        review_audio_text=item.example_en,
    )


def _phrase_question(item: PhraseItem, library: ContentLibrary, rng: random.Random) -> Question:
    pool = [other for other in library.phrases if other.id != item.id]

    def same_scene(other: PhraseItem) -> bool:
        return other.scene == item.scene

    kind = rng.choice(_WORD_AND_PHRASE_KINDS)
    match kind:
        case QuestionKind.MEANING_FROM_ENGLISH | QuestionKind.MEANING_FROM_AUDIO:
            correct = item.meaning_ja
            distractors = _pick_distractors(correct, pool, lambda other: other.meaning_ja, same_scene, rng)
        case QuestionKind.ENGLISH_FROM_MEANING:
            correct = item.phrase_en
            distractors = _pick_distractors(correct, pool, lambda other: other.phrase_en, same_scene, rng)
        case QuestionKind.SENTENCE_FROM_AUDIO | QuestionKind.BETTER_EXPRESSION:
            raise ValueError(f"表現では使わない出題形式です: {kind}")
        case _:
            assert_never(kind)
    choices, answer_index = _shuffle_choices(correct, distractors, rng)
    instruction, prompt, audio_text = _word_or_phrase_presentation(kind, item.phrase_en, item.meaning_ja)
    return Question(
        item_id=item.id,
        domain=item.domain,
        kind=kind,
        instruction=instruction,
        prompt=prompt,
        audio_text=audio_text,
        choices=choices,
        answer_index=answer_index,
        explanation_markdown=phrase_markdown(item),
        review_audio_text=item.phrase_en,
    )


def _connected_speech_question(item: ConnectedSpeechItem, library: ContentLibrary, rng: random.Random) -> Question:
    distractors = list(item.distractors[: NUM_CHOICES - 1])
    choices, answer_index = _shuffle_choices(item.sentence, distractors, rng)
    return Question(
        item_id=item.id,
        domain=item.domain,
        kind=QuestionKind.SENTENCE_FROM_AUDIO,
        instruction="音声を聞いて、実際に言われた英文を選んでください",
        prompt="",
        audio_text=item.sentence,
        choices=choices,
        answer_index=answer_index,
        explanation_markdown=connected_speech_markdown(item, library.rule_by_id(item.rule_id)),
        review_audio_text=item.sentence,
    )


def _grammar_question(item: GrammarItem, rng: random.Random) -> Question:
    distractors = [option for index, option in enumerate(item.options) if index != item.answer_index]
    choices, answer_index = _shuffle_choices(item.correct_option, distractors, rng)
    return Question(
        item_id=item.id,
        domain=item.domain,
        kind=QuestionKind.BETTER_EXPRESSION,
        instruction="場面に合う表現を選んでください",
        prompt=item.situation_ja,
        audio_text=None,
        choices=choices,
        answer_index=answer_index,
        explanation_markdown=grammar_markdown(item),
        review_audio_text=item.correct_option,
    )


def _word_or_phrase_presentation(kind: QuestionKind, english: str, meaning: str) -> tuple[str, str, str | None]:
    """出題形式ごとの (指示文, 大きく表示する文, 読み上げる英文) を返す。"""
    match kind:
        case QuestionKind.MEANING_FROM_ENGLISH:
            return "意味を選んでください", english, english
        case QuestionKind.ENGLISH_FROM_MEANING:
            return "英語を選んでください", meaning, None
        case QuestionKind.MEANING_FROM_AUDIO:
            return "音声を聞いて、意味を選んでください", "", english
        case QuestionKind.SENTENCE_FROM_AUDIO | QuestionKind.BETTER_EXPRESSION:
            raise ValueError(f"単語・表現では使わない出題形式です: {kind}")
        case _:
            assert_never(kind)


def _pick_distractors(
    correct: str,
    pool: Sequence[PoolItem],
    text_of: Callable[[PoolItem], str],
    is_preferred: Callable[[PoolItem], bool],
    rng: random.Random,
    count: int = NUM_CHOICES - 1,
) -> list[str]:
    preferred = [text_of(entry) for entry in pool if is_preferred(entry)]
    others = [text_of(entry) for entry in pool if not is_preferred(entry)]
    rng.shuffle(preferred)
    rng.shuffle(others)
    distractors: list[str] = []
    for text in [*preferred, *others]:
        if text != correct and text not in distractors:
            distractors.append(text)
        if len(distractors) == count:
            break
    return distractors


def _shuffle_choices(correct: str, distractors: Sequence[str], rng: random.Random) -> tuple[tuple[str, ...], int]:
    choices = [correct, *distractors]
    rng.shuffle(choices)
    return tuple(choices), choices.index(correct)
