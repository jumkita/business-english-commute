import pytest

from english_app.content import Domain, load_library
from english_app.dictation import build_dictation_items, grade_for_verdict, hint_for
from english_app.srs import Grade
from english_app.text_match import Verdict
from tests.factories import make_connected_speech, make_dialogue, make_library, make_phrase


def test_builds_items_from_sentences_phrases_and_dialogue_lines():
    library = make_library(
        connected_speech=[make_connected_speech("cs-1", "Check it out.")],
        phrases=[make_phrase("ph-1", "Let's get started.", "始めましょう")],
        dialogues=[make_dialogue("dlg-1", [("Emma", "Hi, Ken."), ("Ken", "Hi, Emma.")])],
    )
    items = build_dictation_items(library)
    assert [item.item_id for item in items] == ["cs-1", "ph-1", "dlg-1-1", "dlg-1-2"]
    assert items[3].text == "Hi, Emma."
    assert "2/2" in items[3].source_label


def test_filters_by_domain():
    items = build_dictation_items(load_library(), Domain.DIALOGUE)
    assert items
    assert {item.domain for item in items} == {Domain.DIALOGUE}


def test_item_ids_are_unique_in_bundled_content():
    items = build_dictation_items(load_library())
    assert len({item.item_id for item in items}) == len(items)


@pytest.mark.parametrize(
    ("verdict", "grade"),
    [(Verdict.CORRECT, Grade.EASY), (Verdict.CLOSE, Grade.HARD), (Verdict.INCORRECT, Grade.AGAIN)],
)
def test_grade_for_verdict(verdict, grade):
    assert grade_for_verdict(verdict) is grade


def test_hint_keeps_first_letters_and_punctuation():
    assert hint_for("Let's touch base next week.") == "L__'_ t____ b___ n___ w___."
    assert hint_for("It's 10% off.") == "I_'_ 1_% o__."
