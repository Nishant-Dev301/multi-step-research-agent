"""
API rate limiting — advanced/hardening enhancement (see ENHANCEMENTS.md).

Status: 🟢 stubbed & runnable as a standalone limiter, 🟡 not wired into
main.py yet (needs an API-key auth layer first so limits are per-caller
rather than global).

A per-key sliding-window limiter — small enough to run in-process for a
single-server demo. For multi-instance deployments, back this with Redis
(INCR + EXPIRE) instead of the in-memory dict below.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque


class RateLimiter:
    def __init__(self, max_requests: int = 20, window_seconds: int = 60):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._calls: dict[str, deque] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.time()
        window = self._calls[key]
        while window and now - window[0] > self.window_seconds:
            window.popleft()
        if len(window) >= self.max_requests:
            return False
        window.append(now)
        return True


# Example wiring once API keys exist:
#
#   limiter = RateLimiter(max_requests=20, window_seconds=60)
#
#   @app.post("/research")
#   def research(req: ResearchRequest, api_key: str = Header(...)):
#       if not limiter.allow(api_key):
#           raise HTTPException(429, "rate limit exceeded, try again shortly")
#       ...
