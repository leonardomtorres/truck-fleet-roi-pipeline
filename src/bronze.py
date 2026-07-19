"""Bronze: copia os CSVs de data/raw/ pra bronze.db sem alterar nada."""

import sqlite3
from pathlib import Path

import pandas as pd

RAW_DIR = Path("data/raw")
DB_PATH = Path("bronze.db")
SCHEMA_PATH = Path("sql/bronze_schema.sql")


def main():
    veiculos = pd.read_csv(RAW_DIR / "veiculos.csv")
    financiamentos = pd.read_csv(RAW_DIR / "financiamentos.csv")
    operacoes = pd.read_csv(RAW_DIR / "operacoes_mensais.csv")
    custos = pd.read_csv(RAW_DIR / "custos_mensais.csv")

    if DB_PATH.exists():
        DB_PATH.unlink()

    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
        veiculos.to_sql("bronze_veiculos", conn, if_exists="append", index=False)
        financiamentos.to_sql("bronze_financiamentos", conn, if_exists="append", index=False)
        operacoes.to_sql("bronze_operacoes_mensais", conn, if_exists="append", index=False)
        custos.to_sql("bronze_custos_mensais", conn, if_exists="append", index=False)
        conn.commit()
    finally:
        conn.close()

    print(f"bronze.db gerado em {DB_PATH.resolve()}")
    print(f"  bronze_veiculos          -> {len(veiculos)} linhas")
    print(f"  bronze_financiamentos    -> {len(financiamentos)} linhas")
    print(f"  bronze_operacoes_mensais -> {len(operacoes)} linhas")
    print(f"  bronze_custos_mensais    -> {len(custos)} linhas")


if __name__ == "__main__":
    main()
