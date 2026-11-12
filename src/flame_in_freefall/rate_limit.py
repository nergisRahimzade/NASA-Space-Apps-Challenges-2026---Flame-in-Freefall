"""Day 16 (BE): a limit on how often something may happen, e.g. summaries sent to Gemini.

Every visitor shares one Gemini key, and the free tier allows only so many requests a minute.
Without a limit, a busy minute (or one person clicking fast) uses the quota up and every
summary after it fails. With one, the extra summaries are quoted from the passages instead."""

import threading
import time
from collections import deque
from collections.abc import Callable


class RateLimiter:
    """Allows at most `max_calls` calls in any `per_seconds` window (a sliding window)."""

    def __init__(
        self,
        max_calls: int,
        per_seconds: float,
        clock: Callable[[], float] = time.monotonic,
    ):
        # bool is a kind of int in Python, so True would pass as 1 without this check.
        if isinstance(max_calls, bool) or not isinstance(max_calls, int) or max_calls <= 0:
            raise ValueError("max_calls must be a whole number above 0")
        if isinstance(per_seconds, bool) or not isinstance(per_seconds, int | float):
            raise ValueError("per_seconds must be a number above 0")
        if per_seconds <= 0:
            raise ValueError("per_seconds must be a number above 0")
        self.max_calls = max_calls
        self.per_seconds = per_seconds
        # The clock can be swapped, so tests move time on without sleeping.
        # time.monotonic only goes forward, even if someone changes the computer's clock.
        self._clock = clock
        self._times: deque[float] = deque()  # when each recent allowed call happened, oldest first
        # Streamlit runs each visitor in its own thread: two calls at the same moment must not
        # both see "one slot left" and both take it.
        self._lock = threading.Lock()

    def allow(self) -> bool:
        """True (and the call is counted) if there is room now; False if the limit is reached."""
        with self._lock:
            now = self._clock()
            # Forget calls that happened a full window ago or more: they no longer count.
            while self._times and now - self._times[0] >= self.per_seconds:
                self._times.popleft()
            if len(self._times) >= self.max_calls:
                return False  # a refused call is not counted, so it can't push the window on
            self._times.append(now)
            return True
