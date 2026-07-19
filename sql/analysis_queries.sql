-- Consultas de analise contra gold.db (gerado por src/gold.py).
-- Uso: sqlite3 gold.db < sql/analysis_queries.sql

-- 1) Visao geral: receita, custo, parcela, DSCR e resultado liquido medio por veiculo
SELECT
    v.placa,
    v.modelo,
    ROUND(AVG(r.receita_total), 2)              AS receita_media_mensal,
    ROUND(AVG(r.custo_operacional_total), 2)    AS custo_operacional_medio,
    ROUND(AVG(r.parcela_financiamento), 2)      AS parcela_financiamento,
    ROUND(AVG(r.resultado_operacional), 2)      AS resultado_operacional_medio,
    ROUND(AVG(r.dscr), 2)                       AS dscr_medio,
    ROUND(AVG(r.resultado_liquido), 2)          AS resultado_liquido_medio
FROM gold_resultado_mensal r
JOIN gold_dim_veiculo v ON v.veiculo_id = r.veiculo_id
GROUP BY v.veiculo_id
ORDER BY resultado_liquido_medio DESC;


-- 2) Custo por km medio por veiculo (eficiencia operacional)
SELECT
    v.placa,
    ROUND(AVG(r.custo_por_km), 2) AS custo_por_km_medio,
    ROUND(AVG(r.km_rodado), 0)    AS km_rodado_medio_mes
FROM gold_resultado_mensal r
JOIN gold_dim_veiculo v ON v.veiculo_id = r.veiculo_id
GROUP BY v.veiculo_id
ORDER BY custo_por_km_medio ASC;


-- 3) Situacao de payback ao final do periodo de dados disponivel
SELECT
    v.placa,
    MIN(CASE WHEN r.resultado_liquido_acumulado >= 0 THEN r.mes_referencia END) AS mes_payback,
    ROUND(MAX(r.resultado_liquido_acumulado), 2) AS acumulado_no_ultimo_mes
FROM gold_resultado_mensal r
JOIN gold_dim_veiculo v ON v.veiculo_id = r.veiculo_id
GROUP BY v.veiculo_id;


-- 4) Composicao dos custos operacionais por categoria (% do total, todos os veiculos)
SELECT
    categoria,
    ROUND(SUM(valor), 2) AS total_periodo,
    ROUND(100.0 * SUM(valor) / (SELECT SUM(valor) FROM gold_custo_categoria_mensal), 1) AS pct_do_total
FROM gold_custo_categoria_mensal
GROUP BY categoria
ORDER BY total_periodo DESC;


-- 5) Meses em que o veiculo operou sem folga segura pra sustentar mais divida (DSCR < 1,3)
SELECT
    v.placa,
    COUNT(*) AS meses_abaixo_de_1_3,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM gold_resultado_mensal WHERE veiculo_id = v.veiculo_id), 1) AS pct_dos_meses
FROM gold_resultado_mensal r
JOIN gold_dim_veiculo v ON v.veiculo_id = r.veiculo_id
WHERE r.dscr < 1.3
GROUP BY v.veiculo_id
ORDER BY pct_dos_meses DESC;
