"""
Gera dados sinteticos de operacao de uma frota de caminhoes em data/raw/.
Categorias de custo e o formato de recebimento do frete seguem um padrao
real de controle de fluxo de caixa por veiculo; os valores em si sao
aleatorios.
"""

import numpy as np
import pandas as pd

RNG = np.random.default_rng(seed=42)

N_MESES = 24
MES_INICIAL = pd.Period("2024-01", freq="M")
MESES = [MES_INICIAL + i for i in range(N_MESES)]

VEICULOS = [
    {"veiculo_id": 1, "placa": "FIC-1A23", "modelo": "Caminhao 0km c/ implemento", "ano_fabricacao": 2024, "data_aquisicao": "2024-01-05", "valor_veiculo": 465000.0, "fator_desempenho": 1.05},
    {"veiculo_id": 2, "placa": "FIC-2B45", "modelo": "Caminhao 0km c/ implemento", "ano_fabricacao": 2024, "data_aquisicao": "2024-01-05", "valor_veiculo": 480000.0, "fator_desempenho": 0.95},
    {"veiculo_id": 3, "placa": "FIC-3C67", "modelo": "Caminhao 0km c/ implemento", "ano_fabricacao": 2024, "data_aquisicao": "2024-01-05", "valor_veiculo": 470000.0, "fator_desempenho": 1.00},
]

TAXA_JUROS_ANUAL = 0.1336
PRAZO_MESES = 60
ENTRADA_PCT = 0.20  # entrada tipica de financiamento de veiculo pesado

CATEGORIAS_CUSTO = [
    "combustivel", "pneu", "seguro", "manutencao", "motorista",
    "ajudante", "pedagio", "rastreamento_gps", "impostos_taxas", "administrativo",
]


def sazonalidade(mes: pd.Period) -> float:
    """Dezembro mais forte, fevereiro mais fraco -- padrao tipico de frete."""
    m = mes.month
    if m == 12:
        return 1.12
    if m == 2:
        return 0.90
    return 1.0


def gerar_veiculos() -> pd.DataFrame:
    return pd.DataFrame(VEICULOS)[["veiculo_id", "placa", "modelo", "ano_fabricacao", "data_aquisicao", "valor_veiculo"]]


def gerar_financiamentos() -> pd.DataFrame:
    rows = []
    for v in VEICULOS:
        valor_financiado = round(v["valor_veiculo"] * (1 - ENTRADA_PCT), 2)
        rows.append({
            "veiculo_id": v["veiculo_id"],
            "valor_veiculo": v["valor_veiculo"],
            "valor_entrada": round(v["valor_veiculo"] * ENTRADA_PCT, 2),
            "valor_financiado": valor_financiado,
            "prazo_meses": PRAZO_MESES,
            "taxa_juros_anual": TAXA_JUROS_ANUAL,
            "data_inicio": v["data_aquisicao"],
        })
    return pd.DataFrame(rows)


def gerar_operacoes_mensais() -> pd.DataFrame:
    rows = []
    for v in VEICULOS:
        fator = v["fator_desempenho"]
        for mes in MESES:
            saz = sazonalidade(mes)
            km_rodado = round(RNG.normal(4800, 400) * fator * saz)
            num_entregas = int(RNG.normal(55, 6) * fator * saz)

            # frete recebido em 3 parcelas ao longo do mes
            base_frete = RNG.normal(9500, 800) * fator * saz
            parcela_dia_30 = round(max(base_frete * RNG.uniform(0.9, 1.1), 0), 2)
            parcela_dia_9 = round(max(base_frete * RNG.uniform(0.9, 1.1), 0), 2)
            parcela_dia_15 = round(max(base_frete * RNG.uniform(0.9, 1.1), 0), 2)

            rows.append({
                "veiculo_id": v["veiculo_id"],
                "mes_referencia": str(mes),
                "km_rodado": max(km_rodado, 0),
                "num_entregas": max(num_entregas, 0),
                "receita_frete_dia_30": parcela_dia_30,
                "receita_frete_dia_9": parcela_dia_9,
                "receita_frete_dia_15": parcela_dia_15,
            })
    return pd.DataFrame(rows)


def gerar_custos_mensais(operacoes: pd.DataFrame) -> pd.DataFrame:
    rows = []
    op_by_key = operacoes.set_index(["veiculo_id", "mes_referencia"])

    for v in VEICULOS:
        for mes in MESES:
            km = op_by_key.loc[(v["veiculo_id"], str(mes)), "km_rodado"]

            combustivel = km * RNG.uniform(1.15, 1.35)
            pneu = RNG.normal(580, 90) if RNG.random() < 0.85 else RNG.normal(580, 90) + RNG.uniform(800, 1800)
            seguro = RNG.normal(920, 15)
            manutencao = RNG.normal(250, 80) if RNG.random() > 0.15 else RNG.normal(2200, 500)
            motorista = 3600 + (RNG.uniform(2200, 3200) if mes.month in (11, 12) else 0)
            ajudante = 2700 + (RNG.uniform(1600, 2400) if mes.month in (11, 12) else 0)
            pedagio = km * RNG.uniform(0.15, 0.24)
            rastreamento_gps = RNG.normal(550, 60)
            impostos_taxas = RNG.normal(2500, 300)
            administrativo = RNG.normal(650, 200) + (RNG.uniform(300, 900) if RNG.random() < 0.2 else 0)

            valores = {
                "combustivel": combustivel, "pneu": pneu, "seguro": seguro,
                "manutencao": manutencao, "motorista": motorista, "ajudante": ajudante,
                "pedagio": pedagio, "rastreamento_gps": rastreamento_gps,
                "impostos_taxas": impostos_taxas, "administrativo": administrativo,
            }
            for categoria, valor in valores.items():
                rows.append({
                    "veiculo_id": v["veiculo_id"],
                    "mes_referencia": str(mes),
                    "categoria": categoria,
                    "valor": round(max(valor, 0), 2),
                })
    return pd.DataFrame(rows)


def main():
    veiculos = gerar_veiculos()
    financiamentos = gerar_financiamentos()
    operacoes = gerar_operacoes_mensais()
    custos = gerar_custos_mensais(operacoes)

    veiculos.to_csv("data/raw/veiculos.csv", index=False)
    financiamentos.to_csv("data/raw/financiamentos.csv", index=False)
    operacoes.to_csv("data/raw/operacoes_mensais.csv", index=False)
    custos.to_csv("data/raw/custos_mensais.csv", index=False)

    print("Gerado com sucesso:")
    print(f"  veiculos.csv          -> {len(veiculos)} linhas")
    print(f"  financiamentos.csv    -> {len(financiamentos)} linhas")
    print(f"  operacoes_mensais.csv -> {len(operacoes)} linhas")
    print(f"  custos_mensais.csv    -> {len(custos)} linhas")


if __name__ == "__main__":
    main()
