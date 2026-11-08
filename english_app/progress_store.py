"""学習履歴の保存先（非公開の GitHub Gist・ローカルファイル・メモリ）。

HTTP 通信は標準ライブラリの urllib で行い、依存を増やさない。
"""

from __future__ import annotations

import copy
import json
import re
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any, Protocol

GITHUB_API_URL = "https://api.github.com"
GITHUB_API_VERSION = "2022-11-28"
REQUEST_TIMEOUT_SECONDS = 10
DEFAULT_GIST_FILENAME = "progress.json"
USER_AGENT = "business-english-commute"
GIST_ID_PATTERN = re.compile(r"[0-9a-f]+")


class ProgressStoreError(RuntimeError):
    """学習履歴の読み書きに失敗したときに送出する。メッセージにトークンは含めない。"""


class ProgressStore(Protocol):
    def load(self) -> dict[str, Any]: ...

    def save(self, data: Mapping[str, Any]) -> None: ...


class MemoryProgressStore:
    """保存なしのお試しモード用。ブラウザを閉じると消える。"""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}

    def load(self) -> dict[str, Any]:
        return copy.deepcopy(self._data)

    def save(self, data: Mapping[str, Any]) -> None:
        self._data = copy.deepcopy(dict(data))


class FileProgressStore:
    """ローカル開発用。Streamlit Cloud ではファイルが再起動で消えるため使わない。"""

    def __init__(self, path: Path) -> None:
        self._path = path

    def load(self) -> dict[str, Any]:
        if not self._path.exists():
            return {}
        try:
            data = json.loads(self._path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ProgressStoreError(f"学習履歴ファイルを読めませんでした: {self._path.name}") from error
        if not isinstance(data, dict):
            raise ProgressStoreError(f"学習履歴ファイルの形式が不正です: {self._path.name}")
        return data

    def save(self, data: Mapping[str, Any]) -> None:
        temporary_path = self._path.with_suffix(self._path.suffix + ".tmp")
        try:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            temporary_path.write_text(_serialize(data), encoding="utf-8")
            temporary_path.replace(self._path)
        except OSError as error:
            raise ProgressStoreError(f"学習履歴ファイルに保存できませんでした: {self._path.name}") from error


UrlOpener = Callable[..., Any]


class GistProgressStore:
    def __init__(
        self,
        gist_id: str,
        token: str,
        filename: str = DEFAULT_GIST_FILENAME,
        urlopen: UrlOpener = urllib.request.urlopen,
    ) -> None:
        if not GIST_ID_PATTERN.fullmatch(gist_id):
            raise ValueError("GIST_ID は Gist の URL 末尾にある英数字（16進数）を指定してください")
        self._gist_url = f"{GITHUB_API_URL}/gists/{gist_id}"
        self._token = token
        self._filename = filename
        self._urlopen = urlopen

    def load(self) -> dict[str, Any]:
        gist = _parse_json_object(self._request("GET", self._gist_url), "GitHub API の応答")
        file_info = gist.get("files", {}).get(self._filename)
        if file_info is None:
            return {}
        content = file_info.get("content") or ""
        if file_info.get("truncated"):
            content = self._request("GET", file_info["raw_url"])
        if not content.strip():
            return {}
        return _parse_json_object(content, f"Gist の {self._filename}")

    def save(self, data: Mapping[str, Any]) -> None:
        body = {"files": {self._filename: {"content": _serialize(data)}}}
        self._request("PATCH", self._gist_url, body)

    def _request(self, method: str, url: str, body: Mapping[str, Any] | None = None) -> str:
        headers = {
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {self._token}",
            "X-GitHub-Api-Version": GITHUB_API_VERSION,
            "User-Agent": USER_AGENT,
        }
        data = None
        if body is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(body).encode("utf-8")
        request = urllib.request.Request(url, data=data, method=method, headers=headers)
        try:
            with self._urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                return response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            raise ProgressStoreError(f"GitHub API がエラーを返しました（HTTP {error.code}）") from error
        except (urllib.error.URLError, TimeoutError) as error:
            raise ProgressStoreError("GitHub API に接続できませんでした") from error


def _serialize(data: Mapping[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False, indent=1, sort_keys=True)


def _parse_json_object(text: str, source: str) -> dict[str, Any]:
    try:
        data = json.loads(text)
    except json.JSONDecodeError as error:
        raise ProgressStoreError(f"{source}を JSON として読めませんでした") from error
    if not isinstance(data, dict):
        raise ProgressStoreError(f"{source}の形式が不正です")
    return data
