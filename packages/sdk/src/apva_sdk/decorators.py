"""Async decorators for APVA SDK telemetry capture."""

from __future__ import annotations

import asyncio
import inspect
import time
from collections.abc import Awaitable, Callable
from functools import wraps
from typing import Any, ParamSpec, TypeVar
from uuid import uuid4

from apva_sdk.client import APVATelemetryClient, TelemetryEventPayload, get_default_client

P = ParamSpec("P")
T = TypeVar("T")


def _ensure_async_result(result: Awaitable[T] | T) -> Awaitable[T]:
    """Return an awaitable result for sync or async functions.

    Args:
        result: Function result or awaitable.

    Returns:
        Awaitable[T]: Awaitable result.
    """
    if inspect.isawaitable(result):
        return result

    async def _async_result() -> T:
        return result

    return _async_result()


def apva_track_latency(
    *,
    client: APVATelemetryClient | None = None,
    app_name: str | None = None,
    session_id: str | None = None,
    run_id: str | None = None,
    human_baseline_time: float | None = None,
    hourly_rate_usd: float | None = None,
    is_shadow: bool = False,
    metadata: dict[str, Any] | None = None,
) -> Callable[[Callable[P, Awaitable[T] | T]], Callable[P, Awaitable[T]]]:
    """Track AI-augmented latency and stream APVA telemetry.

    Args:
        client: Telemetry client. Defaults to a new SDK client.
        app_name: Client application name.
        session_id: Client session ID.
        run_id: Client run ID.
        human_baseline_time: Human baseline time in minutes.
        hourly_rate_usd: Optional hourly rate.
        is_shadow: Shadow mode flag.
        metadata: Optional metadata.

    Returns:
        Callable: Decorator that records latency after the wrapped call.
    """
    telemetry_client = client or get_default_client()
    default_app_name = app_name or telemetry_client.app_name
    default_session_id = session_id or telemetry_client.session_id
    default_run_id = run_id or uuid4().hex
    default_metadata = metadata or {}

    def decorator(func: Callable[P, Awaitable[T] | T]) -> Callable[P, Awaitable[T]]:
        """Wrap an async function and send latency telemetry.

        Args:
            func: Async function to wrap.

        Returns:
            Callable: Wrapped function.
        """

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            """Execute the function and send latency telemetry."""
            start = time.perf_counter()
            result = func(*args, **kwargs)
            awaited = await _ensure_async_result(result)
            elapsed_min = (time.perf_counter() - start) / 60.0
            payload = TelemetryEventPayload(
                app_name=default_app_name,
                session_id=default_session_id,
                run_id=default_run_id,
                human_baseline_time=float(human_baseline_time or 0.0),
                ai_augmented_time=elapsed_min,
                guardrail_latency_tax=0.0,
                session_iterations=1,
                hourly_rate_usd=hourly_rate_usd,
                is_shadow=is_shadow,
                metadata=dict(default_metadata),
            )
            telemetry_client.ingest_async(payload)
            return awaited

        return wrapper

    return decorator


def apva_guardrail_check(
    *,
    client: APVATelemetryClient | None = None,
    app_name: str | None = None,
    session_id: str | None = None,
    run_id: str | None = None,
    human_baseline_time: float | None = None,
    ai_augmented_time: float | None = None,
    session_iterations: int = 1,
    hourly_rate_usd: float | None = None,
    is_shadow: bool = False,
    metadata: dict[str, Any] | None = None,
) -> Callable[[Callable[P, Awaitable[T] | T]], Callable[P, Awaitable[T]]]:
    """Track guardrail latency tax and stream APVA telemetry.

    Args:
        client: Telemetry client. Defaults to a new SDK client.
        app_name: Client application name.
        session_id: Client session ID.
        run_id: Client run ID.
        human_baseline_time: Human baseline time in minutes.
        ai_augmented_time: AI-augmented time in minutes.
        session_iterations: Session iteration count.
        hourly_rate_usd: Optional hourly rate.
        is_shadow: Shadow mode flag.
        metadata: Optional metadata.

    Returns:
        Callable: Decorator that records guardrail tax after the wrapped call.
    """
    telemetry_client = client or get_default_client()
    default_app_name = app_name or telemetry_client.app_name
    default_session_id = session_id or telemetry_client.session_id
    default_run_id = run_id or uuid4().hex
    default_metadata = metadata or {}

    def decorator(func: Callable[P, Awaitable[T] | T]) -> Callable[P, Awaitable[T]]:
        """Wrap an async function and send guardrail telemetry.

        Args:
            func: Async function to wrap.

        Returns:
            Callable: Wrapped function.
        """

        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            """Execute the function and send guardrail telemetry."""
            start = time.perf_counter()
            result = func(*args, **kwargs)
            awaited = await _ensure_async_result(result)
            guardrail_latency_tax = (time.perf_counter() - start) / 60.0
            payload = TelemetryEventPayload(
                app_name=default_app_name,
                session_id=default_session_id,
                run_id=default_run_id,
                human_baseline_time=float(human_baseline_time or 0.0),
                ai_augmented_time=float(ai_augmented_time or 0.0),
                guardrail_latency_tax=guardrail_latency_tax,
                session_iterations=session_iterations,
                hourly_rate_usd=hourly_rate_usd,
                is_shadow=is_shadow,
                metadata=dict(default_metadata),
            )
            telemetry_client.ingest_async(payload)
            return awaited

        return wrapper

    return decorator
