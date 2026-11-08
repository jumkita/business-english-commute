"""各項目の解説（Markdown）と、表示名・読み上げ用の英文。クイズ・ディクテーション・辞書で共通に使う。"""

from __future__ import annotations

from typing import assert_never

from english_app.content import (
    GRAMMAR_TOPIC_LABELS,
    POLITENESS_LABELS,
    SCENE_LABELS,
    ConnectedSpeechItem,
    ConnectedSpeechRule,
    ContentLibrary,
    DialogueItem,
    GrammarItem,
    PhraseItem,
    StudyItem,
    VocabularyItem,
)


def vocabulary_markdown(item: VocabularyItem) -> str:
    collocations = " / ".join(item.collocations)
    return (
        f"**{item.headword}**（{item.part_of_speech}）{item.meaning_ja}\n\n"
        f"{item.nuance}\n\n"
        f"- よく使う組み合わせ: {collocations}\n"
        f"- 例文: {item.example_en}\n"
        f"- 訳: {item.example_ja}"
    )


def phrase_markdown(item: PhraseItem) -> str:
    return (
        f"**{item.phrase_en}**\n\n"
        f"{item.meaning_ja}（{SCENE_LABELS[item.scene]}・{POLITENESS_LABELS[item.politeness]}）\n\n"
        f"{item.note}"
    )


def connected_speech_markdown(item: ConnectedSpeechItem, rule: ConnectedSpeechRule) -> str:
    return (
        f"**{rule.name_ja}**（{rule.name_en}）\n\n"
        f"- 英文: {item.sentence}\n"
        f"- 聞こえ方: {item.sounds_like}\n"
        f"- 訳: {item.meaning_ja}\n\n"
        f"{item.explanation}"
    )


def grammar_markdown(item: GrammarItem) -> str:
    return (
        f"**{GRAMMAR_TOPIC_LABELS[item.topic]}**\n\n"
        f"- 正解: {item.correct_option}\n\n"
        f"{item.explanation}"
    )


def dialogue_markdown(item: DialogueItem) -> str:
    lines = [f"- **{line.speaker}**: {line.text}  \n  {line.meaning_ja}" for line in item.lines]
    return f"**{item.title}**（{SCENE_LABELS[item.scene]}）\n\n" + "\n".join(lines)


def item_markdown(library: ContentLibrary, item: StudyItem) -> str:
    match item:
        case VocabularyItem():
            return vocabulary_markdown(item)
        case PhraseItem():
            return phrase_markdown(item)
        case ConnectedSpeechItem():
            return connected_speech_markdown(item, library.rule_by_id(item.rule_id))
        case GrammarItem():
            return grammar_markdown(item)
        case DialogueItem():
            return dialogue_markdown(item)
        case _:
            assert_never(item)


def item_title(item: StudyItem) -> str:
    match item:
        case VocabularyItem():
            return item.headword
        case PhraseItem():
            return item.phrase_en
        case ConnectedSpeechItem():
            return item.sentence
        case GrammarItem():
            return item.situation_ja
        case DialogueItem():
            return item.title
        case _:
            assert_never(item)


def item_subtitle(item: StudyItem) -> str:
    match item:
        case VocabularyItem() | PhraseItem() | ConnectedSpeechItem():
            return item.meaning_ja
        case GrammarItem():
            return GRAMMAR_TOPIC_LABELS[item.topic]
        case DialogueItem():
            return SCENE_LABELS[item.scene]
        case _:
            assert_never(item)


def item_audio_text(item: StudyItem) -> str:
    match item:
        case VocabularyItem():
            return item.example_en
        case PhraseItem():
            return item.phrase_en
        case ConnectedSpeechItem():
            return item.sentence
        case GrammarItem():
            return item.correct_option
        case DialogueItem():
            return " ".join(line.text for line in item.lines)
        case _:
            assert_never(item)


def title_for_item_id(library: ContentLibrary, item_id: str) -> str | None:
    item = library.items_by_id.get(item_id)
    if item is not None:
        return item_title(item)
    return text_for_item_id(library, item_id)


def text_for_item_id(library: ContentLibrary, item_id: str) -> str | None:
    """学習履歴に残っている ID から読み上げ用の英文を引く。会話の1行ごとの ID にも対応する。"""
    item = library.items_by_id.get(item_id)
    if item is not None:
        return item_audio_text(item)
    line_location = library.dialogue_lines_by_id.get(item_id)
    if line_location is None:
        return None
    dialogue, line_index = line_location
    return dialogue.lines[line_index].text
