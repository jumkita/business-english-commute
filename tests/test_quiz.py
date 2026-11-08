import random

import pytest

from english_app.content import load_library
from english_app.quiz import NUM_CHOICES, QuestionKind, build_question, quiz_items
from tests.factories import make_connected_speech, make_grammar, make_library, make_phrase, make_vocabulary

SEEDS = range(30)


@pytest.fixture(scope="module")
def bundled_library():
    return load_library()


def test_every_bundled_item_builds_valid_questions(bundled_library):
    rng = random.Random(0)
    for item in quiz_items(bundled_library):
        for _ in range(5):
            question = build_question(item, bundled_library, rng)
            assert len(set(question.choices)) == len(question.choices), item.id
            assert question.choices[question.answer_index] == question.correct_choice
            assert 2 <= len(question.choices) <= NUM_CHOICES


def test_vocabulary_distractors_exclude_same_confusable_group():
    library = make_library(
        vocabulary=[
            make_vocabulary("v1", "implement", "実行する", confusable_group="introduce"),
            make_vocabulary("v2", "roll out", "展開する", confusable_group="introduce"),
            make_vocabulary("v3", "allocate", "割り当てる"),
            make_vocabulary("v4", "delegate", "任せる"),
            make_vocabulary("v5", "defer", "延期する"),
        ]
    )
    for seed in SEEDS:
        question = build_question(library.vocabulary[0], library, random.Random(seed))
        assert "展開する" not in question.choices
        assert "roll out" not in question.choices


def test_vocabulary_prefers_same_part_of_speech():
    library = make_library(
        vocabulary=[
            make_vocabulary("v1", "allocate", "割り当てる"),
            make_vocabulary("v2", "delegate", "任せる"),
            make_vocabulary("v3", "defer", "延期する"),
            make_vocabulary("v4", "endorse", "支持する"),
            make_vocabulary("v5", "prerequisite", "前提条件", part_of_speech="名詞"),
        ]
    )
    for seed in SEEDS:
        question = build_question(library.vocabulary[0], library, random.Random(seed))
        assert "前提条件" not in question.choices
        assert "prerequisite" not in question.choices


def test_english_from_meaning_does_not_play_the_answer():
    library = make_library(
        phrases=[make_phrase(f"p{index}", f"Phrase {index}.", f"意味{index}") for index in range(5)]
    )
    kinds = set()
    for seed in SEEDS:
        question = build_question(library.phrases[0], library, random.Random(seed))
        kinds.add(question.kind)
        if question.kind is QuestionKind.ENGLISH_FROM_MEANING:
            assert question.audio_text is None
            assert question.prompt == "意味0"
        if question.kind is QuestionKind.MEANING_FROM_AUDIO:
            assert question.prompt == ""
            assert question.audio_text == "Phrase 0."
    assert kinds == {
        QuestionKind.MEANING_FROM_ENGLISH,
        QuestionKind.ENGLISH_FROM_MEANING,
        QuestionKind.MEANING_FROM_AUDIO,
    }


def test_connected_speech_question_hides_sentence():
    item = make_connected_speech("c1", "Check it out.", distractors=("Check out.", "Check it.", "Checked it out."))
    library = make_library(connected_speech=[item])
    question = build_question(item, library, random.Random(0))
    assert question.kind is QuestionKind.SENTENCE_FROM_AUDIO
    assert question.audio_text == "Check it out."
    assert question.prompt == ""
    assert question.correct_choice == "Check it out."
    assert len(question.choices) == NUM_CHOICES


def test_grammar_question_uses_options():
    item = make_grammar("g1", ("Could you possibly review this?", "Review this."), answer_index=0)
    question = build_question(item, make_library(grammar=[item]), random.Random(0))
    assert question.kind is QuestionKind.BETTER_EXPRESSION
    assert question.audio_text is None
    assert question.correct_choice == "Could you possibly review this?"
    assert question.is_correct(question.answer_index)
    assert not question.is_correct(1 - question.answer_index)
