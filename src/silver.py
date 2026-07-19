"""Silver: le bronze.db, limpa/valida e grava em silver.db. Ainda sem metrica de negocio -- so dado confiavel."""

import sqlite3
from pathlib import Path

import pandas as pd

DB_IN = Path("bronze.db")
DB_OUT = Path("silver.db")
SCHEMA_PATH = Path("sql/silver_schema.sql")

CATEGORIAS_VALIDAS = {
    "combustivel", "pneu", "seguro", "manutencao", "motorista",
    "ajudante", "pedagio", "rastreamento_gps", "impostos_taxas", "administrativo",
}


def limpar_veiculo(conn_in) -> pd.DataFrame:
    df = pd.read_sql("SELECT * FROM bronze_veiculos", conn_in)
    df = df.drop_duplicates(subset="veiculo_id", keep="first")
    return df[df.valor_veiculo > 0]


def limpar_financiamento(conn_in) -> pd.DataFrame:
    df = pd.read_sql("SELECT * FROM bronze_financiamentos", conn_in)
    df = df.drop_duplicates(subset="veiculo_id", keep="first")
    df = df[(df.valor_entrada > 0) & (df.valor_financiado > 0) & (df.prazo_meses > 0)]
    df = df[(df.taxa_juros_anual > 0) & (df.taxa_juros_anual < 1)]
    return df.drop(columns=["valor_veiculo"])


def limpar_operacao_mensal(conn_in) -> pd.DataFrame:
    df = pd.read_sql("SELECT * FROM bronze_operacoes_mensais", conn_in)
    df = df.drop_duplicates(subset=["veiculo_id", "mes_referencia"], keep="first")
    df["receita_total"] = (
        df["receita_frete_dia_30"] + df["receita_frete_dia_9"] + df["receita_frete_dia_15"]
    )
    df = df[(df.km_rodado >= 0) & (df.num_entregas >= 0) & (df.receita_total >= 0)]
    return df[["veiculo_id", "mes_referencia", "km_rodado", "num_entregas", "receita_total"]]


def limpar_custo_mensal(conn_in) -> pd.DataFrame:
    df = pd.read_sql("SELECT * FROM bronze_custos_mensais", conn_in)

    invalidas = sorted(set(df.categoria.unique()) - CATEGORIAS_VALIDAS)
    if invalidas:
        print(f"  aviso: descartando categorias fora da taxonomia: {invalidas}")
        df = df[df.categoria.isin(CATEGORIAS_VALIDAS)]

    df = df[df.valor >= 0]
    # soma qualquer duplicata em vez de descartar, para nao perder valor real
    return df.groupby(["veiculo_id", "mes_referencia", "categoria"], as_index=False)["valor"].sum()


def calcular_amortizacao(financiamento: pd.DataFrame, operacao_mensal: pd.DataFrame) -> pd.DataFrame:
    """Amortizacao Price, limitada aos meses com dado operacional de cada veiculo."""
    rows = []
    for _, fin in financiamento.iterrows():
        veiculo_id = fin["veiculo_id"]
        pv = fin["valor_financiado"]
        i_mensal = (1 + fin["taxa_juros_anual"]) ** (1 / 12) - 1
        n = fin["prazo_meses"]
        parcela = pv * i_mensal / (1 - (1 + i_mensal) ** -n)

        meses = sorted(operacao_mensal.loc[operacao_mensal.veiculo_id == veiculo_id, "mes_referencia"].unique())

        saldo = pv
        for num_parcela, mes in enumerate(meses, start=1):
            juros = saldo * i_mensal
            amortizacao = parcela - juros
            saldo -= amortizacao
            rows.append({
                "veiculo_id": veiculo_id,
                "num_parcela": num_parcela,
                "mes_referencia": mes,
                "parcela": round(parcela, 2),
                "juros": round(juros, 2),
                "amortizacao": round(amortizacao, 2),
                "saldo_devedor": round(max(saldo, 0), 2),
            })
    return pd.DataFrame(rows)


def main():
    conn_in = sqlite3.connect(DB_IN)
    try:
        veiculo = limpar_veiculo(conn_in)
        financiamento = limpar_financiamento(conn_in)
        operacao_mensal = limpar_operacao_mensal(conn_in)
        custo_mensal = limpar_custo_mensal(conn_in)
    finally:
        conn_in.close()

    amortizacao_mensal = calcular_amortizacao(financiamento, operacao_mensal)

    if DB_OUT.exists():
        DB_OUT.unlink()

    conn_out = sqlite3.connect(DB_OUT)
    try:
        conn_out.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        veiculo.to_sql("silver_veiculo", conn_out, if_exists="append", index=False)
        financiamento.to_sql("silver_financiamento", conn_out, if_exists="append", index=False)
        operacao_mensal.to_sql("silver_operacao_mensal", conn_out, if_exists="append", index=False)
        custo_mensal.to_sql("silver_custo_mensal", conn_out, if_exists="append", index=False)
        amortizacao_mensal.to_sql("silver_amortizacao_mensal", conn_out, if_exists="append", index=False)
        conn_out.commit()
    finally:
        conn_out.close()

    print(f"silver.db gerado em {DB_OUT.resolve()}")
    print(f"  silver_veiculo             -> {len(veiculo)} linhas")
    print(f"  silver_financiamento       -> {len(financiamento)} linhas")
    print(f"  silver_operacao_mensal     -> {len(operacao_mensal)} linhas")
    print(f"  silver_custo_mensal        -> {len(custo_mensal)} linhas")
    print(f"  silver_amortizacao_mensal  -> {len(amortizacao_mensal)} linhas")


if __name__ == "__main__":
    main()
