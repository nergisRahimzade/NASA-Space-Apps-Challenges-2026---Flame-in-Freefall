"""FIF-D13-DAT: riskiness ranking table (data/ranking.csv), see data_notes.md section 9."""

import pandas as pd
import pytest

from flame_in_freefall.build_master import build_master
from flame_in_freefall.build_ranking import (
    GROUP_KEYS,
    RANKING,
    RANKING_COLUMNS,
    build_ranking,
    burn_spread_mm_s,
    oxygen_level,
)
from flame_in_freefall.clean_tables import clean_flex, clean_flex2, clean_saffire2


@pytest.fixture(scope="module")
def saffire2() -> pd.DataFrame:
    return clean_saffire2()


@pytest.fixture(scope="module")
def ranking(saffire2) -> pd.DataFrame:
    # Built from the raw files, so the test does not depend on data/ being up to date.
    master = build_master([clean_flex2(), saffire2, clean_flex()])
    return build_ranking(master, saffire2)


def by_material(ranking: pd.DataFrame, experiment: str) -> pd.DataFrame:
    return ranking[ranking["experiment"] == experiment].set_index(["material", "oxygen_pct"])


def test_columns_and_one_row_per_group(ranking):
    assert list(ranking.columns) == RANKING_COLUMNS
    assert not ranking.duplicated(GROUP_KEYS).any()


def test_flex2_dropped_because_it_has_no_results(ranking):
    assert set(ranking["experiment"]) == {"Saffire-II", "FLEX"}


def test_every_saffire_sample_and_finished_flex_test_is_counted(ranking):
    tests = ranking.groupby("experiment")["tests"].sum().to_dict()
    assert tests["Saffire-II"] == 9
    # 273 FLEX tests, minus 10 in the three groups where every test was cut short
    # (Heptane 25% (2) and 34% (4), Methanol 25% (4)): those groups have nothing to rank on.
    assert tests["FLEX"] == 273 - 10
    flex = ranking[ranking["experiment"] == "FLEX"]
    assert ((flex["completion"] + flex["extinction"]) > 0).all()


def test_oxygen_level_is_the_rounded_middle_half_up():
    rows = pd.DataFrame(
        {"oxygen_pct_min": [21.5, 21.9, 20.5, 17.0], "oxygen_pct_max": [21.5, 22.0, 20.5, 30.0]}
    )
    assert oxygen_level(rows).tolist() == [22.0, 22.0, 21.0, 24.0]


def test_burn_spread_matches_the_measured_spread_rate(saffire2):
    """The SIBAL samples have both, so they show burn length / burn time is a fair stand-in."""
    sibal = saffire2[saffire2["spread_rate_mm_s"].notna()]
    estimate = burn_spread_mm_s(sibal)
    assert len(sibal) == 2
    assert (estimate - sibal["spread_rate_mm_s"]).abs().max() < 0.15


def test_no_burn_length_means_no_spread(saffire2):
    silicone = saffire2[saffire2["material"] == "Silicone"]
    assert silicone["burn_time_s"].isna().all()  # 'Insignificant' in the raw file
    assert (burn_spread_mm_s(silicone) == 0).all()


def test_saffire_ranked_by_burn_spread(ranking):
    saffire = by_material(ranking, "Saffire-II")
    order = saffire.sort_values("risk_rank").index.get_level_values("material").tolist()
    assert order == ["Cotton-Fiberglass (SIBAL)", "PMMA & Nomex", "PMMA", "Silicone"]
    sibal = saffire.loc[("Cotton-Fiberglass (SIBAL)", 22.0)]
    assert sibal["spread_rate_n"] == 2
    assert sibal["spread_rate_mm_s_min"] == 2.1
    assert sibal["spread_rate_mm_s_max"] == 2.6
    assert sibal["spread_rate_mm_s_mean"] == pytest.approx(2.35)
    # No outcome column in Saffire-II, so the counts are empty, not 0.
    assert saffire[["completion", "extinction", "disruption"]].isna().all().all()


def test_flex_kept_burning_share_leaves_out_disruptions(ranking):
    flex = by_material(ranking, "FLEX")
    methanol_30 = flex.loc[("Methanol", 30.0)]  # 2 completion, 2 extinction, 4 disruption
    assert methanol_30["kept_burning_share"] == 0.5
    assert flex["kept_burning_share"].between(0, 1).all()
    assert flex["spread_rate_n"].eq(0).all()  # droplets have no spread rate


def test_ranks_within_each_experiment_ties_share_a_rank(ranking):
    for experiment, group in ranking.groupby("experiment"):
        assert group["risk_rank"].min() == 1, experiment
        # Higher risk_value never gets a worse (bigger) rank.
        ordered = group.sort_values("risk_rank")
        assert ordered["risk_value"].is_monotonic_decreasing, experiment
    flex = ranking[ranking["experiment"] == "FLEX"]
    tied_first = flex[flex["risk_value"] == 1.0]
    assert (tied_first["risk_rank"] == 1).all() and len(tied_first) == 2


def test_risk_value_is_the_column_named_in_risk_basis(ranking):
    for _, row in ranking.iterrows():
        assert row["risk_value"] == pytest.approx(round(row[row["risk_basis"]], 3))


def test_saved_ranking_loads_and_matches_a_fresh_build(ranking):
    saved = pd.read_csv(RANKING)
    pd.testing.assert_frame_equal(saved, ranking, check_dtype=False)
