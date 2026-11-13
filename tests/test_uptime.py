"""Day 18 (BE): the uptime check tells up, asleep and down apart (a fake opener: no network)."""

import http.client

import pytest

from flame_in_freefall import uptime

BASE = "https://app.example"


def _opener(answers: dict):
    # answers: address -> (status, body) to return, or an exception to raise
    asked = []

    def open_url(url, timeout):
        asked.append(url)
        answer = answers[url]
        if isinstance(answer, Exception):
            raise answer
        return answer

    open_url.asked = asked
    return open_url


def test_health_ok_means_up_and_the_page_is_not_asked():
    opener = _opener({BASE + uptime.HEALTH_PATH: (200, "ok\n")})
    result = uptime.check(BASE, opener=opener)
    assert result["state"] == "up" and result["status"] == 200
    assert opener.asked == [BASE + uptime.HEALTH_PATH]


def test_a_trailing_slash_in_the_address_is_fine():
    opener = _opener({BASE + uptime.HEALTH_PATH: (200, "ok")})
    assert uptime.check(BASE + "/", opener=opener)["state"] == "up"


def test_a_page_that_answers_but_does_not_say_ok_is_asleep():
    opener = _opener(
        {BASE + uptime.HEALTH_PATH: (200, "<html>wake me</html>"), BASE + "/": (200, "")}
    )
    assert uptime.check(BASE, opener=opener)["state"] == "asleep"


def test_a_missing_app_is_down():
    # What a made-up app name really answered on 2026-11-13: 404 with no health.
    opener = _opener({BASE + uptime.HEALTH_PATH: (404, ""), BASE + "/": (404, "")})
    result = uptime.check(BASE, opener=opener)
    assert (result["state"], result["status"]) == ("down", 404)


def test_a_server_error_is_down():
    opener = _opener({BASE + uptime.HEALTH_PATH: (503, ""), BASE + "/": (503, "")})
    assert uptime.check(BASE, opener=opener)["state"] == "down"


def test_a_health_server_error_is_down_even_when_the_page_answers():
    # The platform's page can answer 200 while the app behind it fails; keep the app's status.
    opener = _opener({BASE + uptime.HEALTH_PATH: (503, ""), BASE + "/": (200, "")})
    result = uptime.check(BASE, opener=opener)
    assert (result["state"], result["status"]) == ("down", 503)
    assert opener.asked == [BASE + uptime.HEALTH_PATH]  # no need to ask the page


def test_a_timeout_is_down_not_a_crash():
    opener = _opener({BASE + uptime.HEALTH_PATH: TimeoutError("timed out")})
    result = uptime.check(BASE, opener=opener)
    assert result["state"] == "down" and "TimeoutError" in result["detail"]


def test_no_connection_is_down_not_a_crash():
    opener = _opener({BASE + uptime.HEALTH_PATH: ConnectionRefusedError("refused")})
    assert uptime.check(BASE, opener=opener)["state"] == "down"


def test_a_broken_reply_is_down_not_a_crash():
    # http.client.HTTPException is not an OSError, so it needs its own catch.
    opener = _opener({BASE + uptime.HEALTH_PATH: http.client.BadStatusLine("garbage")})
    assert uptime.check(BASE, opener=opener)["state"] == "down"


def test_the_page_failing_after_a_bad_health_answer_is_down():
    opener = _opener({BASE + uptime.HEALTH_PATH: (200, "nope"), BASE + "/": OSError("reset")})
    assert uptime.check(BASE, opener=opener)["state"] == "down"


def test_exit_code_is_zero_only_when_up():
    up = _opener({BASE + uptime.HEALTH_PATH: (200, "ok")})
    uptime.main(["--url", BASE], opener=up)  # returns normally


@pytest.mark.parametrize("health, page", [((200, "x"), (200, "")), ((404, ""), (404, ""))])
def test_asleep_and_down_both_fail_the_run(health, page):
    opener = _opener({BASE + uptime.HEALTH_PATH: health, BASE + "/": page})
    with pytest.raises(SystemExit) as stop:
        uptime.main(["--url", BASE], opener=opener)
    assert stop.value.code == 1


def test_the_default_address_is_the_live_app():
    assert uptime.LIVE_URL == "https://crc-flame-in-freefall.streamlit.app"
