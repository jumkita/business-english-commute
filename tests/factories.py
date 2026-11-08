"""テスト用の小さな学習データを作るヘルパー。"""

from __future__ import annotations

from collections.abc import Sequence

from english_app.content import (
    ConnectedSpeechItem,
    ConnectedSpeechRule,
    ContentLibrary,
    DialogueItem,
    DialogueLine,
    GrammarItem,
    PhraseItem,
    VocabularyItem,
)


def make_vocabulary(
    item_id: str,
    headword: str,
    meaning_ja: str,
    part_of_speech: str = "動詞",
    confusable_group: str | None = None,
    tags: tuple[str, ...] = ("management",),
) -> VocabularyItem:
    return VocabularyItem(
        id=item_id,
        headword=headword,
        part_of_speech=part_of_speech,
        meaning_ja=meaning_ja,
        nuance="ニュアンス",
        collocations=(f"{headword} it",),
        example_en=f"We should {headword} it.",
        example_ja="例文の訳",
        tags=tags,
        confusable_group=confusable_group,
    )


def make_rule(rule_id: str = "linking") -> ConnectedSpeechRule:
    return ConnectedSpeechRule(id=rule_id, name_ja="連結", name_en="Linking", explanation="子音と母音がつながる")


def make_connected_speech(
    item_id: str,
    sentence: str,
    distractors: tuple[str, ...] = ("Distractor one.", "Distractor two."),
    rule_id: str = "linking",
) -> ConnectedSpeechItem:
    return ConnectedSpeechItem(
        id=item_id,
        rule_id=rule_id,
        sentence=sentence,
        meaning_ja="意味",
        sounds_like="カタカナ",
        explanation="解説",
        distractors=distractors,
    )


def make_phrase(item_id: str, phrase_en: str, meaning_ja: str, scene: str = "meeting") -> PhraseItem:
    return PhraseItem(
        id=item_id, scene=scene, phrase_en=phrase_en, meaning_ja=meaning_ja, politeness="neutral", note="メモ"
    )


def make_grammar(item_id: str, options: tuple[str, ...], answer_index: int, topic: str = "politeness") -> GrammarItem:
    return GrammarItem(
        id=item_id,
        topic=topic,
        situation_ja="上司に依頼する場面",
        options=options,
        answer_index=answer_index,
        explanation="解説",
    )


def make_dialogue(dialogue_id: str, lines: Sequence[tuple[str, str]], scene: str = "meeting") -> DialogueItem:
    return DialogueItem(
        id=dialogue_id,
        title="会話のタイトル",
        scene=scene,
        lines=tuple(DialogueLine(speaker=speaker, text=text, meaning_ja="訳") for speaker, text in lines),
    )


def make_library(
    vocabulary: Sequence[VocabularyItem] = (),
    rules: Sequence[ConnectedSpeechRule] = (make_rule(),),
    connected_speech: Sequence[ConnectedSpeechItem] = (),
    phrases: Sequence[PhraseItem] = (),
    grammar: Sequence[GrammarItem] = (),
    dialogues: Sequence[DialogueItem] = (),
) -> ContentLibrary:
    return ContentLibrary(
        vocabulary=tuple(vocabulary),
        rules=tuple(rules),
        connected_speech=tuple(connected_speech),
        phrases=tuple(phrases),
        grammar=tuple(grammar),
        dialogues=tuple(dialogues),
    )
