from datetime import date

from english_app.stats import AreaSummary, DailyMinutes
from english_app.text_match import compare
from english_app.ui.charts import area_table_markdown, daily_minutes_bars_html
from english_app.ui.components import to_js_literal
from english_app.ui.diff_view import render_diff_html
from english_app.ui.formatting import escape_markdown, format_percent, format_remaining


def test_escape_markdown():
    assert escape_markdown("a*b_c [d]") == "a\\*b\\_c \\[d\\]"
    assert escape_markdown("Let's meet.") == "Let's meet."


def test_format_remaining():
    assert format_remaining(125) == "2:05"
    assert format_remaining(-3) == "0:00"


def test_format_percent():
    assert format_percent(0.756) == "76%"
    assert format_percent(None) == "—"


def test_js_literal_cannot_close_script_tag():
    assert "</script>" not in to_js_literal("</script><script>alert(1)</script>")


def test_diff_html_shows_wrong_and_expected_words():
    html = render_diff_html(compare("I'll circle back to you.", "I'll circle back to them"))
    assert "them" in html
    assert "you" in html
    assert "<s " in html


def test_area_table_markdown():
    table = area_table_markdown([AreaSummary("クイズ：単語", total=10, studied=4, mastered=1, accuracy=0.5)])
    assert table.splitlines()[2] == "| クイズ：単語 | 4 / 10 | 1 | 50% |"


def test_daily_bars_have_one_column_per_day():
    daily = [DailyMinutes(date(2026, 11, day), minutes=float(day)) for day in range(1, 15)]
    html = daily_minutes_bars_html(daily)
    assert html.count("border-radius:3px") == len(daily)
