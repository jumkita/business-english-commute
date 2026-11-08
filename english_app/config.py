"""Secrets（または環境変数）の読み込みと、学習履歴の保存方式の決定。"""

from __future__ import annotations

import hmac
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum

PASSCODE_KEY = "APP_PASSCODE"
GIST_ID_KEY = "GIST_ID"
GITHUB_TOKEN_KEY = "GITHUB_TOKEN"
PROGRESS_FILE_KEY = "PROGRESS_FILE"


class StorageMode(StrEnum):
    GIST = "gist"
    LOCAL_FILE = "local_file"
    TRIAL = "trial"


STORAGE_MODE_LABELS: dict[StorageMode, str] = {
    StorageMode.GIST: "☁️ 学習履歴は GitHub Gist に保存されます",
    StorageMode.LOCAL_FILE: "💾 学習履歴はローカルファイルに保存されます",
    StorageMode.TRIAL: "🧪 お試しモード（学習履歴は保存されません）",
}


@dataclass(frozen=True)
class AppSettings:
    passcode: str | None = None
    gist_id: str | None = None
    github_token: str | None = None
    progress_file: str | None = None

    @property
    def gist_configured(self) -> bool:
        return bool(self.gist_id and self.github_token)

    @property
    def login_required(self) -> bool:
        return self.gist_configured and bool(self.passcode)

    @property
    def gist_without_passcode(self) -> bool:
        """公開 URL から誰でも Gist に書き込めてしまう設定。保存を無効にして警告する。"""
        return self.gist_configured and not self.passcode


def load_settings(get_value: Callable[[str], str | None]) -> AppSettings:
    return AppSettings(
        passcode=get_value(PASSCODE_KEY),
        gist_id=get_value(GIST_ID_KEY),
        github_token=get_value(GITHUB_TOKEN_KEY),
        progress_file=get_value(PROGRESS_FILE_KEY),
    )


def passcode_matches(settings: AppSettings, candidate: str | None) -> bool:
    if not settings.passcode or not candidate:
        return False
    return hmac.compare_digest(settings.passcode.encode("utf-8"), candidate.encode("utf-8"))


def decide_storage_mode(settings: AppSettings, authenticated: bool) -> StorageMode:
    if settings.gist_configured:
        return StorageMode.GIST if settings.login_required and authenticated else StorageMode.TRIAL
    if settings.progress_file:
        return StorageMode.LOCAL_FILE
    return StorageMode.TRIAL
