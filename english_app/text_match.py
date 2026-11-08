"""正解文と入力文（タイプまたは音声認識の結果）の照合（FR-10・FR-03）。

大文字小文字・句読点・縮約形・数字の書き方の違いは誤りにせず、
iPhone の自動修正で起きやすい 1〜2 文字のつづり違いは「惜しい」と判定する。
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from dataclasses import dataclass
from enum import StrEnum
from typing import assert_never

MIN_LENGTH_FOR_TYPO = 4
LONG_WORD_LENGTH = 8
MAX_TYPO_DISTANCE = 1
MAX_TYPO_DISTANCE_LONG_WORD = 2
LARGEST_NUMBER_TO_SPELL = 999_999
ONE_THOUSAND = 1000
ONE_HUNDRED = 100
TEENS_LIMIT = 20
# 語尾の変化（三単現の s・過去形の ed・比較級の er・副詞の ly など）は聞き取りの誤りとして扱い、つづりミス扱いにしない
INFLECTION_SUFFIXES = frozenset({"s", "es", "d", "ed", "ing", "r", "er", "st", "est", "ly"})


class TokenStatus(StrEnum):
    CORRECT = "correct"
    CLOSE = "close"
    WRONG = "wrong"
    MISSING = "missing"
    EXTRA = "extra"


class Verdict(StrEnum):
    CORRECT = "correct"
    CLOSE = "close"
    INCORRECT = "incorrect"


@dataclass(frozen=True)
class TokenDiff:
    status: TokenStatus
    expected: str | None = None
    actual: str | None = None


@dataclass(frozen=True)
class MatchResult:
    verdict: Verdict
    tokens: tuple[TokenDiff, ...]
    accuracy: float


_PUNCTUATION_TRANSLATION = str.maketrans(
    {
        "\u2018": "'",
        "\u2019": "'",
        "\u201c": '"',
        "\u201d": '"',
        "\u2013": " ",
        "\u2014": " ",
    }
)

_ONES = (
    "zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten",
    "eleven", "twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen",
)
_TENS = ("", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety")
_IRREGULAR_ORDINALS = {
    "one": "first",
    "two": "second",
    "three": "third",
    "five": "fifth",
    "eight": "eighth",
    "nine": "ninth",
    "twelve": "twelfth",
}

_IRREGULAR_CONTRACTIONS: dict[str, tuple[str, ...]] = {
    "won't": ("will", "not"),
    "can't": ("can", "not"),
    "shan't": ("shall", "not"),
    "cannot": ("can", "not"),
    "ok": ("okay",),
}
_NOT_CONTRACTION_BASES = (
    "do", "does", "did", "is", "are", "was", "were", "have", "has", "had",
    "would", "could", "should", "must", "need",
)
# アポストロフィなしでタイプされた縮約形。were / well / its など普通の単語と重なるものは含めない
_APOSTROPHE_FREE_CONTRACTIONS: dict[str, tuple[str, ...]] = {
    **{f"{base}nt": (base, "not") for base in _NOT_CONTRACTION_BASES},
    "cant": ("can", "not"),
    "wont": ("will", "not"),
    "im": ("i", "am"),
    "ive": ("i", "have"),
    "youre": ("you", "are"),
    "youve": ("you", "have"),
    "youll": ("you", "will"),
    "theyre": ("they", "are"),
    "theyve": ("they", "have"),
    "theyll": ("they", "will"),
    "weve": ("we", "have"),
    "thats": ("that", "is"),
    "whats": ("what", "is"),
    "theres": ("there", "is"),
    "heres": ("here", "is"),
}
_SUFFIX_CONTRACTIONS = (("'re", "are"), ("'ve", "have"), ("'ll", "will"), ("'m", "am"), ("'d", "would"))
# 's を is と読む語。それ以外の 's（client's など）は所有格として残す
_IS_CONTRACTION_BASES = frozenset(
    {"it", "that", "what", "there", "here", "he", "she", "who", "where", "how", "when", "why"}
)

_TOKEN_PATTERN = re.compile(r"\d+(?:\.\d+)?(?:st|nd|rd|th)?|[a-z]+(?:'[a-z]+)*")
_NUMBER_PATTERN = re.compile(r"(\d+)(?:\.(\d+))?(st|nd|rd|th)?")


def normalize_tokens(text: str) -> list[str]:
    """照合用に、英文を正規化した単語の並びに変換する。"""
    normalized = unicodedata.normalize("NFKC", text).translate(_PUNCTUATION_TRANSLATION).lower()
    normalized = re.sub(r"\b([ap])\.m\.", r"\1m", normalized)
    normalized = re.sub(r"(\d)(am|pm)\b", r"\1 \2", normalized)
    normalized = re.sub(r"(?<=\d),(?=\d{3})", "", normalized)
    normalized = re.sub(r"\$(\d+(?:\.\d+)?)", _spell_dollars, normalized)
    normalized = normalized.replace("%", " percent")
    normalized = normalized.replace("e-mail", "email")
    normalized = re.sub(r"(?<=\w)-(?=\w)", " ", normalized)
    tokens: list[str] = []
    for raw_token in _TOKEN_PATTERN.findall(normalized):
        tokens.extend(_expand_token(raw_token))
    return tokens


def compare(expected: str, actual: str) -> MatchResult:
    expected_tokens = normalize_tokens(expected)
    actual_tokens = normalize_tokens(actual)
    matcher = difflib.SequenceMatcher(a=expected_tokens, b=actual_tokens, autojunk=False)
    diffs: list[TokenDiff] = []
    for tag, expected_start, expected_end, actual_start, actual_end in matcher.get_opcodes():
        expected_block = expected_tokens[expected_start:expected_end]
        actual_block = actual_tokens[actual_start:actual_end]
        match tag:
            case "equal":
                diffs.extend(TokenDiff(TokenStatus.CORRECT, token, token) for token in expected_block)
            case "delete":
                diffs.extend(TokenDiff(TokenStatus.MISSING, expected=token) for token in expected_block)
            case "insert":
                diffs.extend(TokenDiff(TokenStatus.EXTRA, actual=token) for token in actual_block)
            case "replace":
                diffs.extend(_compare_replaced_block(expected_block, actual_block))
            case _:
                raise ValueError(f"想定外の差分種別です: {tag}")
    return MatchResult(
        verdict=_verdict(diffs),
        tokens=tuple(diffs),
        accuracy=_accuracy(diffs),
    )


def _compare_replaced_block(expected_block: list[str], actual_block: list[str]) -> list[TokenDiff]:
    joined_actual = "".join(actual_block)
    if "".join(expected_block) == joined_actual:
        # set up / setup のような空白の有無だけの違い
        return [TokenDiff(TokenStatus.CLOSE, token, joined_actual) for token in expected_block]
    diffs = []
    for index in range(max(len(expected_block), len(actual_block))):
        expected = expected_block[index] if index < len(expected_block) else None
        actual = actual_block[index] if index < len(actual_block) else None
        if expected is None:
            diffs.append(TokenDiff(TokenStatus.EXTRA, actual=actual))
        elif actual is None:
            diffs.append(TokenDiff(TokenStatus.MISSING, expected=expected))
        elif _is_typo(expected, actual):
            diffs.append(TokenDiff(TokenStatus.CLOSE, expected, actual))
        else:
            diffs.append(TokenDiff(TokenStatus.WRONG, expected, actual))
    return diffs


def _verdict(diffs: list[TokenDiff]) -> Verdict:
    statuses = {diff.status for diff in diffs}
    if statuses <= {TokenStatus.CORRECT}:
        return Verdict.CORRECT
    if statuses <= {TokenStatus.CORRECT, TokenStatus.CLOSE}:
        return Verdict.CLOSE
    return Verdict.INCORRECT


def _accuracy(diffs: list[TokenDiff]) -> float:
    """正解文の語数に余分な語の数を足した数を分母にする（余分な語があるのに 100% と出さないため）。"""
    matched = 0
    counted = 0
    for diff in diffs:
        match diff.status:
            case TokenStatus.CORRECT | TokenStatus.CLOSE:
                matched += 1
                counted += 1
            case TokenStatus.WRONG | TokenStatus.MISSING | TokenStatus.EXTRA:
                counted += 1
            case _:
                assert_never(diff.status)
    return matched / counted if counted else 0.0


def _is_typo(expected: str, actual: str) -> bool:
    if len(expected) < MIN_LENGTH_FOR_TYPO or _is_inflection(expected, actual):
        return False
    limit = MAX_TYPO_DISTANCE_LONG_WORD if len(expected) >= LONG_WORD_LENGTH else MAX_TYPO_DISTANCE
    return _edit_distance(expected, actual) <= limit


def _is_inflection(first: str, second: str) -> bool:
    shorter, longer = sorted((first, second), key=len)
    return longer.startswith(shorter) and longer[len(shorter):] in INFLECTION_SUFFIXES


def _edit_distance(first: str, second: str) -> int:
    """隣り合う文字の入れ替えも 1 回と数える編集距離（OSA 距離）。"""
    previous_row: list[int] | None = None
    row = list(range(len(second) + 1))
    for i, first_char in enumerate(first, start=1):
        before_previous, previous_row = previous_row, row
        row = [i] + [0] * len(second)
        for j, second_char in enumerate(second, start=1):
            cost = 0 if first_char == second_char else 1
            row[j] = min(previous_row[j] + 1, row[j - 1] + 1, previous_row[j - 1] + cost)
            if (
                before_previous is not None
                and i > 1
                and j > 1
                and first_char == second[j - 2]
                and first[i - 2] == second_char
            ):
                row[j] = min(row[j], before_previous[j - 2] + 1)
    return row[-1]


def _expand_token(raw_token: str) -> list[str]:
    if raw_token[0].isdigit():
        return _number_tokens(raw_token)
    if raw_token in _IRREGULAR_CONTRACTIONS:
        return list(_IRREGULAR_CONTRACTIONS[raw_token])
    if raw_token in _APOSTROPHE_FREE_CONTRACTIONS:
        return list(_APOSTROPHE_FREE_CONTRACTIONS[raw_token])
    if raw_token.endswith("n't"):
        return [raw_token[: -len("n't")], "not"]
    for suffix, expansion in _SUFFIX_CONTRACTIONS:
        if raw_token.endswith(suffix):
            return [raw_token[: -len(suffix)], expansion]
    if raw_token.endswith("'s") and raw_token[: -len("'s")] in _IS_CONTRACTION_BASES:
        return [raw_token[: -len("'s")], "is"]
    return [raw_token]


def _number_tokens(raw_token: str) -> list[str]:
    match_result = _NUMBER_PATTERN.fullmatch(raw_token)
    if match_result is None:
        return [raw_token]
    integer_part, decimal_part, ordinal_suffix = match_result.groups()
    value = int(integer_part)
    if value > LARGEST_NUMBER_TO_SPELL:
        return [raw_token]
    words = number_to_words(value)
    if decimal_part:
        words += ["point", *(_ONES[int(digit)] for digit in decimal_part)]
    elif ordinal_suffix:
        words[-1] = _ordinal(words[-1])
    return words


def number_to_words(value: int) -> list[str]:
    if value == 0:
        return [_ONES[0]]
    thousands, rest = divmod(value, ONE_THOUSAND)
    words: list[str] = []
    if thousands:
        words += [*_under_one_thousand(thousands), "thousand"]
    if rest:
        words += _under_one_thousand(rest)
    return words


def _under_one_thousand(value: int) -> list[str]:
    hundreds, rest = divmod(value, ONE_HUNDRED)
    words: list[str] = []
    if hundreds:
        words += [_ONES[hundreds], "hundred"]
    if rest:
        if rest < TEENS_LIMIT:
            words.append(_ONES[rest])
        else:
            tens, ones = divmod(rest, 10)
            words.append(_TENS[tens])
            if ones:
                words.append(_ONES[ones])
    return words


def _ordinal(word: str) -> str:
    if word in _IRREGULAR_ORDINALS:
        return _IRREGULAR_ORDINALS[word]
    if word.endswith("y"):
        return f"{word[:-1]}ieth"
    return f"{word}th"


def _spell_dollars(match_result: re.Match[str]) -> str:
    amount = match_result.group(1)
    unit = "dollar" if amount == "1" else "dollars"
    return f"{amount} {unit}"
