import streamlit as st

# --- Imports da nova estrutura utils ---
from utils.internacional_utils import carregar_dados_fred, gerar_grafico_fred

# --- Configuração da Página ---
st.set_page_config(layout="wide", page_title="Internacional")

# --- Conteúdo da Página ---
st.header("Monitor de Indicadores Internacionais (FRED)")
st.markdown("---")

# Lembre-se de configurar este Secret no Streamlit Cloud!
# Em pages/6_Internacional.py e pages/1_NTN-Bs.py

FRED_API_KEY = st.secrets.get("FRED_API_KEY")

if not FRED_API_KEY:
    st.error("Chave da API do FRED não configurada. Por favor, configure o secret 'FRED_API_KEY'.")
    st.stop() # Impede a execução do resto da página

# O restante do código que usa a chave...

INDICADORES_FRED = {
    'T10Y2Y': 'Spread da Curva de Juros dos EUA (10 Anos vs 2 Anos)',
    'BAMLH0A0HYM2': 'Spread de Crédito High Yield dos EUA (ICE BofA)',
    'DGS10': 'Juros do Título Americano de 10 Anos (DGS10)'
}
df_fred = carregar_dados_fred(FRED_API_KEY, INDICADORES_FRED)
config_fred = {'modeBarButtonsToRemove': ['autoscale']}

if not df_fred.empty:
    st.info("O **Spread da Curva de Juros dos EUA (T10Y2Y)** é um dos indicadores mais observados para prever recessões. Quando o valor fica negativo (inversão da curva), historicamente tem sido um sinal de que uma recessão pode ocorrer nos próximos 6 a 18 meses.")
    fig_t10y2y = gerar_grafico_fred(df_fred, 'T10Y2Y', INDICADORES_FRED['T10Y2Y'])
    st.plotly_chart(fig_t10y2y, use_container_width=True, config=config_fred)
    
    st.markdown("---")
    
    st.info("O **Spread de Crédito High Yield** mede o prêmio de risco exigido pelo mercado para investir em títulos de empresas com maior risco de crédito. **Spreads crescentes** indicam aversão ao risco (medo) e podem sinalizar uma desaceleração econômica.")
    fig_hy = gerar_grafico_fred(df_fred, 'BAMLH0A0HYM2', INDICADORES_FRED['BAMLH0A0HYM2'])
    st.plotly_chart(fig_hy, use_container_width=True, config=config_fred)
    
    st.markdown("---")
    
    st.info("A **taxa de juros do título americano de 10 anos (DGS10)** é uma referência para o custo do crédito global. **Juros em alta** podem indicar expectativas de crescimento econômico e inflação mais fortes.")
    fig_dgs10 = gerar_grafico_fred(df_fred, 'DGS10', INDICADORES_FRED['DGS10'])
    st.plotly_chart(fig_dgs10, use_container_width=True, config=config_fred)
else:
    st.warning("Não foi possível carregar dados do FRED. Verifique a chave da API ou a conexão com a internet.")
