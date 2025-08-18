import streamlit as st

# --- Imports da nova estrutura utils ---
from utils.credito_utils import carregar_dados_idex, gerar_grafico_idex, carregar_dados_idex_infra, gerar_grafico_idex_infra

# --- Configuração da Página ---
st.set_page_config(layout="wide", page_title="Crédito Privado")

# --- Conteúdo da Página ---
st.header("IDEX JGP - Indicador de Crédito Privado (Spread/CDI)")
st.info(
    "O IDEX-CDI mostra o spread médio (prêmio acima do CDI) exigido pelo mercado para comprar debêntures. "
    "Spreads maiores indicam maior percepção de risco. Filtramos emissores que passaram por eventos de crédito "
    "relevantes (Americanas, Light, etc.) para uma visão mais limpa da tendência."
)
df_idex = carregar_dados_idex()
if not df_idex.empty:
    fig_idex = gerar_grafico_idex(df_idex)
    st.plotly_chart(fig_idex, use_container_width=True)
else:
    st.warning("Não foi possível carregar os dados do IDEX-CDI para exibição.")

st.markdown("---")

st.header("IDEX INFRA - Debêntures de Infraestrutura (Spread/NTN-B)")
st.info(
    "O IDEX-INFRA mede o spread médio de debêntures incentivadas em relação aos títulos públicos de referência (NTN-Bs). "
    "Ele reflete o prêmio de risco exigido para investir em dívida de projetos de infraestrutura."
)
df_idex_infra = carregar_dados_idex_infra()
if not df_idex_infra.empty:
    fig_idex_infra = gerar_grafico_idex_infra(df_idex_infra)
    st.plotly_chart(fig_idex_infra, use_container_width=True)
else:
    st.warning("Não foi possível carregar os dados do IDEX INFRA para exibição.")
