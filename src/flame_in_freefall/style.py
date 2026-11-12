"""Day 18 (FE): the mission-control look, in one place.

The rule: controls and page chrome stay neutral (steel grey), and hot colors (orange, amber)
are kept for risk data only, so a hot color always means "fire risk". Every color here was
checked for contrast on the page background #14161A (FIF-D18-FE PR has the numbers)."""

# --- Experiments: one color and one marker shape each, everywhere in the app ---------------
# Cool, color-blind-friendly hues (based on Okabe-Ito), so they never look like risk. The
# marker shape repeats the meaning, so color isn't the only cue. All at least 5:1 on the page.
EXPERIMENT_COLORS = {
    "FLEX": "#56B4E9",  # sky blue
    "FLEX-2": "#5FC9A8",  # teal
    "Saffire-II": "#CC79A7",  # mauve
    "BASS-II": "#B8C4D6",  # steel
}
EXPERIMENT_SYMBOLS = {
    "FLEX": "circle",
    "FLEX-2": "square",
    "Saffire-II": "diamond",
    "BASS-II": "triangle-up",
}

# --- Risk: the only place hot colors appear ------------------------------------------------
RISK_COLOR = "#F77F00"  # flame orange: ranking bars
# FLEX fuels: orange vs light amber differ in brightness, not just hue, and each line also has
# its own marker and dash, so they stay apart for color-blind readers.
FUEL_COLORS = {"Heptane": "#F77F00", "Methanol": "#FCBF49"}
FUEL_SYMBOLS = {"Heptane": "circle", "Methanol": "diamond"}
FUEL_DASHES = {"Heptane": "solid", "Methanol": "dash"}

# --- Coverage: how many tests, in neutral blue so it doesn't read as danger ---------------
# Stops end at #2A6BA6 so the white cell numbers keep at least 5:1 contrast (AA) everywhere.
COVERAGE_SCALE = ["#1F2329", "#1D4266", "#2A6BA6"]
CELL_TEXT_COLOR = "#F5F3EF"
