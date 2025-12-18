from calendar import monthrange
from datetime import date
from typing import Any, Optional

from fastapi import APIRouter, Header

from core.config import TABLE
from core.db import run_query
from core.security import require_api_key

from .models import RecurringClientsRequest, RecurringClientsResponse

router = APIRouter()


@router.post("/recurring", response_model=RecurringClientsResponse)
def recurring_clients(
    payload: RecurringClientsRequest,
    x_api_key: Optional[str] = Header(None),
):
    require_api_key(x_api_key)

    months = sorted(payload.months)
    if not months:
        return {"year": payload.year, "months": months, "clientes": []}

    start = date(payload.year, months[0], 1)
    last_month = months[-1]
    end = date(
        payload.year,
        last_month,
        monthrange(payload.year, last_month)[1],
    )

    # --------------------
    # WHERE dinâmico
    # --------------------
    where_filters = []
    params: list[Any] = []

    if payload.uf:
        where_filters.append("uf = %s")
        params.append(payload.uf)

    where_extra = ""
    if where_filters:
        where_extra = " AND " + " AND ".join(where_filters)

    # --------------------
    # HAVING dinâmico
    # --------------------
    having_clauses = ["count(distinct mes) = %s"]

    # SQL base
    sql = f"""
        WITH mensal AS (
            SELECT
                cliente,
                date_trunc('month', emissao)::date AS mes,
                sum(faturamento) AS faturamento_mes
            FROM {TABLE}
            WHERE emissao BETWEEN %s AND %s
            {where_extra}
            GROUP BY cliente, date_trunc('month', emissao)
        )
        SELECT
            cliente,
            sum(faturamento_mes) AS faturamento_total
        FROM mensal
        GROUP BY cliente
    """

    # ordem dos params precisa bater com os %s
    params = [start, end] + params
    params.append(len(months))

    if payload.min_total_revenue is not None:
        having_clauses.append("sum(faturamento_mes) >= %s")
        params.append(payload.min_total_revenue)

    # injeta HAVING corretamente
    sql += " HAVING " + " AND ".join(having_clauses)
    sql += " ORDER BY faturamento_total DESC"

    print(sql)
    print(params)

    rows = run_query(sql, params)

    return {
        "year": payload.year,
        "months": months,
        "clientes": rows,
    }
