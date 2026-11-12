"""Day 16 (AI): claim_check finds numbers and experiment names a takeaway doesn't get from its
passage, without flagging the ones it does."""

import json
from pathlib import Path

import pytest

from flame_in_freefall.claim_check import (
    EXPERIMENTS,
    check_claims,
    unsupported_numbers,
    wrong_experiments,
)

ROOT = Path(__file__).resolve().parents[1]
FLEX2 = {
    "id": "flex2-p1-c3",
    "text": "Pressure ranged from 0.5 atm to 3.0 atm, with 0.1 to 0.4 mole fraction oxygen.",
    "source": "FLEX-2 report",
    "page": 1,
    "experiment": "FLEX-2",
}


# --- numbers --------------------------------------------------------------------------------


def test_numbers_from_the_passage_are_supported():
    assert unsupported_numbers("FLEX-2 used 0.5 to 3.0 atm.", FLEX2["text"]) == []


def test_a_changed_number_is_reported_as_written():
    assert unsupported_numbers("Pressure went up to 4.0 atm.", FLEX2["text"]) == ["4.0"]


def test_3_and_3_point_0_are_the_same_number():
    assert unsupported_numbers("Up to 3 atm.", FLEX2["text"]) == []


def test_leading_dot_decimals_match_equivalent_values():
    assert unsupported_numbers("Pressure was .5 atm.", "Pressure was 0.5 atm.") == []


def test_an_unsupported_leading_dot_decimal_is_reported():
    assert unsupported_numbers("Pressure was .6 atm.", "Pressure was 0.5 atm.") == [".6"]


@pytest.mark.parametrize("sign", ["-", "−"])
def test_a_negative_value_does_not_match_a_positive_value(sign: str):
    assert unsupported_numbers(f"Temperature was {sign}5 C.", "Temperature was 5 C.") == [
        f"{sign}5"
    ]


def test_a_positive_value_does_not_match_a_negative_value():
    assert unsupported_numbers("Temperature was 5 C.", "Temperature was -5 C.") == ["5"]


def test_unicode_minus_matches_an_ascii_negative_value():
    assert unsupported_numbers("Temperature was −.5 C.", "Temperature was -0.5 C.") == []


@pytest.mark.parametrize("separator", ["-", "–", " -", " - ", " − "])
def test_range_separators_do_not_negate_the_upper_endpoint(separator: str):
    assert unsupported_numbers(f"Pressure was .5{separator}3.0 atm.", FLEX2["text"]) == []


@pytest.mark.parametrize("interval", ["-5 to -1", "-5--1", "-5–-1"])
def test_negative_range_endpoints_keep_their_signs(interval: str):
    assert unsupported_numbers(f"Temperature was {interval} C.", "5 C and 1 C.") == ["-5", "-1"]


def test_numbers_glued_to_units_are_checked():
    assert unsupported_numbers("A 29cm sample.", "A 28 cm sample.") == ["29"]


def test_ordinals_are_checked_as_numbers():
    assert unsupported_numbers("The 1st test.", "The 2nd test.") == ["1"]


def test_a_range_with_a_dash_is_read_number_by_number():
    # "0.5–3.0" must not be read as 0.5 and minus 3.0.
    assert unsupported_numbers("Pressure was 0.5–3.0 atm.", FLEX2["text"]) == []
    assert unsupported_numbers("Pressure was 0.5–3.5 atm.", FLEX2["text"]) == ["3.5"]


def test_percent_sign_and_the_word_percent_match():
    assert unsupported_numbers("Oxygen was 21%.", "Oxygen stayed below 21 percent.") == []


def test_thousands_separators_are_one_number():
    assert unsupported_numbers("About 1,000 tests ran.", "The crew ran 1000 tests.") == []
    assert unsupported_numbers("About 1,500 tests ran.", "The crew ran 1000 tests.") == ["1,500"]


def test_digits_inside_formulas_are_not_numbers():
    # CO2, SF6 and O2: the 2 and 6 are part of the name, not measurements.
    assert unsupported_numbers("CO2 and SF6 were tested in O2.", "Suppressants were tested.") == []


def test_digits_inside_experiment_names_are_not_numbers():
    # The passage never says "2", but "FLEX-2" in the takeaway is a name, not a value.
    assert unsupported_numbers("FLEX-2 studied droplets.", "Droplets were studied.") == []


def test_numbers_written_as_words_are_not_checked():
    # Out of scope (claim_check's docstring): "nine" vs "9" isn't compared.
    assert unsupported_numbers("Nine samples burned.", "9 samples burned.") == []


def test_each_missing_number_is_reported_once():
    assert unsupported_numbers("5 cm, then 5 cm again.", "No sizes here.") == ["5"]


# --- experiment names -------------------------------------------------------------------------


def test_the_passages_own_experiment_is_fine():
    assert wrong_experiments("FLEX-2 used 3.0 atm.", FLEX2) == []


def test_another_experiment_is_reported():
    assert wrong_experiments("FLEX used 3.0 atm.", FLEX2) == ["FLEX"]


def test_an_experiment_the_passage_mentions_is_fine():
    passage = {**FLEX2, "text": "Unlike FLEX, this study varied pressure."}
    assert wrong_experiments("FLEX did not vary pressure.", passage) == []


def test_flex_is_not_found_inside_flex_2():
    # The same whole-name rule as retrieval.experiment_in_question.
    assert wrong_experiments("FLEX-2 tested droplets.", {**FLEX2, "experiment": "FLEX-2"}) == []


def test_an_en_dash_in_the_passage_counts_as_a_hyphen():
    # The BASS-II report writes "BASS–II" once. With no tag to fall back on, the name must still
    # be recognised in the passage, or the takeaway's "BASS-II" would be a false alarm.
    untagged = {"id": "bass2-p1-c2", "text": "BASS–II tests the hypothesis.", "experiment": None}
    assert wrong_experiments("BASS-II tests a hypothesis.", untagged) == []


def test_an_en_dash_in_the_takeaway_is_still_checked():
    # Otherwise "BASS–II" in a takeaway would never be read as a name, and slip through.
    assert wrong_experiments("BASS–II used 3.0 atm.", FLEX2) == ["BASS-II"]


def test_a_passage_without_a_tag_only_allows_names_in_its_text():
    untagged = {k: v for k, v in FLEX2.items() if k != "experiment"}
    assert wrong_experiments("FLEX-2 used 3.0 atm.", untagged) == ["FLEX-2"]


def test_the_experiment_list_matches_the_chunks():
    # A 5th experiment in the reports must be added to EXPERIMENTS, or its name would never be
    # checked (and the digits in a name like "FLEX-3" would count as numbers).
    path = ROOT / "data" / "processed" / "chunks.jsonl"
    tags = {
        json.loads(line)["experiment"] for line in path.read_text(encoding="utf-8").splitlines()
    }
    assert tags == set(EXPERIMENTS)


# --- whole summaries --------------------------------------------------------------------------


def _summary(*takeaways: tuple[str, str]) -> dict:
    return {
        "takeaways": [{"text": t, "source": "x", "chunk_id": c} for t, c in takeaways],
        "not_found": not takeaways,
    }


def test_a_summary_that_matches_its_passages_has_no_problems():
    assert check_claims(_summary(("FLEX-2 used 0.5 to 3.0 atm.", "flex2-p1-c3")), [FLEX2]) == []


def test_each_problem_names_the_takeaway_and_its_chunk():
    summary = _summary(("Fine: 0.5 atm.", "flex2-p1-c3"), ("FLEX used 9 atm.", "flex2-p1-c3"))
    assert check_claims(summary, [FLEX2]) == [
        "takeaway 2 (flex2-p1-c3): numbers not in the passage: 9",
        "takeaway 2 (flex2-p1-c3): experiment not in the passage: FLEX",
    ]


def test_a_takeaway_citing_an_unknown_chunk_is_reported_not_skipped():
    assert check_claims(_summary(("Made up.", "nope-p1-c0")), [FLEX2]) == [
        "takeaway 1 cites 'nope-p1-c0', which is not one of the passages"
    ]


def test_not_found_has_nothing_to_check():
    assert check_claims({"takeaways": [], "not_found": True}, [FLEX2]) == []
