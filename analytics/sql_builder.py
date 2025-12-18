from typing import Any

from fastapi import HTTPException

from core.config import TABLE
from utils.time import resolve_time

from .fields import ALLOWED_FIELDS, FIELD_ALIASES
from .metrics import METRIC_ALIASES, METRICS
from .models import AnalyticsQuery, Filter


def normalize_payload(q: AnalyticsQuery) -> AnalyticsQuery:
    # fields
    for f in q.filters:
        f.field = FIELD_ALIASES.get(f.field, f.field)

        # wildcard automático
        if f.op in ("like", "ilike") and isinstance(f.value, str):
            if "%" not in f.value:
                f.value = f"%{f.value}%"

    q.group_by = [FIELD_ALIASES.get(g, g) for g in q.group_by]
    q.metrics = [METRIC_ALIASES.get(m, m) for m in q.metrics]

    for h in q.having:
        h.metric = METRIC_ALIASES.get(h.metric, h.metric)

    for ob in q.order_by:
        ob.metric = METRIC_ALIASES.get(ob.metric, ob.metric)

    return q


def validate_field(field: str):
    if field not in ALLOWED_FIELDS:
        raise HTTPException(400, f"Campo inválido: {field}")


def validate_metric(metric: str):
    if metric not in METRICS:
        raise HTTPException(400, f"Métrica inválida: {metric}")


def build_where(filters: list[Filter], params: list):
    clauses = []
    for f in filters:
        validate_field(f.field)
        col = f.field

        if f.op in ("=", "!=", ">", ">=", "<", "<="):
            clauses.append(f"{col} {f.op} %s")
            params.append(f.value)

        elif f.op == "in":
            if not isinstance(f.value, list) or len(f.value) == 0:
                raise HTTPException(400, f"Filtro IN exige lista não vazia: {col}")
            placeholders = ", ".join(["%s"] * len(f.value))
            clauses.append(f"{col} in ({placeholders})")
            params.extend(f.value)

        elif f.op == "between":
            if not isinstance(f.value, list) or len(f.value) != 2:
                raise HTTPException(400, f"Filtro BETWEEN exige [min,max]: {col}")
            clauses.append(f"{col} between %s and %s")
            params.extend([f.value[0], f.value[1]])

        elif f.op in ("like", "ilike"):
            # Ex.: "%CRIO%" etc.
            clauses.append(f"unaccent(lower({col})) like unaccent(lower(%s))")
            params.append(f.value)

        else:
            raise HTTPException(400, f"Operador inválido: {f.op}")

    return " and ".join(clauses)


def expr_of_metric(metric: str) -> str:
    # pega só a expressão antes do " as ..."
    return METRICS[metric].split(" as ")[0]


def build_query(q: AnalyticsQuery):
    start, end = resolve_time(q.time)
    params: list[Any] = []

    # group_by + select
    select_parts: list[str] = []
    group_parts: list[str] = []

    for g in q.group_by:
        validate_field(g)
        group_parts.append(g)
        select_parts.append(g)

    if not q.metrics:
        q.metrics = ["faturamento_total", "mc_total", "mc_percentual_ponderado"]

    for m in q.metrics:
        validate_metric(m)
        select_parts.append(METRICS[m])

    sql = f"select {', '.join(select_parts)} from {TABLE}"

    # WHERE com período
    params.extend([start, end])
    base_where = "emissao between %s and %s"

    extra_where = build_where(q.filters, params)
    where_sql = base_where + (f" and {extra_where}" if extra_where else "")
    sql += f" where {where_sql}"

    # GROUP BY
    if group_parts:
        sql += " group by " + ", ".join(group_parts)

    # HAVING (sobre agregados)
    if q.having:
        having_clauses = []
        for h in q.having:
            validate_metric(h.metric)
            having_clauses.append(f"{expr_of_metric(h.metric)} {h.op} %s")
            params.append(h.value)
        sql += " having " + " and ".join(having_clauses)

    # ORDER BY
    if q.order_by:
        order_parts = []
        for ob in q.order_by:
            validate_metric(ob.metric)
            order_parts.append(f"{expr_of_metric(ob.metric)} {ob.dir}")
        sql += " order by " + ", ".join(order_parts)

    # LIMIT
    sql += " limit %s"
    params.append(int(q.limit))

    return sql, params, start, end
    return sql, params, start, end
    return sql, params, start, end
