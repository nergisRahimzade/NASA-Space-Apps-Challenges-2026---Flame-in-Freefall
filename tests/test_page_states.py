"""Day 16 (FE): messages for no results, failures and slow searches."""

from flame_in_freefall.page_states import (
    ALL_EXPERIMENTS_TIP,
    SLOW_SEARCH_NOTE,
    no_results_tips,
    no_results_title,
    slow_search_note,
)


def test_slow_note_only_for_slow_searches():
    assert slow_search_note(0.1) is None
    assert slow_search_note(2.99) is None
    assert slow_search_note(3.0) == SLOW_SEARCH_NOTE
    assert slow_search_note(4.93) == SLOW_SEARCH_NOTE  # a real first search, measured locally


def test_title_names_the_experiment_when_filtered():
    assert no_results_title(None) == "Nothing in the reports matches this question."
    assert no_results_title("FLEX-2") == "Nothing in the FLEX-2 reports matches this question."


def test_tips_mention_the_sidebar_only_when_filtered():
    assert ALL_EXPERIMENTS_TIP not in no_results_tips(None)
    assert no_results_tips("FLEX").splitlines()[0] == f"- {ALL_EXPERIMENTS_TIP}"


def test_tips_are_a_markdown_list():
    assert all(line.startswith("- ") for line in no_results_tips(None).splitlines())
