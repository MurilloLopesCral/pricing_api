from typing import Optional

from fastapi import APIRouter, Header, HTTPException

from core.config import TABLE
from core.db import run_query
from core.security import require_api_key
from utils.time import resolve_time

from .models import ClientSegmentRequest

router = APIRouter()


@router.post("/segments/clients")
def segment_clients(
    req: ClientSegmentRequest, x_api_key: Optional[str] = Header(default=None)
):
    require_api_key(x_api_key)

    start, end = resolve_time(req.time)
    params = [start, end]

    where = "emissao between %s and %s"
    if req.uf:
        if req.uf not in (
            "AC",
            "AL",
            "AP",
            "AM",
            "BA",
            "CE",
            "DF",
            "ES",
            "GO",
            "MA",
            "MT",
            "MS",
            "MG",
            "PA",
            "PB",
            "PR",
            "PE",
            "PI",
            "RJ",
            "RN",
            "RS",
            "RO",
            "RR",
            "SC",
            "SP",
            "SE",
            "TO",
        ):
            raise HTTPException(400, "UF inválida")
        where += " and uf = %s"
        params.append(req.uf)

    sql = f"""
    with mensal as (
      select
        cliente,
        date_trunc('month', emissao)::date as mes,
        sum(faturamento) as faturamento_mes
      from {TABLE}
      where {where}
      group by cliente, date_trunc('month', emissao)::date
    )
    select distinct cliente
    from mensal
    where faturamento_mes >= %s
    order by cliente
    """
    params.append(float(req.min_monthly_revenue))  # type: ignore

    rows = run_query(sql, params)
    return {
        "time_resolved": {"start": start, "end": end},
        "min_monthly_revenue": req.min_monthly_revenue,
        "uf": req.uf,
        "clientes": [r["cliente"] for r in rows],  # type: ignore
        "debug": {"sql": sql, "params": params},
    }
