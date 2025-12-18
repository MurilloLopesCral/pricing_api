from datetime import date
from typing import Optional

from fastapi import APIRouter, Header, HTTPException

from analytics.models import AnalyticsQuery, CompareRequest, TimeWindow
from analytics.sql_builder import build_query, normalize_payload
from core.db import run_query
from core.security import require_api_key
from utils.time import month_end, timedelta

from .metrics import METRIC_ALIASES, METRICS

router = APIRouter()


@router.post("/query")
def analytics_query(payload: AnalyticsQuery, x_api_key: Optional[str] = Header(None)):
    require_api_key(x_api_key)
    payload = normalize_payload(payload)
    sql, params, start, end = build_query(payload)
    rows = run_query(sql, params)

    return {
        "time_resolved": {"start": start, "end": end},
        "group_by": payload.group_by,
        "metrics": payload.metrics,
        "rows": rows,
    }


@router.post("/compare")
def analytics_compare(
    req: CompareRequest, x_api_key: Optional[str] = Header(default=None)
):
    require_api_key(x_api_key)

    # valida métrica
    metric = METRIC_ALIASES.get(req.metric, req.metric)
    if metric not in METRICS:
        raise HTTPException(400, f"Métrica inválida: {req.metric}")

    # define âncora = fim do mês
    end_current = month_end(req.anchor.year, req.anchor.month)
    start_current = end_current - timedelta(days=req.window_days)

    end_prev = start_current - timedelta(days=1)
    start_prev = end_prev - timedelta(days=req.window_days)

    def run_range(start_d: date, end_d: date):
        q = AnalyticsQuery(
            time=TimeWindow(
                mode="range", start=start_d.isoformat(), end=end_d.isoformat()
            ),
            filters=req.filters,
            group_by=req.group_by,
            metrics=[metric],
            limit=1000,
        )
        q = normalize_payload(q)
        sql, params, _, _ = build_query(q)
        rows = run_query(sql, params)

        # sem group_by: retorna 1 linha com a métrica
        if not req.group_by:
            value = rows[0].get(metric) if rows else None  # type: ignore
            return value, rows

        return None, rows  # se group_by, você vai comparar linha a linha (opcional)

    cur_value, cur_rows = run_range(start_current, end_current)
    prev_value, prev_rows = run_range(start_prev, end_prev)

    if req.group_by:
        # versão simples: devolve as duas tabelas e o GPT interpreta
        return {
            "anchor": f"{req.anchor.year}-{req.anchor.month:02d}",
            "current": {
                "start": start_current.isoformat(),
                "end": end_current.isoformat(),
                "rows": cur_rows,
            },
            "previous": {
                "start": start_prev.isoformat(),
                "end": end_prev.isoformat(),
                "rows": prev_rows,
            },
            "metric": metric,
        }

    # sem group_by: calcula delta
    if cur_value is None or prev_value is None:
        trend = "indefinido"
        delta_abs = None
        delta_pct = None
    else:
        delta_abs = cur_value - prev_value
        delta_pct = (delta_abs / prev_value) if prev_value not in (0, None) else None
        trend = "aclive" if delta_abs > 0 else "declive" if delta_abs < 0 else "estavel"

    return {
        "anchor": f"{req.anchor.year}-{req.anchor.month:02d}",
        "metric": metric,
        "current": {
            "start": start_current.isoformat(),
            "end": end_current.isoformat(),
            "value": cur_value,
        },
        "previous": {
            "start": start_prev.isoformat(),
            "end": end_prev.isoformat(),
            "value": prev_value,
        },
        "delta_abs": delta_abs,
        "delta_pct": delta_pct,
        "trend": trend,
    }
