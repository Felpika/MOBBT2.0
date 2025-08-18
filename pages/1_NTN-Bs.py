import streamlit as st
import pandas as pd
import plotly.express as px

# --- Imports da nova estrutura utils ---
from utils.tesouro_utils import (
    obter_dados_tesouro,
    calcular_inflacao_implicita,
    calcular_juro_real_10a_br,  # Renomeada
    calcular_juro_prefixado_10a_br, # Nova
    gerar_grafico_ntnb_multiplos_vencimentos,
    gerar_grafico_juro_prefixado_10a_br, # Nova
)
from utils.internacional_utils import carregar_dados_fred, gerar_grafico_spread_br_eua

# --- Configuração da Página ---
st.set_page_config(layout="wide", page_title="NTN-Bs")

# --- Conteúdo da Página ---
st.header("Dashboard de Análise de NTN-Bs (Tesouro IPCA+)")
st.markdown("---")

df_tesouro = obter_dados_tesouro()

if not df_tesouro.empty:
    st.subheader("Análise Histórica Comparativa")
    st.info("Selecione um ou mais vencimentos para comparar a variação da taxa ou preço ao longo do tempo.")

    tipos_ntnb = ['Tesouro IPCA+', 'Tesouro IPCA+ com Juros Semestrais']
    df_ntnb_all = df_tesouro[df_tesouro['Tipo Titulo'].isin(tipos_ntnb)]

    vencimentos_disponiveis = sorted(df_ntnb_all['Data Vencimento'].unique())

    anos_padrao = [2030, 2035, 2040, 2045, 2060]
    vencimentos_padrao = [v for v in vencimentos_disponiveis if pd.to_datetime(v).year in anos_padrao]

    col1, col2 = st.columns([0.8, 0.2])
    with col1:
        vencimentos_selecionados = st.multiselect(
            "Selecione os Vencimentos",
            options=vencimentos_disponiveis,
            default=vencimentos_padrao,
            format_func=lambda dt: pd.to_datetime(dt).strftime('%d/%m/%Y'),
            key='multi_venc_ntnb'
        )
    with col2:
         metrica_escolhida = st.radio(
            "Analisar por:", ('Taxa', 'PU'),
            horizontal=True, key='metrica_ntnb',
            help="Analisar por Taxa de Compra ou Preço Unitário (PU)"
        )
    coluna_metrica = 'Taxa Compra Manha' if metrica_escolhida == 'Taxa' else 'PU Compra Manha'

    fig_hist_ntnb = gerar_grafico_ntnb_multiplos_vencimentos(
        df_ntnb_all, vencimentos_selecionados, metrica=coluna_metrica
    )
    st.plotly_chart(fig_hist_ntnb, use_container_width=True)

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.subheader("Inflação Implícita (Breakeven)")
        df_breakeven = calcular_inflacao_implicita(df_tesouro)
        if not df_breakeven.empty:
            fig_breakeven = px.bar(df_breakeven, y='Inflação Implícita (% a.a.)', text_auto='.2f', title='Inflação Implícita por Vencimento').update_traces(textposition='outside')
            fig_breakeven.update_layout(title_x=0, template='plotly_dark')
            st.plotly_chart(fig_breakeven, use_container_width=True)
        else:
            st.warning("Não há pares de títulos para calcular a inflação implícita hoje.")
            
    with col2:
        st.subheader("Juro Prefixado de ~10 Anos")
        df_juro_prefixado_br = calcular_juro_prefixado_10a_br(df_tesouro)
        if not df_juro_prefixado_br.empty:
            fig_juro_10a = gerar_grafico_juro_prefixado_10a_br(df_juro_prefixado_br)
            st.plotly_chart(fig_juro_10a, use_container_width=True, config={'modeBarButtonsToRemove': ['autoscale']})
        else:
            st.warning("Não foi possível calcular a série de juros prefixados de 10 anos.")

    with col3:
        st.subheader("Spread Juro Real: Brasil vs. EUA")
        st.info("Diferença entre a taxa da NTN-B de ~10 anos e o título americano de 10 anos.")
        
        FRED_API_KEY = st.secrets.get("FRED_API_KEY")
        
        if not FRED_API_KEY:
            st.error("Chave da API do FRED não configurada. Por favor, configure o secret 'FRED_API_KEY'.")
            st.stop()
        
        df_fred_br_tab = carregar_dados_fred(FRED_API_KEY, {'DGS10': 'Juros 10 Anos EUA'})
        if not df_fred_br_tab.empty:
            # Usando a função correta para o juro REAL aqui
            df_juro_br_spread = calcular_juro_real_10a_br(df_tesouro) 
            if not df_juro_br_spread.empty:
                fig_spread_br_eua = gerar_grafico_spread_br_eua(df_juro_br_spread, df_fred_br_tab)
                st.plotly_chart(fig_spread_br_eua, use_container_width=True, config={'modeBarButtonsToRemove': ['autoscale']})
            else:
                st.warning("Não foi possível calcular a série de juros reais de 10 anos para o Brasil.")
        else:
            st.warning("Não foi possível carregar os dados de juros dos EUA.")
else:
    st.warning("Não foi possível carregar os dados do Tesouro Direto para exibir esta página.")
