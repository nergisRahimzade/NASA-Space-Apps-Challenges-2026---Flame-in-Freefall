"""Day 18 (BE): is the live app up? A small check that the scheduled GitHub job runs.

    uv run --no-project python -m flame_in_freefall.uptime            # PYTHONPATH=src
    uv run python -m flame_in_freefall.uptime --url https://example.com

Three answers, measured against the live app on 2026-11-13:
- up: https://<app>/~/+/_stcore/health answers the plain text "ok". Streamlit's own health
  address is only reachable under "/~/+/" (without it, the hosting platform's wrapper page
  answers instead, which is why D07 couldn't use it from CI).
- asleep: the app's page still answers 200, but the health address doesn't say "ok" (and isn't
  a server error). Community Cloud puts an app to sleep after 12 hours without traffic, and a
  visitor wakes it in about a minute. NOT observed yet: we couldn't make the live app sleep, so
  what a sleeping app really answers is unknown. This state is "the address exists, the app
  isn't answering ok". If a sleeping app's health address answers a 5xx, it shows as down.
- down: no answer, a timeout, a broken reply, a server error (5xx) from the health address, or an
  error status from the page such as 404 (an app name that doesn't exist).

"up" means Streamlit's server is running, NOT that the page works: Streamlit answers "ok" without
running the page, so a page that crashes for every visitor (like the KeyError on 2026-11-06)
still shows as up. tests/test_app.py, before each merge, is what checks the page itself.

Only the standard library is used, so the GitHub job needs no `uv sync`. The exit code is 0 only
for "up", so a scheduled run that isn't up shows as failed and GitHub emails whoever set it up."""

import argparse
import http.client
import http.cookiejar
import logging
import time
import urllib.error
import urllib.request
from collections.abc import Callable

from flame_in_freefall.config import setup_logging

LIVE_URL = "https://crc-flame-in-freefall.streamlit.app"
HEALTH_PATH = "/~/+/_stcore/health"
TIMEOUT_S = 20
READ_BYTES = 1000  # the health answer is "ok"; a page is never read past its first bytes

log = logging.getLogger("flame_in_freefall.uptime")

# An opener takes (url, timeout) and returns (HTTP status, start of the body). Tests pass a fake.
Opener = Callable[[str, float], tuple[int, str]]


def _make_opener() -> Opener:
    # A cookie jar, because the app's address first redirects through share.streamlit.io, which
    # sets a cookie. No personal details in the User-Agent: it's a plain name for the check.
    jar = http.cookiejar.CookieJar()
    real = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))

    def open_url(url: str, timeout: float) -> tuple[int, str]:
        request = urllib.request.Request(url, headers={"User-Agent": "flame-uptime-check"})
        try:
            with real.open(request, timeout=timeout) as response:
                return response.status, response.read(READ_BYTES).decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            return e.code, ""  # an error status is an answer, not a crash

    return open_url


def _result(url: str, state: str, status: int | None, detail: str, start: float) -> dict:
    return {
        "url": url,
        "state": state,
        "status": status,
        "detail": detail,
        "seconds": round(time.perf_counter() - start, 2),
    }


def check(url: str = LIVE_URL, opener: Opener | None = None, timeout: float = TIMEOUT_S) -> dict:
    """Return {"url", "state", "status", "detail", "seconds"}; state is up, asleep or down.
    Never raises: a network problem is the answer "down"."""
    start = time.perf_counter()
    base = url.rstrip("/")
    opener = opener or _make_opener()
    try:
        status, body = opener(base + HEALTH_PATH, timeout)
        if status == 200 and body.strip() == "ok":
            return _result(base, "up", status, "the app's health address answered ok", start)
        # A server error from the health address is a clear "broken", even if the platform's page
        # in front of the app still answers. Keep that status, so the log says what really failed.
        if status >= 500:
            return _result(
                base, "down", status, f"the health address answered HTTP {status}", start
            )
        # Not "ok": is the address there at all? The page itself tells asleep from nonexistent.
        status, _ = opener(base + "/", timeout)
    # OSError covers URLError, timeouts and refused connections; HTTPException, broken replies.
    except (OSError, http.client.HTTPException) as e:
        return _result(base, "down", None, f"{type(e).__name__}: {e}", start)
    if status == 200:
        return _result(base, "asleep", status, "the page answers but the app didn't say ok", start)
    return _result(base, "down", status, f"the page answered HTTP {status}", start)


def main(argv: list[str] | None = None, opener: Opener | None = None) -> None:
    parser = argparse.ArgumentParser(description="Check whether the live app is up.")
    parser.add_argument("--url", default=LIVE_URL, help="the app's address (default: the live app)")
    args = parser.parse_args(argv)
    setup_logging()
    result = check(args.url, opener=opener)
    log.info(
        "%s is %s (HTTP %s, %.2f s): %s",
        result["url"],
        result["state"].upper(),
        result["status"],
        result["seconds"],
        result["detail"],
    )
    if result["state"] != "up":
        # A non-zero exit code makes the scheduled GitHub run fail, which is what sends the email.
        raise SystemExit(1)


if __name__ == "__main__":
    main()
