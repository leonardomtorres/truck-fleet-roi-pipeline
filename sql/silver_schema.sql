-- Silver: dado limpo e validado, sem duplicata. A amortizacao entra aqui
-- por ser um calculo tecnico (Price), nao ainda uma metrica de negocio.

DROP TABLE IF EXISTS silver_veiculo;
DROP TABLE IF EXISTS silver_financiamento;
DROP TABLE IF EXISTS silver_operacao_mensal;
DROP TABLE IF EXISTS silver_custo_mensal;
DROP TABLE IF EXISTS silver_amortizacao_mensal;

CREATE TABLE silver_veiculo (
    veiculo_id      INTEGER PRIMARY KEY,
    placa           TEXT NOT NULL,
    modelo          TEXT NOT NULL,
    ano_fabricacao  INTEGER NOT NULL,
    data_aquisicao  TEXT NOT NULL,
    valor_veiculo   REAL NOT NULL CHECK (valor_veiculo > 0)
);

CREATE TABLE silver_financiamento (
    veiculo_id          INTEGER PRIMARY KEY REFERENCES silver_veiculo(veiculo_id),
    valor_entrada       REAL NOT NULL CHECK (valor_entrada > 0),
    valor_financiado    REAL NOT NULL CHECK (valor_financiado > 0),
    prazo_meses         INTEGER NOT NULL CHECK (prazo_meses > 0),
    taxa_juros_anual    REAL NOT NULL CHECK (taxa_juros_anual > 0 AND taxa_juros_anual < 1),
    data_inicio         TEXT NOT NULL
);

CREATE TABLE silver_operacao_mensal (
    veiculo_id      INTEGER NOT NULL REFERENCES silver_veiculo(veiculo_id),
    mes_referencia  TEXT NOT NULL,
    km_rodado       INTEGER NOT NULL CHECK (km_rodado >= 0),
    num_entregas    INTEGER NOT NULL CHECK (num_entregas >= 0),
    receita_total   REAL NOT NULL CHECK (receita_total >= 0),
    PRIMARY KEY (veiculo_id, mes_referencia)
);

CREATE TABLE silver_custo_mensal (
    veiculo_id      INTEGER NOT NULL REFERENCES silver_veiculo(veiculo_id),
    mes_referencia  TEXT NOT NULL,
    categoria       TEXT NOT NULL,
    valor           REAL NOT NULL CHECK (valor >= 0),
    PRIMARY KEY (veiculo_id, mes_referencia, categoria)
);

CREATE TABLE silver_amortizacao_mensal (
    veiculo_id      INTEGER NOT NULL REFERENCES silver_veiculo(veiculo_id),
    num_parcela     INTEGER NOT NULL,
    mes_referencia  TEXT NOT NULL,
    parcela         REAL NOT NULL,
    juros           REAL NOT NULL,
    amortizacao     REAL NOT NULL,
    saldo_devedor   REAL NOT NULL,
    PRIMARY KEY (veiculo_id, num_parcela)
);
