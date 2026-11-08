import pytest

from english_app.config import AppSettings, StorageMode, decide_storage_mode, load_settings, passcode_matches

FULL = AppSettings(passcode="secret", gist_id="abc123", github_token="token")


def test_load_settings_reads_each_key():
    values = {"APP_PASSCODE": "secret", "GIST_ID": "abc123", "GITHUB_TOKEN": "token", "PROGRESS_FILE": "p.json"}
    settings = load_settings(values.get)
    assert settings == AppSettings(passcode="secret", gist_id="abc123", github_token="token", progress_file="p.json")


@pytest.mark.parametrize(
    ("settings", "authenticated", "expected"),
    [
        (FULL, True, StorageMode.GIST),
        (FULL, False, StorageMode.TRIAL),
        (AppSettings(gist_id="abc123", github_token="token"), True, StorageMode.TRIAL),
        (AppSettings(passcode="secret", gist_id="abc123"), True, StorageMode.TRIAL),
        (AppSettings(progress_file="p.json"), False, StorageMode.LOCAL_FILE),
        (AppSettings(), False, StorageMode.TRIAL),
    ],
)
def test_decide_storage_mode(settings, authenticated, expected):
    assert decide_storage_mode(settings, authenticated) is expected


def test_gist_without_passcode_is_flagged():
    settings = AppSettings(gist_id="abc123", github_token="token")
    assert settings.gist_without_passcode
    assert not settings.login_required
    assert not FULL.gist_without_passcode
    assert FULL.login_required


@pytest.mark.parametrize(
    ("settings", "candidate", "expected"),
    [
        (FULL, "secret", True),
        (FULL, "wrong", False),
        (FULL, "", False),
        (FULL, None, False),
        (AppSettings(), "", False),
        (AppSettings(), "anything", False),
    ],
)
def test_passcode_matches(settings, candidate, expected):
    assert passcode_matches(settings, candidate) is expected
