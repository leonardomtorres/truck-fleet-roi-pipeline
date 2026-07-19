"""Gold: le silver.db, calcula resultado liquido/custo por km/payback e grava em gold.db. Notebook e dashboard leem so daqui."""

import sqlite3
from pathlib import Path

import pandas as pd

DB_IN = Path("silver.db")
DB_OUT = Path("gold.db")
SCHEMA_PATH = Path("sql/gold_schema.sql")


def montar_dim_veiculo(conn_in) -> pd.DataFrame:
    veiculo = pd.read_sql("SELECT * FROM silver_veiculo", conn_in)
    financiamento = pd.read_sql("SELECT * FROM silver_financiamento", conn_in)
    dim = veiculo.merge(financiamento, on="veiculo_id")
    return dim[[
        "veiculo_id", "placa", "modelo", "valor_veiculo",
        "valor_entrada", "valor_financiado", "taxa_juros_anual", "prazo_meses",
    ]]


def montar_resultado_mensal(conn_in, dim_veiculo: pd.DataFrame) -> pd.DataFrame:
    operacao = pd.read_sql("SELECT * FROM silver_operacao_mensal", conn_in)
    custo = pd.read_sql("SELECT * FROM silver_custo_mensal", conn_in)
    amortizacao = pd.read_sql("SELECT * FROM silver_amortizacao_mensal", conn_in)

    custo_total = (
        custo.groupby(["veiculo_id", "mes_referencia"])["valor"]
        .sum()
        .reset_index()
        .rename(columns={"valor": "custo_operacional_total"})
    )

    df = operacao.merge(custo_total, on=["veiculo_id", "mes_referencia"])
    df = df.merge(
        amortizacao[["veiculo_id", "mes_referencia", "parcela"]], on=["veiculo_id", "mes_referencia"]
    ).rename(columns={"parcela": "parcela_financiamento"})

    df["custo_por_km"] = round(df["custo_operacional_total"] / df["km_rodado"], 2)
    df["resultado_operacional"] = df["receita_total"] - df["custo_operacional_total"]
    # DSCR (debt service coverage ratio): quanto o resultado operacional cobre a parcela.
    # >= 1,3 e o patamar que costuma ser aceito como folga segura pra sustentar mais divida.
    df["dscr"] = round(df["resultado_operacional"] / df["parcela_financiamento"], 2)
    df["resultado_liquido"] = df["resultado_operacional"] - df["parcela_financiamento"]
    df = df.sort_values(["veiculo_id", "mes_referencia"])

    entrada_por_veiculo = dim_veiculo.set_index("veiculo_id")["valor_entrada"]
    grupos = []
    for veiculo_id, grupo in df.groupby("veiculo_id"):
        grupo = grupo.copy()
        acumulado = -entrada_por_veiculo.loc[veiculo_id]
        acumulados = []
        for resultado in grupo["resultado_liquido"]:
            acumulado += resultado
            acumulados.append(round(acumulado, 2))
        grupo["resultado_liquido_acumulado"] = acumulados
        grupos.append(grupo)

    return pd.concat(grupos).reset_index(drop=True)


def main():
    conn_in = sqlite3.connect(DB_IN)
    try:
        dim_veiculo = montar_dim_veiculo(conn_in)
        resultado_mensal = montar_resultado_mensal(conn_in, dim_veiculo)
        custo_categoria_mensal = pd.read_sql("SELECT * FROM silver_custo_mensal", conn_in)
    finally:
        conn_in.close()

    if DB_OUT.exists():
        DB_OUT.unlink()

    conn_out = sqlite3.connect(DB_OUT)
    try:
        conn_out.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        dim_veiculo.to_sql("gold_dim_veiculo", conn_out, if_exists="append", index=False)
        resultado_mensal.to_sql("gold_resultado_mensal", conn_out, if_exists="append", index=False)
        custo_categoria_mensal.to_sql("gold_custo_categoria_mensal", conn_out, if_exists="append", index=False)
        conn_out.commit()
    finally:
        conn_out.close()

    print(f"gold.db gerado em {DB_OUT.resolve()}")
    print(f"  gold_dim_veiculo            -> {len(dim_veiculo)} linhas")
    print(f"  gold_resultado_mensal       -> {len(resultado_mensal)} linhas")
    print(f"  gold_custo_categoria_mensal -> {len(custo_categoria_mensal)} linhas")


if __name__ == "__main__":
    main()
