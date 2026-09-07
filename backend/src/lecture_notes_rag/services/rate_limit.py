from __future__ import annotations

import time
from collections.abc import Callable


class RequestPacer:
    """Serializes outbound embedding calls below a configured request rate."""

    def __init__(
        self,
        requests_per_minute: int,
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ):
        self._minimum_interval = 60 / requests_per_minute
        self._clock = clock
        self._sleep = sleep
        self._next_request_at = 0.0

    def wait_for_slot(self, units: int = 1) -> None:
        if units < 1:
            raise ValueError("units must be at least one")
        now = self._clock()
        if self._next_request_at > now:
            self._sleep(self._next_request_at - now)
            now = self._clock()
        self._next_request_at = now + (self._minimum_interval * units)

    def defer_for(self, seconds: float) -> None:
        self._next_request_at = max(self._next_request_at, self._clock() + seconds)
