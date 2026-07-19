-- Bronze: copia fiel dos CSVs de origem, so com tipagem basica.

DROP TABLE IF EXISTS bronze_veiculos;
DROP TABLE IF EXISTS bronze_financiamentos;
DROP TABLE IF EXISTS bronze_operacoes_mensais;
DROP TABLE IF EXISTS bronze_custos_mensais;

CREATE TABLE bronze_veiculos (
    veiculo_id      INTEGER,
    placa           TEXT,
    modelo          TEXT,
    ano_fabricacao  INTEGER,
    data_aquisicao  TEXT,
    valor_veiculo   REAL
);

CREATE TABLE bronze_financiamentos (
    veiculo_id          INTEGER,
    valor_veiculo       REAL,
    valor_entrada       REAL,
    valor_financiado    REAL,
    prazo_meses         INTEGER,
    taxa_juros_anual    REAL,
    data_inicio         TEXT
);

CREATE TABLE bronze_operacoes_mensais (
    veiculo_id              INTEGER,
    mes_referencia          TEXT,
    km_rodado               INTEGER,
    num_entregas             INTEGER,
    receita_frete_dia_30    REAL,
    receita_frete_dia_9     REAL,
    receita_frete_dia_15    REAL
);

CREATE TABLE bronze_custos_mensais (
    veiculo_id      INTEGER,
    mes_referencia  TEXT,
    categoria       TEXT,
    valor           REAL
);
