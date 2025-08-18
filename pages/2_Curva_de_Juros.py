import streamlit as st

# --- Imports da nova estrutura utils ---
from utils.tesouro_utils import obter_dados_tesouro, gerar_grafico_ettj_curto_prazo, gerar_grafico_ettj_longo_prazo

# --- Configuração da Página ---
st.set_page_config(layout="wide", page_title="Curva de Juros")

# --- Conteúdo da Página ---
st.header("Estrutura a Termo da Taxa de Juros (ETTJ)")
st.info("Esta página foca na análise dos títulos públicos prefixados (LTNs e NTN-Fs), que formam a curva de juros nominal da economia.")
st.markdown("---")

df_tesouro = obter_dados_tesouro()

if not df_tesouro.empty:
    st.subheader("Comparativo de Curto Prazo (Últimos 5 Dias)")
    st.plotly_chart(gerar_grafico_ettj_curto_prazo(df_tesouro), use_container_width=True)
    
    st.markdown("---")
    
    st.subheader("Comparativo de Longo Prazo (Histórico)")
    st.plotly_chart(gerar_grafico_ettj_longo_prazo(df_tesouro), use_container_width=True)
else:
    st.warning("Não foi possível carregar os dados do Tesouro Direto.")
