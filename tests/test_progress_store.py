import json
import urllib.error

import pytest

from english_app.progress_store import (
    DEFAULT_GIST_FILENAME,
    FileProgressStore,
    GistProgressStore,
    MemoryProgressStore,
    ProgressStoreError,
)

GIST_ID = "0123abcd"
TOKEN = "test-token-value"


class FakeResponse:
    def __init__(self, body: str) -> None:
        self._body = body.encode("utf-8")

    def read(self) -> bytes:
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False


class FakeUrlOpen:
    """urllib.request.urlopen の代わりに、決めた応答を順に返す。"""

    def __init__(self, *responses) -> None:
        self._responses = list(responses)
        self.requests = []

    def __call__(self, request, timeout):
        self.requests.append(request)
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return FakeResponse(response)


def _gist_body(content: str | None, truncated: bool = False) -> str:
    files = {}
    if content is not None:
        files[DEFAULT_GIST_FILENAME] = {"content": content, "truncated": truncated, "raw_url": "https://raw.example/p"}
    return json.dumps({"files": files})


def _store(opener: FakeUrlOpen) -> GistProgressStore:
    return GistProgressStore(GIST_ID, TOKEN, urlopen=opener)


class TestGistProgressStore:
    def test_load_reads_progress_file(self):
        opener = FakeUrlOpen(_gist_body(json.dumps({"version": 1})))
        assert _store(opener).load() == {"version": 1}
        request = opener.requests[0]
        assert request.get_method() == "GET"
        assert request.full_url.endswith(f"/gists/{GIST_ID}")
        assert request.get_header("Authorization") == f"Bearer {TOKEN}"

    @pytest.mark.parametrize("content", [None, "", "  \n"])
    def test_missing_or_empty_file_is_empty_progress(self, content):
        assert _store(FakeUrlOpen(_gist_body(content))).load() == {}

    def test_truncated_file_is_fetched_from_raw_url(self):
        opener = FakeUrlOpen(_gist_body("{", truncated=True), json.dumps({"cards": {}}))
        assert _store(opener).load() == {"cards": {}}
        assert opener.requests[1].full_url == "https://raw.example/p"

    def test_save_patches_progress_file(self):
        opener = FakeUrlOpen("{}")
        _store(opener).save({"version": 1, "cards": {}})
        request = opener.requests[0]
        assert request.get_method() == "PATCH"
        body = json.loads(request.data.decode("utf-8"))
        assert json.loads(body["files"][DEFAULT_GIST_FILENAME]["content"]) == {"version": 1, "cards": {}}

    def test_http_error_hides_token(self):
        error = urllib.error.HTTPError("https://api.github.com", 401, "Unauthorized", hdrs=None, fp=None)
        with pytest.raises(ProgressStoreError, match="401") as raised:
            _store(FakeUrlOpen(error)).load()
        assert TOKEN not in str(raised.value)

    def test_network_error(self):
        with pytest.raises(ProgressStoreError):
            _store(FakeUrlOpen(urllib.error.URLError("offline"))).save({})

    def test_broken_json_is_error(self):
        with pytest.raises(ProgressStoreError):
            _store(FakeUrlOpen(_gist_body("{broken"))).load()

    @pytest.mark.parametrize("gist_id", ["", "../users", "abc/def", "XYZ"])
    def test_rejects_invalid_gist_id(self, gist_id):
        with pytest.raises(ValueError):
            GistProgressStore(gist_id, TOKEN, urlopen=FakeUrlOpen())


class TestFileProgressStore:
    def test_round_trip(self, tmp_path):
        store = FileProgressStore(tmp_path / "progress.json")
        assert store.load() == {}
        store.save({"version": 1, "flagged_item_ids": ["ph-001"]})
        assert store.load() == {"version": 1, "flagged_item_ids": ["ph-001"]}

    def test_broken_file_is_error(self, tmp_path):
        path = tmp_path / "progress.json"
        path.write_text("[1, 2", encoding="utf-8")
        with pytest.raises(ProgressStoreError):
            FileProgressStore(path).load()


def test_memory_store_returns_copies():
    store = MemoryProgressStore()
    store.save({"cards": {"a": 1}})
    loaded = store.load()
    loaded["cards"]["a"] = 2
    assert store.load() == {"cards": {"a": 1}}
