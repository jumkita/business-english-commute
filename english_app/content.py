"""学習コンテンツ（data/content/*.json）の読み込みと検証。"""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from enum import StrEnum
from functools import cached_property
from pathlib import Path
from typing import Any, ClassVar

CONTENT_DIR = Path(__file__).resolve().parent.parent / "data" / "content"

MIN_DISTRACTORS = 2
MIN_GRAMMAR_OPTIONS = 2
MIN_DIALOGUE_LINES = 2


class ContentError(ValueError):
    """コンテンツ JSON の形式が不正なときに送出する。"""


class Domain(StrEnum):
    VOCABULARY = "vocabulary"
    CONNECTED_SPEECH = "connected_speech"
    PHRASE = "phrase"
    GRAMMAR = "grammar"
    DIALOGUE = "dialogue"


DOMAIN_LABELS: dict[Domain, str] = {
    Domain.VOCABULARY: "ボキャブラリー",
    Domain.CONNECTED_SPEECH: "音声変化",
    Domain.PHRASE: "ビジネス表現",
    Domain.GRAMMAR: "実務文法",
    Domain.DIALOGUE: "会話",
}

SCENE_LABELS: dict[str, str] = {
    "meeting": "会議",
    "presentation": "プレゼン",
    "negotiation": "交渉",
    "email": "メール・チャット",
    "online_meeting": "オンライン会議",
    "small_talk": "雑談",
    "feedback": "フィードバック",
}

TAG_LABELS: dict[str, str] = {
    "meeting": "会議",
    "management": "マネジメント",
    "operations": "業務・オペレーション",
    "finance": "財務・会計",
    "contract": "契約・法務",
    "negotiation": "交渉",
    "communication": "コミュニケーション",
    "hr": "人事・組織",
}

POLITENESS_LABELS: dict[str, str] = {
    "casual": "カジュアル",
    "neutral": "標準",
    "formal": "丁寧",
}

GRAMMAR_TOPIC_LABELS: dict[str, str] = {
    "politeness": "丁寧さ",
    "word_order": "語順",
    "tense": "時制",
    "countability": "可算・不可算",
    "verb_pattern": "動詞の語法",
    "conditional": "仮定法",
    "modal": "助動詞",
    "preposition": "前置詞",
    "article": "冠詞",
    "comparison": "比較",
}


@dataclass(frozen=True)
class VocabularyItem:
    domain: ClassVar[Domain] = Domain.VOCABULARY
    id: str
    headword: str
    part_of_speech: str
    meaning_ja: str
    nuance: str
    collocations: tuple[str, ...]
    example_en: str
    example_ja: str
    tags: tuple[str, ...]
    confusable_group: str | None = None


@dataclass(frozen=True)
class ConnectedSpeechRule:
    id: str
    name_ja: str
    name_en: str
    explanation: str


@dataclass(frozen=True)
class ConnectedSpeechItem:
    domain: ClassVar[Domain] = Domain.CONNECTED_SPEECH
    id: str
    rule_id: str
    sentence: str
    meaning_ja: str
    sounds_like: str
    explanation: str
    distractors: tuple[str, ...]


@dataclass(frozen=True)
class PhraseItem:
    domain: ClassVar[Domain] = Domain.PHRASE
    id: str
    scene: str
    phrase_en: str
    meaning_ja: str
    politeness: str
    note: str


@dataclass(frozen=True)
class GrammarItem:
    domain: ClassVar[Domain] = Domain.GRAMMAR
    id: str
    topic: str
    situation_ja: str
    options: tuple[str, ...]
    answer_index: int
    explanation: str

    @property
    def correct_option(self) -> str:
        return self.options[self.answer_index]


@dataclass(frozen=True)
class DialogueLine:
    speaker: str
    text: str
    meaning_ja: str


@dataclass(frozen=True)
class DialogueItem:
    domain: ClassVar[Domain] = Domain.DIALOGUE
    id: str
    title: str
    scene: str
    lines: tuple[DialogueLine, ...]


StudyItem = VocabularyItem | ConnectedSpeechItem | PhraseItem | GrammarItem | DialogueItem


def dialogue_line_id(dialogue_id: str, line_index: int) -> str:
    return f"{dialogue_id}-{line_index + 1}"


@dataclass(frozen=True)
class ContentLibrary:
    vocabulary: tuple[VocabularyItem, ...]
    rules: tuple[ConnectedSpeechRule, ...]
    connected_speech: tuple[ConnectedSpeechItem, ...]
    phrases: tuple[PhraseItem, ...]
    grammar: tuple[GrammarItem, ...]
    dialogues: tuple[DialogueItem, ...]

    @cached_property
    def items_by_id(self) -> dict[str, StudyItem]:
        items: list[StudyItem] = [
            *self.vocabulary,
            *self.connected_speech,
            *self.phrases,
            *self.grammar,
            *self.dialogues,
        ]
        return {item.id: item for item in items}

    @cached_property
    def dialogue_lines_by_id(self) -> dict[str, tuple[DialogueItem, int]]:
        return {
            dialogue_line_id(dialogue.id, index): (dialogue, index)
            for dialogue in self.dialogues
            for index in range(len(dialogue.lines))
        }

    def rule_by_id(self, rule_id: str) -> ConnectedSpeechRule:
        for rule in self.rules:
            if rule.id == rule_id:
                return rule
        raise KeyError(rule_id)


class _RecordReader:
    """1件分の JSON レコードから、型を確かめながら値を取り出す。"""

    def __init__(self, record: Any, source: str) -> None:
        if not isinstance(record, dict):
            raise ContentError(f"{source}: 各要素はオブジェクトである必要があります")
        self._record = record
        self._source = source

    def _raw(self, key: str) -> Any:
        if key not in self._record:
            item_id = self._record.get("id", "?")
            raise ContentError(f"{self._source}: '{key}' がありません（id={item_id}）")
        return self._record[key]

    def _error(self, key: str, expected: str) -> ContentError:
        item_id = self._record.get("id", "?")
        return ContentError(f"{self._source}: '{key}' は{expected}である必要があります（id={item_id}）")

    def text(self, key: str) -> str:
        value = self._raw(key)
        if not isinstance(value, str) or not value.strip():
            raise self._error(key, "空でない文字列")
        return value

    def optional_text(self, key: str) -> str | None:
        if self._record.get(key) is None:
            return None
        return self.text(key)

    def texts(self, key: str) -> tuple[str, ...]:
        value = self._raw(key)
        if not isinstance(value, list) or not all(isinstance(entry, str) and entry.strip() for entry in value):
            raise self._error(key, "空でない文字列の配列")
        return tuple(value)

    def integer(self, key: str) -> int:
        value = self._raw(key)
        if not isinstance(value, int) or isinstance(value, bool):
            raise self._error(key, "整数")
        return value

    def records(self, key: str) -> list[Any]:
        value = self._raw(key)
        if not isinstance(value, list):
            raise self._error(key, "配列")
        return value


def _read_records(path: Path) -> list[Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ContentError(f"{path.name} が見つかりません") from error
    except json.JSONDecodeError as error:
        raise ContentError(f"{path.name} の JSON が不正です: {error}") from error
    if not isinstance(data, list):
        raise ContentError(f"{path.name} は配列である必要があります")
    return data


def _readers(path: Path) -> list[_RecordReader]:
    return [_RecordReader(record, path.name) for record in _read_records(path)]


def _parse_vocabulary(reader: _RecordReader) -> VocabularyItem:
    return VocabularyItem(
        id=reader.text("id"),
        headword=reader.text("headword"),
        part_of_speech=reader.text("part_of_speech"),
        meaning_ja=reader.text("meaning_ja"),
        nuance=reader.text("nuance"),
        collocations=reader.texts("collocations"),
        example_en=reader.text("example_en"),
        example_ja=reader.text("example_ja"),
        tags=reader.texts("tags"),
        confusable_group=reader.optional_text("confusable_group"),
    )


def _parse_rule(reader: _RecordReader) -> ConnectedSpeechRule:
    return ConnectedSpeechRule(
        id=reader.text("id"),
        name_ja=reader.text("name_ja"),
        name_en=reader.text("name_en"),
        explanation=reader.text("explanation"),
    )


def _parse_connected_speech(reader: _RecordReader) -> ConnectedSpeechItem:
    return ConnectedSpeechItem(
        id=reader.text("id"),
        rule_id=reader.text("rule_id"),
        sentence=reader.text("sentence"),
        meaning_ja=reader.text("meaning_ja"),
        sounds_like=reader.text("sounds_like"),
        explanation=reader.text("explanation"),
        distractors=reader.texts("distractors"),
    )


def _parse_phrase(reader: _RecordReader) -> PhraseItem:
    return PhraseItem(
        id=reader.text("id"),
        scene=reader.text("scene"),
        phrase_en=reader.text("phrase_en"),
        meaning_ja=reader.text("meaning_ja"),
        politeness=reader.text("politeness"),
        note=reader.text("note"),
    )


def _parse_grammar(reader: _RecordReader) -> GrammarItem:
    return GrammarItem(
        id=reader.text("id"),
        topic=reader.text("topic"),
        situation_ja=reader.text("situation_ja"),
        options=reader.texts("options"),
        answer_index=reader.integer("answer_index"),
        explanation=reader.text("explanation"),
    )


def _parse_dialogue(reader: _RecordReader) -> DialogueItem:
    dialogue_id = reader.text("id")
    lines = []
    for record in reader.records("lines"):
        line_reader = _RecordReader(record, f"dialogues.json（{dialogue_id}）")
        lines.append(
            DialogueLine(
                speaker=line_reader.text("speaker"),
                text=line_reader.text("text"),
                meaning_ja=line_reader.text("meaning_ja"),
            )
        )
    return DialogueItem(
        id=dialogue_id,
        title=reader.text("title"),
        scene=reader.text("scene"),
        lines=tuple(lines),
    )


def load_library(content_dir: Path = CONTENT_DIR) -> ContentLibrary:
    return ContentLibrary(
        vocabulary=tuple(_parse_vocabulary(r) for r in _readers(content_dir / "vocabulary.json")),
        rules=tuple(_parse_rule(r) for r in _readers(content_dir / "connected_speech_rules.json")),
        connected_speech=tuple(_parse_connected_speech(r) for r in _readers(content_dir / "connected_speech.json")),
        phrases=tuple(_parse_phrase(r) for r in _readers(content_dir / "phrases.json")),
        grammar=tuple(_parse_grammar(r) for r in _readers(content_dir / "grammar.json")),
        dialogues=tuple(_parse_dialogue(r) for r in _readers(content_dir / "dialogues.json")),
    )


def validate_library(library: ContentLibrary) -> list[str]:
    """ファイル間の整合性を検証し、問題点を日本語のメッセージで返す（問題がなければ空）。"""
    return [
        *_duplicate_id_errors(library),
        *_vocabulary_errors(library),
        *_connected_speech_errors(library),
        *_phrase_errors(library),
        *_grammar_errors(library),
        *_dialogue_errors(library),
    ]


def _duplicate_id_errors(library: ContentLibrary) -> list[str]:
    item_ids = [
        item.id
        for item in (
            *library.vocabulary,
            *library.connected_speech,
            *library.phrases,
            *library.grammar,
            *library.dialogues,
        )
    ]
    item_ids += list(library.dialogue_lines_by_id)
    errors = [f"ID が重複しています: {item_id}" for item_id, count in Counter(item_ids).items() if count > 1]
    rule_counts = Counter(rule.id for rule in library.rules)
    errors += [f"音声変化の規則 ID が重複しています: {rule_id}" for rule_id, count in rule_counts.items() if count > 1]
    return errors


def _vocabulary_errors(library: ContentLibrary) -> list[str]:
    errors = []
    for item in library.vocabulary:
        errors += [f"{item.id}: 未知のタグ '{tag}'" for tag in item.tags if tag not in TAG_LABELS]
        if not item.tags:
            errors.append(f"{item.id}: タグが空です")
    return errors


def _connected_speech_errors(library: ContentLibrary) -> list[str]:
    rule_ids = {rule.id for rule in library.rules}
    errors = []
    for item in library.connected_speech:
        if item.rule_id not in rule_ids:
            errors.append(f"{item.id}: 未知の規則 '{item.rule_id}'")
        if len(item.distractors) < MIN_DISTRACTORS:
            errors.append(f"{item.id}: 紛らわしい選択肢は {MIN_DISTRACTORS} 件以上必要です")
        if item.sentence in item.distractors:
            errors.append(f"{item.id}: 正解の文が紛らわしい選択肢に含まれています")
        if len(set(item.distractors)) != len(item.distractors):
            errors.append(f"{item.id}: 紛らわしい選択肢が重複しています")
    return errors


def _phrase_errors(library: ContentLibrary) -> list[str]:
    errors = []
    for item in library.phrases:
        if item.scene not in SCENE_LABELS:
            errors.append(f"{item.id}: 未知の場面 '{item.scene}'")
        if item.politeness not in POLITENESS_LABELS:
            errors.append(f"{item.id}: 未知の丁寧さ '{item.politeness}'")
    return errors


def _grammar_errors(library: ContentLibrary) -> list[str]:
    errors = []
    for item in library.grammar:
        if item.topic not in GRAMMAR_TOPIC_LABELS:
            errors.append(f"{item.id}: 未知のトピック '{item.topic}'")
        if len(item.options) < MIN_GRAMMAR_OPTIONS:
            errors.append(f"{item.id}: 選択肢は {MIN_GRAMMAR_OPTIONS} 件以上必要です")
        if len(set(item.options)) != len(item.options):
            errors.append(f"{item.id}: 選択肢が重複しています")
        if not 0 <= item.answer_index < len(item.options):
            errors.append(f"{item.id}: answer_index が選択肢の範囲外です")
    return errors


def _dialogue_errors(library: ContentLibrary) -> list[str]:
    errors = []
    for dialogue in library.dialogues:
        if dialogue.scene not in SCENE_LABELS:
            errors.append(f"{dialogue.id}: 未知の場面 '{dialogue.scene}'")
        if len(dialogue.lines) < MIN_DIALOGUE_LINES:
            errors.append(f"{dialogue.id}: 会話は {MIN_DIALOGUE_LINES} 行以上必要です")
    return errors
