import streamlit as st
import pandas as pd
import requests
import io
import plotly.express as px
import plotly.graph_objects as go

@st.cache_data(ttl=3600*4)
def carregar_dados_idex():
    st.info("Carregando dados do IDEX JGP... (Cache de 4h)")
    url_geral = "https://jgp-credito-public-s3.s3.us-east-1.amazonaws.com/idex/idex_cdi_geral_datafile.xlsx"
    url_low_rated = "https://jgp-credito-public-s3.s3.us-east-1.amazonaws.com/idex/idex_cdi_low_rated_datafile.xlsx"
    emissores_para_remover = ['AMERICANAS SA', 'Light - Servicos de Eletricidade', 'Aeris', 'Viveo']

    def _processar_url(url):
        response = requests.get(url)
        response.raise_for_status()
        df = pd.read_excel(io.BytesIO(response.content), sheet_name='Detalhado')
        df.columns = df.columns.str.strip()
        df_filtrado = df[~df['Emissor'].isin(emissores_para_remover)].copy()
        df_filtrado['Data'] = pd.to_datetime(df_filtrado['Data'])
        df_filtrado['weighted_spread'] = df_filtrado['Peso no índice (%)'] * df_filtrado['Spread de compra (%)']
        daily_spread = df_filtrado.groupby('Data').apply(lambda x: x['weighted_spread'].sum() / x['Peso no índice (%)'].sum() if x['Peso no índice (%)'].sum() != 0 else 0).reset_index(name='spread')
        return daily_spread.set_index('Data')

    try:
        spread_geral = _processar_url(url_geral)
        spread_low_rated = _processar_url(url_low_rated)
        df_final = pd.merge(spread_geral, spread_low_rated, on='Data', how='outer', suffixes=('_geral', '_low_rated'))
        df_final.rename(columns={'spread_geral': 'IDEX Geral (Filtrado)', 'spread_low_rated': 'IDEX Low Rated (Filtrado)'}, inplace=True)
        return df_final.sort_index()
    except Exception as e:
        st.error(f"Erro ao carregar dados do IDEX JGP: {e}")
        return pd.DataFrame()

@st.cache_data(ttl=3600*4)
def carregar_dados_idex_infra():
    st.info("Carregando dados do IDEX INFRA... (Cache de 4h)")
    url_infra = "https://jgp-credito-public-s3.s3.us-east-1.amazonaws.com/idex/idex_infra_geral_datafile.xlsx"
    try:
        response = requests.get(url_infra)
        response.raise_for_status()
        df = pd.read_excel(io.BytesIO(response.content), sheet_name='Detalhado')
        df.columns = df.columns.str.strip()
        df['Data'] = pd.to_datetime(df['Data'])
        df['weighted_spread'] = df['Peso no índice (%)'] * df['MID spread (Bps/NTNB)']
        daily_spread = df.groupby('Data').apply(lambda x: x['weighted_spread'].sum() / x['Peso no índice (%)'].sum() if x['Peso no índice (%)'].sum() != 0 else 0).reset_index(name='spread_bps_ntnb')
        return daily_spread.set_index('Data').sort_index()
    except Exception as e:
        st.error(f"Erro ao carregar dados do IDEX INFRA: {e}")
        return pd.DataFrame()

def gerar_grafico_idex_infra(df_idex_infra):
    if df_idex_infra.empty:
        return go.Figure().update_layout(title_text="Não foi possível gerar o gráfico do IDEX INFRA.")
    fig = px.line(df_idex_infra, y='spread_bps_ntnb', title='Histórico do Spread Médio Ponderado: IDEX INFRA', template='plotly_dark')
    fig.update_layout(title_x=0, yaxis_title='Spread Médio (Bps sobre NTNB)', xaxis_title='Data', showlegend=False)
    return fig

def gerar_grafico_idex(df_idex):
    if df_idex.empty:
        return go.Figure().update_layout(title_text="Não foi possível gerar o gráfico do IDEX.")
    fig = px.line(df_idex, y=['IDEX Geral (Filtrado)', 'IDEX Low Rated (Filtrado)'], title='Histórico do Spread Médio Ponderado: IDEX JGP', template='plotly_dark')
    fig.update_yaxes(tickformat=".2%")
    fig.update_traces(hovertemplate='%{y:.2%}')
    fig.update_layout(title_x=0, yaxis_title='Spread Médio Ponderado (%)', xaxis_title='Data', legend_title_text='Índice', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig
