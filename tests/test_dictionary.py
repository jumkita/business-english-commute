import pytest

from english_app.content import Domain, load_library
from english_app.dictionary import build_entries, search_entries


@pytest.fixture(scope="module")
def entries():
    return build_entries(load_library())


def test_has_entry_for_every_item(entries):
    assert len(entries) == len(load_library().items_by_id)
    assert all(entry.audio_text for entry in entries)


def test_search_by_english_is_case_insensitive(entries):
    results = search_entries(entries, "LEVERAGE")
    assert any(entry.title == "leverage" for entry in results)


def test_search_by_japanese(entries):
    results = search_entries(entries, "日程")
    assert results
    assert all("日程" in entry.search_text for entry in results)


def test_filter_by_domain(entries):
    results = search_entries(entries, domain=Domain.GRAMMAR)
    assert results
    assert {entry.domain for entry in results} == {Domain.GRAMMAR}


def test_flagged_only(entries):
    flagged = {entries[0].item_id}
    results = search_entries(entries, flagged_only=True, flagged_item_ids=flagged)
    assert [entry.item_id for entry in results] == [entries[0].item_id]
