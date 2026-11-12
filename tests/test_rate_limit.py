"""Day 16 (BE): RateLimiter lets through at most N calls in any window, and then frees up again.

Every test moves a fake clock instead of sleeping, so they run instantly."""

import threading
import time
from collections import deque

import pytest

from flame_in_freefall.rate_limit import RateLimiter


class FakeClock:
    """A clock that only moves when the test says so."""

    def __init__(self):
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def _limiter(max_calls=3, per_seconds=60):
    clock = FakeClock()
    return RateLimiter(max_calls, per_seconds, clock=clock), clock


def test_allows_up_to_the_limit_then_refuses():
    limiter, _ = _limiter(max_calls=3)
    assert [limiter.allow() for _ in range(4)] == [True, True, True, False]


def test_allows_again_once_the_window_has_passed():
    limiter, clock = _limiter(max_calls=2, per_seconds=60)
    assert limiter.allow() and limiter.allow()
    assert not limiter.allow()
    clock.now += 60  # a full window later, the first two calls no longer count
    assert limiter.allow() and limiter.allow()
    assert not limiter.allow()


def test_is_a_sliding_window_not_a_fixed_minute():
    # Calls at t=0 and t=30. At t=60 only the first has expired, so exactly one slot is free.
    limiter, clock = _limiter(max_calls=2, per_seconds=60)
    assert limiter.allow()  # t=0
    clock.now += 30
    assert limiter.allow()  # t=30
    clock.now += 30  # t=60
    assert limiter.allow()  # the t=0 call has expired
    assert not limiter.allow()  # the t=30 call hasn't


def test_a_refused_call_does_not_extend_the_wait():
    # If refused calls counted, someone clicking over and over would never get a slot back.
    limiter, clock = _limiter(max_calls=1, per_seconds=60)
    assert limiter.allow()
    for _ in range(5):
        clock.now += 10
        assert not limiter.allow()
    clock.now += 10  # 60 s after the one allowed call
    assert limiter.allow()


def test_visitors_at_the_same_moment_cannot_all_take_the_same_slots():
    # Without the lock, threads can all read "5 slots left" before any of them takes one. The gap
    # between reading and taking is tiny, so a slow append stretches it: every thread then reads
    # before anyone has taken a slot, unless the lock makes them queue. (Checked: with the lock
    # removed, this test fails every time. It reaches into `_times` for that reason.)
    class SlowAppendDeque(deque):
        def append(self, item):
            time.sleep(0.005)
            super().append(item)

    limiter, _ = _limiter(max_calls=5)
    limiter._times = SlowAppendDeque()
    results = []
    threads = [threading.Thread(target=lambda: results.append(limiter.allow())) for _ in range(40)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert results.count(True) == 5


@pytest.mark.parametrize("max_calls", [0, -1, 2.5, "3", True, None])
def test_rejects_a_bad_max_calls(max_calls):
    with pytest.raises(ValueError, match="max_calls"):
        RateLimiter(max_calls, 60)


@pytest.mark.parametrize("per_seconds", [0, -5, "60", True, None])
def test_rejects_a_bad_window(per_seconds):
    with pytest.raises(ValueError, match="per_seconds"):
        RateLimiter(3, per_seconds)
