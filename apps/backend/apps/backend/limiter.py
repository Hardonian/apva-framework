"""Rate limiting for the APVA backend.

SlowAPI's ``SlowAPIMiddleware`` cannot see handlers mounted via
``app.include_router(...)`` (they become ``_IncludedRouter`` objects without an
``endpoint`` attribute), so the middleware silently skips limiting for every
route. Additionally, SlowAPI's default ``get_remote_address`` returns an empty
string when a request has no ``client`` (behind some proxies / in the ASGI test
transport), which makes its ``all(args)`` check falsy and disables the limit.

To get reliable, verifiable enforcement we use a small self-contained fixed
-window limiter as a FastAPI dependency (``rate_limit``). It is mounted on every
router via ``dependencies=[Depends(rate_limit)]`` in ``main.py``. The previous
SlowAPI limiter/middleware is kept registered only for backward compatibility
and does not perform enforcement.
"""

from __future__ import annotations

import time
from collections import defaultdict

from fastapi import Request

# (key, window_start) -> count
_hits: dict[tuple[str, int], int] = defaultdict(int)
# default: 100 requests per 60 seconds per client
LIMIT = 100
WINDOW = 60


class RateLimitError(Exception):
    """Raised when a client exceeds the global rate limit."""


def _client_key(request: Request) -> str:
    """Stable per-client key; falls back to a constant when unknown.

    Avoids silently disabling limits when ``request.client`` is ``None``.
    """
    if request.client and request.client.host:
        return request.client.host
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return "anonymous"


def rate_limit(request: Request) -> None:
    """Enforce a global fixed-window rate limit.

    Raises ``RateLimitError`` (mapped to HTTP 429 by the registered
    exception handler in ``main.py``) when the client exceeds the limit.
    """
    key = _client_key(request)
    window = int(time.time() // WINDOW)
    bucket = (key, window)
    _hits[bucket] += 1
    if _hits[bucket] > LIMIT:
        # Clean up the current window bucket to avoid unbounded growth.
        raise RateLimitError("global")
