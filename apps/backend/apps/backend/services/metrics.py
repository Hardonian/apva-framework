"""Efficient tenant metrics aggregation, caching, and trend computation."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config import settings
from ..models import EvaluationJob, TelemetryEvent
from ..observability import RuntimeMetrics


@dataclass(frozen=True)
class MacroTVYMetrics:
    """Aggregated TVY, value, and data-quality metrics for one tenant."""

    telemetry_count: int
    evaluation_count: int
    avg_human_baseline_min: float
    avg_ai_augmented_min: float
    avg_gross_time_saved_min: float
    avg_guardrail_tax_min: float
    avg_rag_reliability_coefficient: float
    avg_hourly_rate_usd: float | None
    macro_tvy_min: float
    macro_tvy_usd: float | None
    total_tvy_min: float
    total_tvy_usd: float | None
    value_per_1000_events_usd: float | None
    shadow_event_count: int
    shadow_event_rate: float
    hourly_rate_coverage: float
    is_net_positive: bool


@dataclass(frozen=True)
class _CacheEntry:
    expires_at: float
    value: MacroTVYMetrics


_metrics_cache: dict[int, _CacheEntry] = {}


def invalidate_metrics_cache(tenant_id: int) -> None:
    """Invalidate a tenant aggregate after a write."""
    _metrics_cache.pop(tenant_id, None)
    RuntimeMetrics.record_cache("invalidation")


def reset_metrics_cache() -> None:
    """Clear cached aggregates for deterministic tests and maintenance."""
    _metrics_cache.clear()


async def compute_macro_tvy_metrics(
    session: AsyncSession,
    tenant_id: int,
) -> MacroTVYMetrics:
    """Compute tenant metrics, reusing a short-lived immutable aggregate."""
    now = time.monotonic()
    cached = _metrics_cache.get(tenant_id)
    if cached is not None and cached.expires_at > now:
        RuntimeMetrics.record_cache("hit")
        return cached.value

    RuntimeMetrics.record_cache("miss")
    telemetry_result = await session.execute(
        select(
            func.count(TelemetryEvent.id),
            func.avg(TelemetryEvent.human_baseline_time),
            func.avg(TelemetryEvent.ai_augmented_time),
            func.avg(TelemetryEvent.guardrail_latency_tax),
            func.avg(TelemetryEvent.hourly_rate_usd),
            func.count(TelemetryEvent.hourly_rate_usd),
            func.sum(TelemetryEvent.is_shadow),
        ).where(TelemetryEvent.tenant_id == tenant_id)
    )
    (
        telemetry_count,
        avg_human,
        avg_ai,
        avg_guardrail,
        avg_hourly_rate,
        hourly_rate_count,
        shadow_event_count,
    ) = telemetry_result.one()

    eval_result = await session.execute(
        select(
            func.count(EvaluationJob.id),
            func.avg(EvaluationJob.rag_reliability_coefficient),
        ).where(
            EvaluationJob.status == "completed",
            EvaluationJob.tenant_id == tenant_id,
        )
    )
    evaluation_count, avg_reliability = eval_result.one()

    count = int(telemetry_count or 0)
    evaluation_count_int = int(evaluation_count or 0)
    avg_human_float = float(avg_human or 0.0)
    avg_ai_float = float(avg_ai or 0.0)
    avg_guardrail_float = float(avg_guardrail or 0.0)
    avg_hourly_rate_float = float(avg_hourly_rate) if avg_hourly_rate is not None else None
    avg_reliability_float = float(
        avg_reliability if avg_reliability is not None else settings.default_rag_reliability
    )
    shadow_count = int(shadow_event_count or 0)

    avg_gross_time_saved = avg_human_float - avg_ai_float
    macro_tvy = (avg_gross_time_saved * avg_reliability_float) - avg_guardrail_float
    macro_tvy_usd = (
        (macro_tvy / 60.0) * avg_hourly_rate_float
        if avg_hourly_rate_float is not None
        else None
    )
    total_tvy_min = macro_tvy * count
    total_tvy_usd = macro_tvy_usd * count if macro_tvy_usd is not None else None

    metrics = MacroTVYMetrics(
        telemetry_count=count,
        evaluation_count=evaluation_count_int,
        avg_human_baseline_min=avg_human_float,
        avg_ai_augmented_min=avg_ai_float,
        avg_gross_time_saved_min=avg_gross_time_saved,
        avg_guardrail_tax_min=avg_guardrail_float,
        avg_rag_reliability_coefficient=avg_reliability_float,
        avg_hourly_rate_usd=avg_hourly_rate_float,
        macro_tvy_min=macro_tvy,
        macro_tvy_usd=macro_tvy_usd,
        total_tvy_min=total_tvy_min,
        total_tvy_usd=total_tvy_usd,
        value_per_1000_events_usd=(
            macro_tvy_usd * 1000.0 if macro_tvy_usd is not None else None
        ),
        shadow_event_count=shadow_count,
        shadow_event_rate=(shadow_count / count if count else 0.0),
        hourly_rate_coverage=(int(hourly_rate_count or 0) / count if count else 0.0),
        is_net_positive=macro_tvy > 0.0,
    )

    if settings.metrics_cache_ttl_seconds > 0:
        _metrics_cache[tenant_id] = _CacheEntry(
            expires_at=now + settings.metrics_cache_ttl_seconds,
            value=metrics,
        )
    return metrics


async def compute_tvy_timeseries(
    session: AsyncSession,
    tenant_id: int,
    days: int,
) -> list[dict[str, Any]]:
    """Return a real daily trend using one grouped database query."""
    now = datetime.now(timezone.utc)
    first_day = (now - timedelta(days=days - 1)).date()
    start = datetime.combine(first_day, datetime.min.time(), tzinfo=timezone.utc)
    end = datetime.combine(now.date() + timedelta(days=1), datetime.min.time(), tzinfo=timezone.utc)

    day = func.date(TelemetryEvent.created_at).label("day")
    result = await session.execute(
        select(
            day,
            func.count(TelemetryEvent.id),
            func.avg(TelemetryEvent.human_baseline_time),
            func.avg(TelemetryEvent.ai_augmented_time),
            func.avg(TelemetryEvent.guardrail_latency_tax),
            func.avg(TelemetryEvent.hourly_rate_usd),
        )
        .where(
            TelemetryEvent.tenant_id == tenant_id,
            TelemetryEvent.created_at >= start,
            TelemetryEvent.created_at < end,
        )
        .group_by(day)
        .order_by(day)
    )
    rows: dict[date, tuple[Any, ...]] = {}
    for db_row in result.all():
        day_value = db_row[0]
        day_key = day_value if isinstance(day_value, date) else date.fromisoformat(str(day_value))
        rows[day_key] = tuple(db_row[1:])

    macro = await compute_macro_tvy_metrics(session, tenant_id)
    points: list[dict[str, Any]] = []
    for offset in range(days):
        current_day = first_day + timedelta(days=offset)
        daily_values = rows.get(current_day)
        if daily_values is None:
            count, avg_human, avg_ai, avg_guardrail, avg_rate = 0, 0.0, 0.0, 0.0, None
        else:
            count, avg_human, avg_ai, avg_guardrail, avg_rate = daily_values

        gross = float(avg_human or 0.0) - float(avg_ai or 0.0)
        guardrail = float(avg_guardrail or 0.0)
        tvy = (gross * macro.avg_rag_reliability_coefficient) - guardrail if count else 0.0
        hourly_rate = float(avg_rate) if avg_rate is not None else macro.avg_hourly_rate_usd
        tvy_usd = (tvy / 60.0) * hourly_rate if hourly_rate is not None else 0.0
        efficiency = (tvy / float(avg_human) * 100.0) if avg_human else 0.0
        points.append(
            {
                "name": current_day.strftime("%a"),
                "date": current_day.isoformat(),
                "tvy": round(tvy, 2),
                "tvyUsd": round(tvy_usd, 2),
                "sample_count": int(count or 0),
                "avg_guardrail_tax_min": round(guardrail, 3),
                "efficiency_percent": round(efficiency, 1),
                "data_source": "observed" if count else "no_data",
            }
        )
    return points
