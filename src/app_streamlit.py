"""
Dashboard Streamlit -- le exclusivamente de gold.db (a camada final do
pipeline). Roda com: streamlit run src/app_streamlit.py
"""

import sqlite3
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import streamlit as st

DB_PATH = Path(__file__).resolve().parent.parent / "gold.db"


@st.cache_data
def carregar_dados():
    conn = sqlite3.connect(DB_PATH)
    veiculos = pd.read_sql("SELECT * FROM gold_dim_veiculo", conn)
    resultado_mensal = pd.read_sql("SELECT * FROM gold_resultado_mensal", conn)
    custo_categoria = pd.read_sql("SELECT * FROM gold_custo_categoria_mensal", conn)
    conn.close()
    return veiculos, resultado_mensal, custo_categoria


def parcela_price(valor_financiado, taxa_anual, prazo_meses):
    i = (1 + taxa_anual) ** (1 / 12) - 1
    return valor_financiado * i / (1 - (1 + i) ** -prazo_meses)


def classificar_dscr(dscr):
    """DSCR = resultado operacional / parcela. Abaixo de 1,0 nem cobre a
    parcela; 1,0-1,3 cobre sem folga; acima de 1,3 e o patamar considerado
    seguro pra sustentar mais divida."""
    if dscr < 1.0:
        return "insustentável (não cobre a parcela)"
    if dscr < 1.3:
        return "cobre a parcela, sem folga"
    return "folga saudável pra mais dívida"


def simular_crescimento_frota(
    frota_inicial, resultado_operacional, valor_veiculo, entrada_pct,
    prazo_financiamento_meses, taxa_juros_anual, vida_util_meses, horizonte_meses,
    reserva_meses_parcela=0,
):
    """Simula mes a mes: cada caminhao rende resultado_operacional menos sua
    propria parcela enquanto financiado, e o valor cheio depois de quitado.
    A sobra vai pra um caixa que compra caminhao novo assim que junta a
    entrada MAIS a reserva de seguranca (reserva_meses_parcela x parcela),
    que fica guardada, nao gasta. Caminhao se aposenta ao atingir a vida util."""
    valor_entrada = valor_veiculo * entrada_pct / 100
    valor_financiado = valor_veiculo - valor_entrada
    parcela = parcela_price(valor_financiado, taxa_juros_anual / 100, prazo_financiamento_meses)
    reserva_minima = parcela * reserva_meses_parcela

    caminhoes = [0] * frota_inicial  # mes de compra de cada caminhao ativo
    caixa = 0.0
    historico = []

    for mes in range(1, horizonte_meses + 1):
        caminhoes = [c for c in caminhoes if (mes - c) <= vida_util_meses]
        contribuicao = 0.0
        for compra in caminhoes:
            idade = mes - compra
            contribuicao += resultado_operacional - parcela if idade <= prazo_financiamento_meses else resultado_operacional
        caixa += contribuicao

        if caixa >= valor_entrada + reserva_minima:
            caixa -= valor_entrada
            caminhoes.append(mes)

        historico.append({"mes": mes, "n_caminhoes": len(caminhoes), "caixa": round(caixa, 2)})

    return pd.DataFrame(historico), reserva_minima


st.set_page_config(page_title="Fleet Financing ROI", layout="wide")
st.title("Fleet Financing ROI")
st.caption("Resultado operacional x resultado líquido de uma frota financiada, e sensibilidade à taxa de juros.")

if not DB_PATH.exists():
    st.error(f"gold.db não encontrado em {DB_PATH}. Rode `python src/run_pipeline.py` primeiro.")
    st.stop()

veiculos, resultado_mensal, custo_categoria = carregar_dados()

st.sidebar.header("Filtros")
placas_selecionadas = st.sidebar.multiselect(
    "Caminhões", options=veiculos["placa"].tolist(), default=veiculos["placa"].tolist()
)

meses_disponiveis = sorted(resultado_mensal["mes_referencia"].unique())
st.sidebar.caption("Período")
col_de, col_ate = st.sidebar.columns(2)
mes_inicio = col_de.selectbox("De", options=meses_disponiveis, index=0)
mes_fim = col_ate.selectbox("Até", options=meses_disponiveis, index=len(meses_disponiveis) - 1)
if mes_inicio > mes_fim:
    mes_inicio, mes_fim = mes_fim, mes_inicio

veiculos_sel = veiculos[veiculos.placa.isin(placas_selecionadas)]
ids_sel = veiculos_sel.veiculo_id.tolist()

resultado_periodo = resultado_mensal[
    (resultado_mensal.mes_referencia >= mes_inicio) & (resultado_mensal.mes_referencia <= mes_fim)
]
resultado_sel = resultado_periodo[resultado_periodo.veiculo_id.isin(ids_sel)].merge(veiculos_sel, on="veiculo_id")
operacional_medio = resultado_periodo.groupby("veiculo_id")["resultado_operacional"].mean()

tab_visao, tab_simulador, tab_crescimento, tab_custos = st.tabs(
    ["Visão geral", "Simulador de investimento", "Crescimento de frota", "Custos"]
)

# ------------------------------------------------------------------ Visão geral
with tab_visao:
    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Receita média/mês", f"R$ {resultado_sel.receita_total.mean():,.0f}")
    col2.metric("Custo operacional médio/mês", f"R$ {resultado_sel.custo_operacional_total.mean():,.0f}")
    col3.metric("Resultado operacional médio", f"R$ {resultado_sel.resultado_operacional.mean():,.0f}")
    col4.metric("Resultado líquido médio (após parcela)", f"R$ {resultado_sel.resultado_liquido.mean():,.0f}")
    dscr_geral = resultado_sel.dscr.mean()
    col5.metric("DSCR médio", f"{dscr_geral:.2f}", help="Resultado operacional / parcela. >= 1,3 é considerado folga segura pra sustentar mais dívida.")
    st.caption(f"DSCR médio: {classificar_dscr(dscr_geral)}.")

    st.subheader("Payback acumulado (taxa contratada real, 13,36% a.a.)")
    fig, ax = plt.subplots(figsize=(10, 4))
    for placa, grupo in resultado_sel.groupby("placa"):
        grupo = grupo.sort_values("mes_referencia")
        ax.plot(grupo.mes_referencia, grupo.resultado_liquido_acumulado, marker="o", markersize=3, label=placa)
    ax.axhline(0, color="black", linewidth=0.8)
    ax.set_ylabel("Resultado líquido acumulado (R$)")
    ax.tick_params(axis="x", rotation=90)
    ax.legend()
    st.pyplot(fig)

# ------------------------------------------------------------ Simulador de investimento
with tab_simulador:
    st.subheader("Quanto tempo até o investimento voltar?")
    st.caption("Ajuste os valores e o payback estimado recalcula na hora, usando o desempenho operacional médio (no período selecionado) do caminhão escolhido como base.")

    placa_base = st.selectbox("Caminhão base (desempenho operacional)", options=veiculos["placa"].tolist())
    v_base = veiculos.loc[veiculos.placa == placa_base].iloc[0]

    # key inclui a placa: troca de caminhão base cria widgets "novos", com o
    # value= voltando a valer como default (senão o Streamlit mantém o valor
    # anterior do campo mesmo depois de trocar o caminhão selecionado)
    c1, c2, c3, c4 = st.columns(4)
    valor_veiculo = c1.number_input(
        "Valor do veículo (R$)", min_value=100_000, max_value=800_000,
        value=int(v_base.valor_veiculo), step=5_000, key=f"valor_{placa_base}",
    )
    entrada_pct = c2.slider(
        "Entrada (%)", min_value=5, max_value=50,
        value=int(round(100 * v_base.valor_entrada / v_base.valor_veiculo)), key=f"entrada_{placa_base}",
    )
    prazo_meses = c3.slider(
        "Prazo (meses)", min_value=12, max_value=72,
        value=int(v_base.prazo_meses), step=6, key=f"prazo_{placa_base}",
    )
    taxa_juros = c4.slider("Taxa de juros anual (%)", min_value=6.0, max_value=24.0, value=13.36, step=0.1)

    valor_entrada = valor_veiculo * entrada_pct / 100
    valor_financiado = valor_veiculo - valor_entrada
    parcela_sim = parcela_price(valor_financiado, taxa_juros / 100, prazo_meses)
    resultado_liquido_sim = operacional_medio[v_base.veiculo_id] - parcela_sim

    dscr_sim = operacional_medio[v_base.veiculo_id] / parcela_sim

    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Parcela mensal", f"R$ {parcela_sim:,.0f}")
    m2.metric("Resultado líquido estimado/mês", f"R$ {resultado_liquido_sim:,.0f}")
    m4.metric("DSCR", f"{dscr_sim:.2f}", help="Resultado operacional / parcela. >= 1,3 é considerado folga segura pra sustentar mais dívida.")
    st.caption(f"DSCR de {dscr_sim:.2f}: {classificar_dscr(dscr_sim)}.")

    if resultado_liquido_sim > 0:
        payback_meses = valor_entrada / resultado_liquido_sim
        if payback_meses <= prazo_meses:
            m3.metric("Payback estimado", f"{payback_meses:.1f} meses ({payback_meses / 12:.1f} anos)")
            st.progress(min(payback_meses / prazo_meses, 1.0), text=f"{payback_meses:.0f} de {prazo_meses} meses do financiamento até se pagar")
        else:
            m3.metric("Payback estimado", f"além do prazo ({prazo_meses}m)")
            st.warning("Nesse cenário, o caminhão não recupera a entrada dentro do prazo do financiamento.")
    else:
        m3.metric("Payback estimado", "nunca")
        st.error("Nesse cenário, a parcela é maior que o resultado operacional médio: o caminhão dá prejuízo líquido todo mês.")

    st.subheader("Sensibilidade: payback vs. taxa de juros")
    taxas = np.arange(0.06, 0.241, 0.005)
    paybacks = []
    for taxa in taxas:
        parcela = parcela_price(valor_financiado, taxa, prazo_meses)
        resultado = operacional_medio[v_base.veiculo_id] - parcela
        if resultado > 0:
            paybacks.append(min(valor_entrada / resultado, prazo_meses))
        else:
            paybacks.append(np.nan)

    fig2, ax2 = plt.subplots(figsize=(10, 4))
    ax2.plot(taxas * 100, paybacks, marker="o", markersize=3)
    ax2.axvline(taxa_juros, color="gray", linestyle="--", linewidth=1, label=f"Taxa escolhida ({taxa_juros:.2f}%)")
    ax2.set_xlabel("Taxa de juros anual (%)")
    ax2.set_ylabel("Meses até o payback")
    ax2.legend()
    st.pyplot(fig2)

# --------------------------------------------------------- Crescimento de frota
with tab_crescimento:
    st.subheader("Reinvestindo a sobra mensal, quantos caminhões eu teria?")
    st.caption("Cada caminhão rende o resultado operacional informado menos sua própria parcela enquanto está financiado, e o valor cheio depois de quitado. A sobra acumula num caixa que compra caminhão novo assim que junta a entrada, e cada caminhão se aposenta ao fim da vida útil.")
    st.caption(f"Resultado operacional default calculado sobre o período {mes_inicio} a {mes_fim}. Ajuste em Filtros, na barra lateral.")

    g1, g2, g3 = st.columns(3)
    frota_inicial = g1.number_input("Frota inicial", min_value=1, max_value=20, value=len(veiculos))
    resultado_op_input = g1.number_input(
        "Resultado operacional/caminhão (R$/mês)", min_value=1_000, max_value=30_000,
        value=int(resultado_periodo.resultado_operacional.mean()), step=500,
        help="Frete menos custo do dia a dia (combustível, pneu, seguro, motorista, ajudante, manutenção, pedágio, impostos) -- ainda SEM descontar a parcela do financiamento. A parcela é calculada e descontada por dentro da simulação, a partir dos campos ao lado. Valor padrão = média do período selecionado na barra lateral.",
    )
    valor_veiculo_g = g2.number_input(
        "Valor do veículo (R$)", min_value=100_000, max_value=800_000,
        value=int(veiculos.valor_veiculo.mean()), step=5_000, key="valor_g",
    )
    entrada_pct_g = g2.slider("Entrada (%)", min_value=5, max_value=50, value=20, key="entrada_g")
    prazo_g = g3.slider("Prazo do financiamento (meses)", min_value=12, max_value=72, value=60, step=6, key="prazo_g")
    taxa_g = g3.slider("Taxa de juros anual (%)", min_value=6.0, max_value=24.0, value=13.36, step=0.1, key="taxa_g")

    h1, h2, h3 = st.columns(3)
    vida_util_anos = h1.slider("Vida útil por caminhão (anos)", min_value=4, max_value=15, value=8)
    horizonte_anos = h2.slider("Horizonte da simulação (anos)", min_value=1, max_value=20, value=10)
    reserva_meses = h3.slider(
        "Reserva de segurança (meses de parcela)", min_value=0, max_value=6, value=2,
        help="Antes de comprar o próximo caminhão, guarda esse tanto de parcela em caixa pra imprevisto (quebra, mês fraco). 0 = reinveste tudo, sem reserva.",
    )

    historico, reserva_minima = simular_crescimento_frota(
        frota_inicial=frota_inicial,
        resultado_operacional=resultado_op_input,
        valor_veiculo=valor_veiculo_g,
        entrada_pct=entrada_pct_g,
        prazo_financiamento_meses=prazo_g,
        taxa_juros_anual=taxa_g,
        vida_util_meses=vida_util_anos * 12,
        horizonte_meses=horizonte_anos * 12,
        reserva_meses_parcela=reserva_meses,
    )

    st.divider()
    k1, k2, k3 = st.columns(3)
    k1.metric("Frota inicial", frota_inicial)
    k2.metric(f"Frota em {horizonte_anos} anos", int(historico.n_caminhoes.iloc[-1]))
    k3.metric("Caixa acumulado ao final", f"R$ {historico.caixa.iloc[-1]:,.0f}")

    st.info("Esse modelo assume carga suficiente pra manter todo caminhão novo ocupado desde o mês 1, e 100% da sobra (além da reserva) reinvestida. É um teto financeiro, não uma previsão. Na prática, o que trava o crescimento costuma ser conseguir contrato e mão de obra na mesma velocidade, não o capital.")

    fig3, (axf, axc) = plt.subplots(1, 2, figsize=(12, 4.5))
    axf.plot(historico.mes / 12, historico.n_caminhoes)
    axf.set_xlabel("Anos")
    axf.set_ylabel("Caminhões na frota")
    axf.set_title("Tamanho da frota ao longo do tempo")

    axc.plot(historico.mes / 12, historico.caixa)
    if reserva_minima > 0:
        axc.axhline(reserva_minima, color="orange", linestyle="--", linewidth=1, label=f"Reserva mínima (R$ {reserva_minima:,.0f})")
        axc.legend()
    axc.set_xlabel("Anos")
    axc.set_ylabel("Caixa acumulado (R$)")
    axc.set_title("Caixa disponível pra próxima entrada")
    plt.tight_layout()
    st.pyplot(fig3)

# ------------------------------------------------------------------------ Custos
with tab_custos:
    st.subheader("Composição de custos por categoria")
    st.caption(f"Período: {mes_inicio} a {mes_fim}. Ajuste em Filtros, na barra lateral.")
    visao = st.radio("Ver", ["Total selecionado", "Por caminhão"], horizontal=True)
    custo_periodo = custo_categoria[
        (custo_categoria.mes_referencia >= mes_inicio) & (custo_categoria.mes_referencia <= mes_fim)
    ]
    custo_sel = custo_periodo[custo_periodo.veiculo_id.isin(ids_sel)].merge(veiculos_sel, on="veiculo_id")

    fig4, ax4 = plt.subplots(figsize=(9, 5.5))
    if visao == "Total selecionado":
        resumo = custo_sel.groupby("categoria")["valor"].sum().sort_values(ascending=True)
        resumo.plot(kind="barh", ax=ax4)
        ax4.set_xlabel("R$ no período")
    else:
        pivot = custo_sel.pivot_table(index="categoria", columns="placa", values="valor", aggfunc="sum").fillna(0)
        pivot = pivot.loc[pivot.sum(axis=1).sort_values().index]
        pivot.plot(kind="barh", stacked=True, ax=ax4)
        ax4.set_xlabel("R$ no período")
        ax4.legend(title="Caminhão")
    st.pyplot(fig4)
