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
