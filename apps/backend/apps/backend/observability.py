"""Low-overhead, dependency-free runtime observability for the API process."""

from __future__ import annotations

import threading
from collections import defaultdict


def _escape_label(value: str) -> str:
    """Escape a Prometheus label value."""
    return value.replace("\\", "\\\\").replace("\n", "\\n").replace('"', '\\"')


class RuntimeMetrics:
    """Collect bounded HTTP and cache telemetry for Prometheus scraping.

    Route templates are used instead of raw URLs, so user-provided path values
    cannot create an unbounded number of metric series.
    """

    _lock = threading.Lock()
    _requests: dict[tuple[str, str, int], int] = defaultdict(int)
    _duration_seconds: dict[tuple[str, str], float] = defaultdict(float)
    _duration_max_seconds: dict[tuple[str, str], float] = defaultdict(float)
    _in_flight = 0
    _cache_events: dict[str, int] = defaultdict(int)

    @classmethod
    def request_started(cls) -> None:
        with cls._lock:
            cls._in_flight += 1

    @classmethod
    def request_finished(
        cls,
        *,
        method: str,
        route: str,
        status_code: int,
        duration_seconds: float,
    ) -> None:
        request_key = (method, route, status_code)
        duration_key = (method, route)
        with cls._lock:
            cls._in_flight = max(0, cls._in_flight - 1)
            cls._requests[request_key] += 1
            cls._duration_seconds[duration_key] += duration_seconds
            cls._duration_max_seconds[duration_key] = max(
                cls._duration_max_seconds[duration_key], duration_seconds
            )

    @classmethod
    def record_cache(cls, outcome: str) -> None:
        if outcome not in {"hit", "miss", "invalidation"}:
            raise ValueError(f"Unsupported cache outcome: {outcome}")
        with cls._lock:
            cls._cache_events[outcome] += 1

    @classmethod
    def render_prometheus(cls) -> str:
        """Render a consistent snapshot in Prometheus text format."""
        with cls._lock:
            requests = dict(cls._requests)
            duration_seconds = dict(cls._duration_seconds)
            duration_max_seconds = dict(cls._duration_max_seconds)
            cache_events = dict(cls._cache_events)
            in_flight = cls._in_flight

        lines = [
            "# HELP apva_http_requests_total HTTP requests handled by this process",
            "# TYPE apva_http_requests_total counter",
        ]
        for (method, route, status_code), count in sorted(requests.items()):
            labels = (
                f'method="{_escape_label(method)}",'
                f'route="{_escape_label(route)}",status="{status_code}"'
            )
            lines.append(f"apva_http_requests_total{{{labels}}} {count}")

        lines.extend(
            [
                "# HELP apva_http_request_duration_seconds_total Cumulative HTTP request time",
                "# TYPE apva_http_request_duration_seconds_total counter",
            ]
        )
        for (method, route), duration in sorted(duration_seconds.items()):
            labels = f'method="{_escape_label(method)}",route="{_escape_label(route)}"'
            lines.append(f"apva_http_request_duration_seconds_total{{{labels}}} {duration:.6f}")

        lines.extend(
            [
                "# HELP apva_http_request_duration_seconds_max Maximum observed HTTP request time",
                "# TYPE apva_http_request_duration_seconds_max gauge",
            ]
        )
        for (method, route), duration in sorted(duration_max_seconds.items()):
            labels = f'method="{_escape_label(method)}",route="{_escape_label(route)}"'
            lines.append(f"apva_http_request_duration_seconds_max{{{labels}}} {duration:.6f}")

        lines.extend(
            [
                "# HELP apva_http_requests_in_flight HTTP requests currently being processed",
                "# TYPE apva_http_requests_in_flight gauge",
                f"apva_http_requests_in_flight {in_flight}",
                "# HELP apva_metrics_cache_events_total TVY metrics cache outcomes",
                "# TYPE apva_metrics_cache_events_total counter",
            ]
        )
        for outcome in ("hit", "miss", "invalidation"):
            lines.append(
                f'apva_metrics_cache_events_total{{outcome="{outcome}"}} '
                f"{cache_events.get(outcome, 0)}"
            )
        return "\n".join(lines) + "\n"

    @classmethod
    def reset(cls) -> None:
        """Reset process metrics for deterministic tests."""
        with cls._lock:
            cls._requests.clear()
            cls._duration_seconds.clear()
            cls._duration_max_seconds.clear()
            cls._cache_events.clear()
            cls._in_flight = 0
