import calendar
import os
from datetime import date, timedelta
from typing import Any, Literal, Optional

import psycopg
from dotenv import load_dotenv
from fastapi import FastAPI, Header, HTTPException
from psycopg.rows import dict_row
from pydantic import BaseModel, Field

load_dotenv()

PG_DSN = os.getenv("PG_DSN", "").strip()
TABLE = os.getenv("TABLE_NAME", "pedido_item").strip()
API_KEY = os.getenv("API_KEY", "").strip()

if not PG_DSN:
    raise RuntimeError("Defina PG_DSN no .env")

# --------------------------
# Schema whitelist (seu Supabase)
# --------------------------
ALLOWED_FIELDS = {
    "id",
    "nota_fiscal",
    "emissao",
    "produto_id",
    "descricao",
    "marca",
    "tipo_estoque",
    "cliente",
    "uf",
    "cidade",
    "quantidade",
    "preco_cheio",
    "preco_unitario",
    "faturamento",
    "cmv",
    "mc",
    "mc_percentual",
    "frete",
    "comissao",
    "icms",
    "pis",
    "cofins",
    "tipo_frete",
    "created_at",
    "custo_reposicao",
}

# --------------------------
# Métricas (tijolinhos)
# Obs: usamos "as <alias>" = o próprio nome da métrica (facilita retorno)
# --------------------------
METRICS = {
    # contagens / volumes
    "linhas": "count(*)::int as linhas",
    "qtde_total": "coalesce(sum(quantidade),0)::int as qtde_total",
    # totais
    "faturamento_total": "coalesce(sum(faturamento),0) as faturamento_total",
    "mc_total": "coalesce(sum(mc),0) as mc_total",
    "cmv_total": "coalesce(sum(cmv),0) as cmv_total",
    # percentuais corretos (ponderados)
    "mc_percentual_ponderado": (
        "case when sum(faturamento)=0 then 0 "
        "else (sum(mc)/sum(faturamento)) end as mc_percentual_ponderado"
    ),
    # médias ponderadas
    "preco_medio_ponderado": (
        "case when sum(quantidade)=0 then 0 "
        "else (sum(faturamento)/sum(quantidade)) end as preco_medio_ponderado"
    ),
    # preço cheio / desconto
    "faturamento_preco_cheio_total": "coalesce(sum(preco_cheio * quantidade),0) as faturamento_preco_cheio_total",
    "desconto_total": "coalesce(sum((preco_cheio - preco_unitario) * quantidade),0) as desconto_total",
    "desconto_percentual_ponderado": (
        "case when sum(preco_cheio*quantidade)=0 then 0 "
        "else (sum((preco_cheio-preco_unitario)*quantidade)/sum(preco_cheio*quantidade)) end as desconto_percentual_ponderado"
    ),
    # custo reposição / markup
    "custo_reposicao_total": "coalesce(sum(custo_reposicao * quantidade),0) as custo_reposicao_total",
    "markup_medio_ponderado": (
        "case when sum(custo_reposicao*quantidade)=0 then null "
        "else (sum(faturamento)/sum(custo_reposicao*quantidade)) end as markup_medio_ponderado"
    ),
    # alertas úteis
    "qtd_abaixo_custo_reposicao": "count(*) filter (where preco_unitario < custo_reposicao)::int as qtd_abaixo_custo_reposicao",
}

# --------------------------
# Apelidos para campos e metricas
# --------------------------
FIELD_ALIASES = {
    "produto_nome": "descricao",
    "produto": "produto_id",
    "nome_produto": "descricao",
    "desc_produto": "descricao",
    "nota": "nota_fiscal",
    "estado": "uf",
}

METRIC_ALIASES = {
    # faturamento
    "faturamento_bruto": "faturamento_total",
    "receita": "faturamento_total",
    "receita_bruta": "faturamento_total",
    # mc (reais)
    "mc_reais": "mc_total",
    "margem_reais": "mc_total",
    "margem": "mc_total",
    "lucro": "mc_total",  # se vocês usarem "lucro" como sinônimo de MC em conversa
    # mc (%) (ponderado)
    "mc_percentual": "mc_percentual_ponderado",
    "mc%": "mc_percentual_ponderado",
    "margem_percentual": "mc_percentual_ponderado",
    "margem_%": "mc_percentual_ponderado",
}


# --------------------------
# Pydantic models
# --------------------------
Op = Literal["=", "!=", ">", ">=", "<", "<=", "in", "between", "like", "ilike"]


class Filter(BaseModel):
    field: str
    op: Op
    value: Any


class Having(BaseModel):
    metric: str
    op: Literal["=", "!=", ">", ">=", "<", "<="]
    value: float


class OrderBy(BaseModel):
    metric: str
    dir: Literal["asc", "desc"] = "desc"


class TimeWindow(BaseModel):
    mode: Literal["rolling", "range"] = "rolling"
    days: Optional[int] = 90
    start: Optional[str] = None  # "YYYY-MM-DD"
    end: Optional[str] = None  # "YYYY-MM-DD"


class AnalyticsQuery(BaseModel):
    time: TimeWindow = Field(default_factory=TimeWindow)
    filters: list[Filter] = Field(default_factory=list)
    group_by: list[str] = Field(default_factory=list)
    metrics: list[str] = Field(default_factory=list)
    having: list[Having] = Field(default_factory=list)
    order_by: list[OrderBy] = Field(default_factory=list)
    limit: int = 200


class ClientSegmentRequest(BaseModel):
    time: TimeWindow = Field(default_factory=TimeWindow)
    min_monthly_revenue: float = 40000
    uf: Optional[str] = None


class AnchorMonth(BaseModel):
    type: Literal["month"] = "month"
    year: int
    month: int


class CompareRequest(BaseModel):
    anchor: AnchorMonth
    window_days: int = 90
    filters: list[Filter] = Field(default_factory=list)
    group_by: list[str] = Field(default_factory=list)
    metric: str = "mc_percentual_ponderado"


# --------------------------
# Helpers
# --------------------------
def require_api_key(x_api_key: Optional[str]):
    if not API_KEY:
        return
    if not x_api_key or x_api_key != API_KEY:
        raise HTTPException(401, "Unauthorized")


def validate_field(field: str):
    if field not in ALLOWED_FIELDS:
        raise HTTPException(400, f"Campo inválido: {field}")


def validate_metric(metric: str):
    if metric not in METRICS:
        raise HTTPException(400, f"Métrica inválida: {metric}")


def resolve_time(tw: TimeWindow):
    if tw.mode == "rolling":
        days = int(tw.days or 90)
        end = date.today()
        start = end - timedelta(days=days)
        return start.isoformat(), end.isoformat()
    if not tw.start or not tw.end:
        raise HTTPException(
            400, "No modo range, informe time.start e time.end (YYYY-MM-DD)."
        )
    return tw.start, tw.end


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
    params: list = []

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


def run_query(sql: str, params: list):
    with psycopg.connect(PG_DSN, row_factory=dict_row) as conn:  # type: ignore
        with conn.cursor() as cur:
            cur.execute(sql, params)  # type: ignore
            return cur.fetchall()


def month_end(year: int, month: int) -> date:
    last_day = calendar.monthrange(year, month)[1]
    return date(year, month, last_day)


def shift_range(end: date, window_days: int):
    start = end - timedelta(days=window_days)
    return start, end


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


# --------------------------
# FastAPI
# --------------------------
app = FastAPI(title="Pricing Analytics API", version="1.0.0")


@app.get("/health")
def health():
    return {"ok": True, "table": TABLE}


@app.post("/analytics/query")
def analytics_query(
    payload: AnalyticsQuery, x_api_key: Optional[str] = Header(default=None)
):
    require_api_key(x_api_key)
    payload = normalize_payload(payload)

    sql, params, start, end = build_query(payload)
    rows = run_query(sql, params)

    return {
        "time_resolved": {"start": start, "end": end},
        "group_by": payload.group_by,
        "metrics": payload.metrics,
        "rows": rows,
        "debug": {
            "sql": sql,  # se não quiser expor, remova
            "params": params,  # se não quiser expor, remova
        },
    }


@app.post("/segments/clients")
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


@app.post("/analytics/compare")
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
