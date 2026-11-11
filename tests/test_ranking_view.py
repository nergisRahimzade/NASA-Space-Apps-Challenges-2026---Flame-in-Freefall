"""Day 13 (FE): reading and filtering data/ranking.csv for the riskiness charts."""

import pandas as pd

from flame_in_freefall.ranking_view import axis_label, filter_ranking, load_ranking


def test_load_ranking_reads_the_real_file():
    ranking = load_ranking()
    assert set(ranking["experiment"]) == {"Saffire-II", "FLEX"}
    assert set(ranking["risk_basis"]) == {"burn_spread_mm_s_mean", "kept_burning_share"}


def test_missing_file_gives_an_empty_table(tmp_path):
    assert load_ranking(tmp_path / "missing.csv").empty


def test_filters_narrow_by_experiment_material_and_oxygen():
    ranking = load_ranking()
    saffire = filter_ranking(ranking, experiment="Saffire-II")
    assert set(saffire["experiment"]) == {"Saffire-II"} and len(saffire) == 4

    heptane = filter_ranking(ranking, material="Heptane", oxygen_min=20, oxygen_max=24)
    assert set(heptane["material"]) == {"Heptane"}
    assert heptane["oxygen_pct"].between(20, 24).all() and len(heptane) > 0


def test_no_filters_keeps_everything():
    ranking = load_ranking()
    assert len(filter_ranking(ranking)) == len(ranking)


def test_unknown_experiment_matches_nothing():
    assert filter_ranking(load_ranking(), experiment="FLEX-2").empty


def test_filtering_an_empty_table_stays_empty():
    assert filter_ranking(pd.DataFrame(), experiment="FLEX").empty


def test_axis_labels_are_plain_words():
    ranking = load_ranking()
    saffire = ranking[ranking["experiment"] == "Saffire-II"]
    flex = ranking[ranking["experiment"] == "FLEX"]
    assert axis_label(saffire) == "Average flame spread (mm/s)"
    assert axis_label(flex) == "Share of tests where the flame kept burning"


def test_saffire_order_matches_data_notes():
    # data_notes.md section 9: SIBAL > PMMA & Nomex > PMMA > Silicone
    saffire = filter_ranking(load_ranking(), experiment="Saffire-II").sort_values("risk_rank")
    assert list(saffire["material"]) == [
        "Cotton-Fiberglass (SIBAL)",
        "PMMA & Nomex",
        "PMMA",
        "Silicone",
    ]
