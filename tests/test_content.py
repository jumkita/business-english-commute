import json
import shutil

import pytest

from english_app.content import CONTENT_DIR, ContentError, Domain, load_library, validate_library
from tests.factories import make_connected_speech, make_dialogue, make_grammar, make_library, make_vocabulary


def test_bundled_content_is_valid():
    library = load_library()
    assert validate_library(library) == []
    for domain_items in (
        library.vocabulary,
        library.connected_speech,
        library.phrases,
        library.grammar,
        library.dialogues,
    ):
        assert domain_items


def test_items_by_id_covers_every_domain():
    library = load_library()
    domains = {item.domain for item in library.items_by_id.values()}
    assert domains == set(Domain)


def test_dialogue_line_ids_point_to_lines():
    dialogue = make_dialogue("dlg-1", [("A", "Hi."), ("B", "Hello.")])
    library = make_library(dialogues=[dialogue])
    assert library.dialogue_lines_by_id["dlg-1-2"] == (dialogue, 1)


def test_detects_duplicate_ids():
    library = make_library(
        vocabulary=[make_vocabulary("dup", "allocate", "割り当てる"), make_vocabulary("dup", "defer", "延期する")]
    )
    assert any("dup" in error for error in validate_library(library))


def test_detects_unknown_rule_and_bad_distractors():
    item = make_connected_speech("c1", "Check it out.", distractors=("Check it out.",), rule_id="unknown")
    errors = validate_library(make_library(connected_speech=[item]))
    assert len(errors) == 3


def test_detects_answer_index_out_of_range():
    item = make_grammar("g1", ("A", "B"), answer_index=2)
    assert validate_library(make_library(grammar=[item])) == ["g1: answer_index が選択肢の範囲外です"]


def test_detects_unknown_vocabulary_tag():
    item = make_vocabulary("v1", "allocate", "割り当てる", tags=("unknown",))
    assert validate_library(make_library(vocabulary=[item])) == ["v1: 未知のタグ 'unknown'"]


def test_missing_field_is_reported_with_file_and_id(tmp_path):
    content_dir = tmp_path / "content"
    shutil.copytree(CONTENT_DIR, content_dir)
    vocabulary_path = content_dir / "vocabulary.json"
    records = json.loads(vocabulary_path.read_text(encoding="utf-8"))
    del records[0]["meaning_ja"]
    vocabulary_path.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ContentError, match=r"vocabulary\.json.*meaning_ja.*vocab-001"):
        load_library(content_dir)


def test_broken_json_is_reported(tmp_path):
    content_dir = tmp_path / "content"
    shutil.copytree(CONTENT_DIR, content_dir)
    (content_dir / "phrases.json").write_text("[{", encoding="utf-8")
    with pytest.raises(ContentError, match=r"phrases\.json"):
        load_library(content_dir)
