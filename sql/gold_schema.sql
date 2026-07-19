-- Gold: pronto pro consumo -- resultado liquido, payback, custo por km.
-- Notebook e dashboard leem so daqui.

DROP TABLE IF EXISTS gold_resultado_mensal;
DROP TABLE IF EXISTS gold_custo_categoria_mensal;
DROP TABLE IF EXISTS gold_dim_veiculo;

CREATE TABLE gold_dim_veiculo (
    veiculo_id          INTEGER PRIMARY KEY,
    placa               TEXT NOT NULL,
    modelo              TEXT NOT NULL,
    valor_veiculo       REAL NOT NULL,
    valor_entrada        REAL NOT NULL,
    valor_financiado     REAL NOT NULL,
    taxa_juros_anual     REAL NOT NULL,
    prazo_meses          INTEGER NOT NULL
);

CREATE TABLE gold_resultado_mensal (
    veiculo_id                      INTEGER NOT NULL REFERENCES gold_dim_veiculo(veiculo_id),
    mes_referencia                  TEXT NOT NULL,
    km_rodado                       INTEGER NOT NULL,
    num_entregas                    INTEGER NOT NULL,
    receita_total                   REAL NOT NULL,
    custo_operacional_total         REAL NOT NULL,
    custo_por_km                    REAL NOT NULL,
    resultado_operacional           REAL NOT NULL,
    parcela_financiamento           REAL NOT NULL,
    dscr                             REAL NOT NULL,
    resultado_liquido               REAL NOT NULL,
    resultado_liquido_acumulado     REAL NOT NULL,
    PRIMARY KEY (veiculo_id, mes_referencia)
);

CREATE TABLE gold_custo_categoria_mensal (
    veiculo_id      INTEGER NOT NULL REFERENCES gold_dim_veiculo(veiculo_id),
    mes_referencia  TEXT NOT NULL,
    categoria       TEXT NOT NULL,
    valor           REAL NOT NULL,
    PRIMARY KEY (veiculo_id, mes_referencia, categoria)
);
