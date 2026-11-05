"""Day 7 (BE): health check for the app before it deploys.

Every merge to main redeploys the live app (be_notes.md §3), and the live URL can't be checked
from CI (it redirects automated requests to a sign-in page). So we check the app here instead:
run the real app/streamlit_app.py with Streamlit's test tool (no browser or server needed) and
fail if the page crashes or shows an error box. Also check that the live app's package list
(app/requirements.txt) still covers our pyproject.toml dependencies."""

import re
import tomllib
from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "app" / "streamlit_app.py"


@pytest.fixture
def app() -> AppTest:
    # The first run imports pandas and plotly, which can take a few seconds.
    return AppTest.from_file(str(APP), default_timeout=30).run()


def _assert_healthy(at: AppTest) -> None:
    # at.exception = the script crashed; at.error = it showed a red st.error box.
    assert not at.exception, [e.value for e in at.exception]
    assert not at.error, [e.value for e in at.error]


def test_start_page_loads(app):
    _assert_healthy(app)
    assert app.title[0].value == "Flame in Freefall"


def test_search_shows_results(app):
    app.text_input[0].input("Which materials burn fastest in microgravity?").run()
    _assert_healthy(app)
    assert any(h.value.startswith("Results") for h in app.subheader)


def _package_names(lines: list[str]) -> set[str]:
    # "sentence-transformers>=6.2.0" -> "sentence-transformers". Lowercase and - vs _ don't
    # matter in package names, so both are normalized.
    names = set()
    for line in lines:
        line = line.split("#")[0].strip()  # drop comments and blank lines
        if line:
            names.add(re.split(r"[<>=!~;\[ ]", line)[0].lower().replace("_", "-"))
    return names


def test_live_app_package_list_covers_pyproject():
    # Community Cloud installs from app/requirements.txt, not uv.lock. A package added only
    # to pyproject.toml would work on our laptops and break the live app.
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    ours = _package_names(pyproject["project"]["dependencies"])
    live = _package_names((ROOT / "app" / "requirements.txt").read_text().splitlines())
    assert ours <= live, f"missing from app/requirements.txt: {sorted(ours - live)}"
