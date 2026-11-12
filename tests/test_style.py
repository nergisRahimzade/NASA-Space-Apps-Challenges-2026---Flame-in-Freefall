"""Day 18 (FE): the mission-control colors keep WCAG contrast, and every experiment has a look.

Contrast follows WCAG 2.x: text needs 4.5:1 (AA), chart marks and lines need 3:1."""

import tomllib
from pathlib import Path

import pandas as pd

from flame_in_freefall.style import (
    CELL_TEXT_COLOR,
    COVERAGE_SCALE,
    EXPERIMENT_COLORS,
    EXPERIMENT_SYMBOLS,
    FUEL_COLORS,
    FUEL_DASHES,
    FUEL_SYMBOLS,
    RISK_COLOR,
)

ROOT = Path(__file__).resolve().parents[1]
THEME = tomllib.loads((ROOT / ".streamlit" / "config.toml").read_text(encoding="utf-8"))["theme"]
PAGE = THEME["backgroundColor"]
PANEL = THEME["secondaryBackgroundColor"]


def _luminance(hex_color: str) -> float:
    def channel(v: int) -> float:
        c = v / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (int(hex_color.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))
    return 0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)


def contrast(a: str, b: str) -> float:
    hi, lo = sorted([_luminance(a), _luminance(b)], reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_contrast_math_matches_known_values():
    assert round(contrast("#FFFFFF", "#000000"), 1) == 21.0
    assert round(contrast("#777777", "#FFFFFF"), 2) == 4.48


def test_text_colors_meet_aa():
    assert contrast(THEME["textColor"], PAGE) >= 7  # AAA for body text
    assert contrast(THEME["linkColor"], PAGE) >= 4.5
    assert contrast(THEME["blueTextColor"], THEME["blueBackgroundColor"]) >= 4.5
    assert contrast(THEME["textColor"], THEME["blueBackgroundColor"]) >= 4.5  # highlights
    assert contrast(THEME["grayTextColor"], THEME["grayBackgroundColor"]) >= 4.5  # badges


def test_heatmap_numbers_meet_aa_on_every_cell_color():
    for cell in COVERAGE_SCALE:
        assert contrast(CELL_TEXT_COLOR, cell) >= 4.5, cell


def test_chart_marks_and_controls_meet_3_to_1_on_page_and_sidebar():
    marks = [THEME["primaryColor"], RISK_COLOR, *EXPERIMENT_COLORS.values(), *FUEL_COLORS.values()]
    for color in marks:
        assert contrast(color, PAGE) >= 3, color
        assert contrast(color, PANEL) >= 3, color


def test_hot_colors_are_only_for_risk():
    hot = {RISK_COLOR, *FUEL_COLORS.values()}
    assert not hot & set(EXPERIMENT_COLORS.values())
    assert THEME["primaryColor"] not in hot


def test_every_experiment_in_the_data_has_a_color_and_marker():
    experiments = set(pd.read_csv(ROOT / "data" / "master.csv")["experiment"])
    assert experiments <= set(EXPERIMENT_COLORS)
    assert set(EXPERIMENT_COLORS) == set(EXPERIMENT_SYMBOLS)
    assert len(set(EXPERIMENT_SYMBOLS.values())) == len(EXPERIMENT_SYMBOLS)  # all different


def test_fuels_differ_by_more_than_color():
    assert FUEL_COLORS.keys() == FUEL_SYMBOLS.keys() == FUEL_DASHES.keys()
    assert len(set(FUEL_SYMBOLS.values())) == len(FUEL_SYMBOLS)
    assert len(set(FUEL_DASHES.values())) == len(FUEL_DASHES)
