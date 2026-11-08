import re
from datetime import date

from english_app.content import load_library
from english_app.listening import REVIEW_UNIT_ID, build_listening_units, build_review_unit
from english_app.progress import Progress
from english_app.session import StudyMode, make_card_id
from english_app.srs import Grade
from tests.factories import make_dialogue, make_library

TODAY = date(2026, 11, 8)
JAPANESE_CHARACTERS = re.compile(r"[\u3040-\u30ff\u4e00-\u9fff]")


def test_units_contain_english_only():
    for unit in build_listening_units(load_library()):
        assert unit.tracks
        for track in unit.tracks:
            assert JAPANESE_CHARACTERS.search(track.text) is None, track.text


def test_dialogue_speakers_get_different_voices():
    dialogue = make_dialogue("dlg-1", [("Emma", "Hi."), ("Ken", "Hello."), ("Emma", "Shall we start?")])
    units = build_listening_units(make_library(dialogues=[dialogue]))
    dialogue_unit = next(unit for unit in units if unit.id == "dialogue:dlg-1")
    assert [track.voice for track in dialogue_unit.tracks] == [0, 1, 0]


def test_review_unit_collects_due_sentences_once():
    library = load_library()
    progress = Progress()
    item = library.connected_speech[0]
    progress.record_answer(make_card_id(StudyMode.QUIZ, item.id), Grade.AGAIN, TODAY, elapsed_seconds=1)
    progress.record_answer(make_card_id(StudyMode.DICTATION, item.id), Grade.AGAIN, TODAY, elapsed_seconds=1)
    progress.record_answer(make_card_id(StudyMode.DICTATION, "dlg-001-1"), Grade.AGAIN, TODAY, elapsed_seconds=1)
    progress.record_answer(make_card_id(StudyMode.QUIZ, library.phrases[0].id), Grade.EASY, TODAY, elapsed_seconds=1)
    unit = build_review_unit(library, progress, TODAY)
    assert unit is not None
    assert unit.id == REVIEW_UNIT_ID
    assert [track.text for track in unit.tracks] == [item.sentence, library.dialogues[0].lines[0].text]


def test_no_review_unit_without_due_cards():
    assert build_review_unit(load_library(), Progress(), TODAY) is None
