import streamlit as st

# --- Imports da nova estrutura utils ---
from utils.commodities_utils import carregar_dados_commodities, calcular_variacao_commodities, colorir_negativo_positivo, gerar_dashboard_commodities

# --- Configuração da Página ---
st.set_page_config(layout="wide", page_title="Commodities")

# --- Conteúdo da Página ---
st.header("Painel de Preços de Commodities")
st.markdown("---")

dados_commodities_categorizados = carregar_dados_commodities()

if dados_commodities_categorizados:
    st.subheader("Variação Percentual de Preços")
    df_variacao = calcular_variacao_commodities(dados_commodities_categorizados)
    if not df_variacao.empty:
        cols_variacao = [col for col in df_variacao.columns if 'Variação' in col]
        format_dict = {'Preço Atual': '{:,.2f}'}
        format_dict.update({col: '{:+.2%}' for col in cols_variacao})
        st.dataframe(df_variacao.style.format(format_dict, na_rep="-").applymap(colorir_negativo_positivo, subset=cols_variacao), use_container_width=True)
    else:
        st.warning("Não foi possível calcular a variação de preços.")
    
    st.markdown("---")
    
    fig_commodities = gerar_dashboard_commodities(dados_commodities_categorizados)
    st.plotly_chart(fig_commodities, use_container_width=True, config={'modeBarButtonsToRemove': ['autoscale']})
else:
    st.warning("Não foi possível carregar os dados de Commodities.")
