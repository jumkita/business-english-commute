import pytest

from english_app.text_match import TokenStatus, Verdict, compare, normalize_tokens, number_to_words


class TestNormalizeTokens:
    def test_ignores_case_and_punctuation(self):
        assert normalize_tokens("Hello,   World!") == ["hello", "world"]

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("I'm", ["i", "am"]),
            ("I\u2019d", ["i", "would"]),
            ("don't", ["do", "not"]),
            ("won't", ["will", "not"]),
            ("cannot", ["can", "not"]),
            ("they're", ["they", "are"]),
            ("it's", ["it", "is"]),
            ("im", ["i", "am"]),
            ("dont", ["do", "not"]),
        ],
    )
    def test_expands_contractions(self, text, expected):
        assert normalize_tokens(text) == expected

    def test_keeps_possessive(self):
        assert normalize_tokens("the client's budget") == ["the", "client's", "budget"]

    @pytest.mark.parametrize(
        ("text", "expected"),
        [
            ("10", ["ten"]),
            ("10%", ["ten", "percent"]),
            ("$5", ["five", "dollars"]),
            ("$1", ["one", "dollar"]),
            ("the 15th", ["the", "fifteenth"]),
            ("21st", ["twenty", "first"]),
            ("2.5", ["two", "point", "five"]),
            ("1,200", ["one", "thousand", "two", "hundred"]),
            ("3pm", ["three", "pm"]),
            ("3 p.m.", ["three", "pm"]),
        ],
    )
    def test_spells_numbers(self, text, expected):
        assert normalize_tokens(text) == expected

    def test_splits_hyphenated_words(self):
        assert normalize_tokens("a follow-up e-mail") == ["a", "follow", "up", "email"]


class TestNumberToWords:
    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (0, ["zero"]),
            (13, ["thirteen"]),
            (40, ["forty"]),
            (105, ["one", "hundred", "five"]),
            (999_999, ["nine", "hundred", "ninety", "nine", "thousand", "nine", "hundred", "ninety", "nine"]),
        ],
    )
    def test_spells_out(self, value, expected):
        assert number_to_words(value) == expected


class TestCompare:
    def test_same_sentence_is_correct(self):
        result = compare("We need to streamline the process.", "we need to streamline the process")
        assert result.verdict is Verdict.CORRECT
        assert result.accuracy == 1.0

    def test_contraction_and_full_form_are_equal(self):
        assert compare("I am not sure.", "I'm not sure").verdict is Verdict.CORRECT

    def test_numbers_and_words_are_equal(self):
        assert compare("Can we get 10% off?", "can we get ten percent off").verdict is Verdict.CORRECT

    def test_one_letter_typo_is_close(self):
        result = compare("We need to streamline the process.", "we need to streamlin the process")
        assert result.verdict is Verdict.CLOSE
        assert TokenStatus.CLOSE in {token.status for token in result.tokens}

    def test_transposed_letters_count_as_one_typo(self):
        assert compare("Check the budget.", "check the budegt").verdict is Verdict.CLOSE

    def test_long_word_allows_two_typos(self):
        assert compare("The implementation", "the implemantasion").verdict is Verdict.CLOSE

    def test_typo_in_short_word_is_wrong(self):
        assert compare("Send the file.", "send tha file").verdict is Verdict.INCORRECT

    def test_missing_inflection_is_wrong_not_typo(self):
        result = compare("She approves the budget.", "she approve the budget")
        assert result.verdict is Verdict.INCORRECT
        wrong = [token for token in result.tokens if token.status is TokenStatus.WRONG]
        assert [(token.expected, token.actual) for token in wrong] == [("approves", "approve")]

    @pytest.mark.parametrize(
        ("expected", "actual"),
        [
            ("something closer to that", "something close to that"),
            ("the fastest option", "the fast option"),
            ("respond quickly please", "respond quick please"),
        ],
    )
    def test_missing_comparative_or_adverb_ending_is_wrong(self, expected, actual):
        assert compare(expected, actual).verdict is Verdict.INCORRECT

    def test_missing_word_is_reported(self):
        result = compare("Could you send me the file?", "could you send the file")
        assert result.verdict is Verdict.INCORRECT
        assert [token.expected for token in result.tokens if token.status is TokenStatus.MISSING] == ["me"]
        assert result.accuracy == pytest.approx(5 / 6)

    def test_extra_word_lowers_accuracy(self):
        result = compare("We can make it.", "we can't make it")
        assert result.verdict is Verdict.INCORRECT
        assert [token.actual for token in result.tokens if token.status is TokenStatus.EXTRA] == ["not"]
        assert result.accuracy == pytest.approx(4 / 5)

    def test_space_difference_is_close(self):
        result = compare("Could you set up a meeting?", "could you setup a meeting")
        assert result.verdict is Verdict.CLOSE

    def test_empty_answer_is_all_missing(self):
        result = compare("Let's touch base.", "")
        assert result.verdict is Verdict.INCORRECT
        assert result.accuracy == 0.0
        assert {token.status for token in result.tokens} == {TokenStatus.MISSING}
