import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import os
import requests
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
import io
import plotly.express as px
import plotly.graph_objects as go

# --- Funções para Radar de Insiders ---
@st.cache_data(ttl=3600*24)
def executar_analise_insiders():
    ANO_ATUAL = datetime.now().year
    URL_MOVIMENTACOES = f"https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/VLMO/DADOS/vlmo_cia_aberta_{ANO_ATUAL}.zip"
    URL_CADASTRO = f"https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/FCA/DADOS/fca_cia_aberta_{ANO_ATUAL}.zip"
    ZIP_MOVIMENTACOES, CSV_MOVIMENTACOES = "movimentacoes.zip", f"vlmo_cia_aberta_con_{ANO_ATUAL}.csv"
    ZIP_CADASTRO, CSV_CADASTRO = "cadastro.zip", f"fca_cia_aberta_valor_mobiliario_{ANO_ATUAL}.csv"

    def _cvm_baixar_zip(url, nome_zip, nome_csv):
        try:
            response = requests.get(url, timeout=60)
            response.raise_for_status()
            with open(nome_zip, 'wb') as f: f.write(response.content)
            with zipfile.ZipFile(nome_zip, 'r') as z: z.extract(nome_csv)
            os.remove(nome_zip)
            return nome_csv
        except Exception as e:
            st.error(f"Erro no download de {url}: {e}")
            if os.path.exists(nome_zip): os.remove(nome_zip)
            return None

    def _obter_market_cap_individual(ticker):
        if pd.isna(ticker) or not isinstance(ticker, str): return ticker, np.nan
        try:
            stock = yf.Ticker(f"{ticker.strip()}.SA")
            return ticker, stock.info.get('marketCap', np.nan)
        except Exception:
            return ticker, np.nan

    caminho_csv_mov = _cvm_baixar_zip(URL_MOVIMENTACOES, ZIP_MOVIMENTACOES, CSV_MOVIMENTACOES)
    caminho_csv_cad = _cvm_baixar_zip(URL_CADASTRO, ZIP_CADASTRO, CSV_CADASTRO)

    if not caminho_csv_mov or not caminho_csv_cad: return None, None, None

    df_mov = pd.read_csv(caminho_csv_mov, sep=';', encoding='ISO-8859-1', on_bad_lines='skip')
    df_cad = pd.read_csv(caminho_csv_cad, sep=';', encoding='ISO-8859-1', on_bad_lines='skip', usecols=['CNPJ_Companhia', 'Codigo_Negociacao'])
    os.remove(caminho_csv_mov); os.remove(caminho_csv_cad)

    df_mov['Data_Movimentacao'] = pd.to_datetime(df_mov['Data_Movimentacao'], errors='coerce')
    df_mov.dropna(subset=['Data_Movimentacao'], inplace=True)
    df_mov = df_mov[df_mov['Tipo_Movimentacao'].isin(['Compra à vista', 'Venda à vista'])]
    ultimo_mes = df_mov['Data_Movimentacao'].max().to_period('M')
    df_mes = df_mov[df_mov['Data_Movimentacao'].dt.to_period('M') == ultimo_mes].copy()
    df_mes['Volume_Net'] = np.where(df_mes['Tipo_Movimentacao'] == 'Compra à vista', df_mes['Volume'], -df_mes['Volume'])

    df_controladores = df_mes[df_mes['Tipo_Cargo'] == 'Controlador ou Vinculado'].copy()
    df_outros = df_mes[df_mes['Tipo_Cargo'] != 'Controlador ou Vinculado'].copy()

    df_net_controladores = df_controladores.groupby(['CNPJ_Companhia', 'Nome_Companhia'])['Volume_Net'].sum().reset_index()
    df_net_outros = df_outros.groupby(['CNPJ_Companhia', 'Nome_Companhia'])['Volume_Net'].sum().reset_index()

    cnpjs_unicos = pd.concat([df_net_controladores[['CNPJ_Companhia']], df_net_outros[['CNPJ_Companhia']]]).drop_duplicates()
    df_tickers = df_cad.dropna().drop_duplicates(subset=['CNPJ_Companhia'])
    df_lookup = pd.merge(cnpjs_unicos, df_tickers, on='CNPJ_Companhia', how='left')

    market_caps = {}
    tickers_para_buscar = df_lookup['Codigo_Negociacao'].dropna().unique().tolist()
    progress_bar = st.progress(0, text="Buscando valores de mercado...")
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_ticker = {executor.submit(_obter_market_cap_individual, ticker): ticker for ticker in tickers_para_buscar}
        for i, future in enumerate(as_completed(future_to_ticker)):
            ticker, market_cap = future.result()
            market_caps[ticker] = market_cap
            progress_bar.progress((i + 1) / len(tickers_para_buscar), text=f"Buscando valores de mercado... ({i+1}/{len(tickers_para_buscar)})")
    progress_bar.empty()
    df_market_caps = pd.DataFrame(list(market_caps.items()), columns=['Codigo_Negociacao', 'MarketCap'])
    df_market_cap_lookup = pd.merge(df_lookup, df_market_caps, on="Codigo_Negociacao", how="left")

    df_final_controladores = pd.merge(df_net_controladores, df_market_cap_lookup, on='CNPJ_Companhia', how='left')
    df_final_controladores['Volume_vs_MarketCap_Pct'] = (df_final_controladores['Volume_Net'] / df_final_controladores['MarketCap']) * 100
    df_final_controladores.fillna({'Volume_vs_MarketCap_Pct': 0}, inplace=True)

    df_final_outros = pd.merge(df_net_outros, df_market_cap_lookup, on='CNPJ_Companhia', how='left')
    df_final_outros['Volume_vs_MarketCap_Pct'] = (df_final_outros['Volume_Net'] / df_final_outros['MarketCap']) * 100
    df_final_outros.fillna({'Volume_vs_MarketCap_Pct': 0}, inplace=True)

    return df_final_controladores, df_final_outros, ultimo_mes

def gerar_graficos_insiders_plotly(df_dados, top_n=10):
    if df_dados.empty: return None, None
    df_plot_volume = df_dados.sort_values(by='Volume_Net', ascending=True).tail(top_n)
    fig_volume = px.bar(df_plot_volume, y='Nome_Companhia', x='Volume_Net', orientation='h', title=f'Top {top_n} por Volume Líquido', template='plotly_dark', text='Volume_Net')
    fig_volume.update_traces(texttemplate='R$ %{text:,.2s}', textposition='outside')
    fig_volume.update_layout(title_x=0, xaxis_title="Volume Líquido (R$)", yaxis_title="")
    df_plot_relevancia = df_dados.sort_values(by='Volume_vs_MarketCap_Pct', ascending=True).tail(top_n)
    fig_relevancia = px.bar(df_plot_relevancia, y='Nome_Companhia', x='Volume_vs_MarketCap_Pct', orientation='h', title=f'Top {top_n} por Relevância (Volume / Valor de Mercado)', template='plotly_dark', text='Volume_vs_MarketCap_Pct')
    fig_relevancia.update_traces(texttemplate='%{text:.3f}%', textposition='outside')
    fig_relevancia.update_layout(title_x=0, xaxis_title="Volume como % do Valor de Mercado", yaxis_title="")
    return fig_volume, fig_relevancia

# --- Funções para Análise de Ratio ---
@st.cache_data
def carregar_dados_acoes(tickers, period="max"):
    try:
        data = yf.download(tickers, period=period, auto_adjust=True)['Close']
        if isinstance(data, pd.Series):
            data = data.to_frame(tickers[0])
        return data.dropna()
    except Exception:
        return pd.DataFrame()

@st.cache_data
def calcular_metricas_ratio(data, ticker_a, ticker_b, window=252):
    ratio = data[ticker_a] / data[ticker_b]
    df_metrics = pd.DataFrame({'Ratio': ratio})
    df_metrics['Rolling_Mean'] = ratio.rolling(window=window).mean()
    rolling_std = ratio.rolling(window=window).std()
    static_median = ratio.median()
    static_std = ratio.std()
    df_metrics['Static_Median'] = static_median
    df_metrics['Upper_Band_2x_Rolling'] = df_metrics['Rolling_Mean'] + (2 * rolling_std)
    df_metrics['Lower_Band_2x_Rolling'] = df_metrics['Rolling_Mean'] - (2 * rolling_std)
    df_metrics['Upper_Band_1x_Static'] = static_median + (1 * static_std)
    df_metrics['Lower_Band_1x_Static'] = static_median - (1 * static_std)
    df_metrics['Upper_Band_2x_Static'] = static_median + (2 * static_std)
    df_metrics['Lower_Band_2x_Static'] = static_median - (2 * static_std)
    return df_metrics

def calcular_kpis_ratio(df_metrics):
    if 'Ratio' not in df_metrics or df_metrics['Ratio'].dropna().empty: return None
    ratio_series = df_metrics['Ratio'].dropna()
    kpis = {"atual": ratio_series.iloc[-1], "media": ratio_series.mean(), "minimo": ratio_series.min(), "data_minimo": ratio_series.idxmin(), "maximo": ratio_series.max(), "data_maximo": ratio_series.idxmax()}
    if kpis["atual"] > 0: kpis["variacao_para_media"] = (kpis["media"] / kpis["atual"] - 1) * 100
    else: kpis["variacao_para_media"] = np.inf
    return kpis

def gerar_grafico_ratio(df_metrics, ticker_a, ticker_b, window):
    fig = go.Figure()
    static_median_val = df_metrics['Static_Median'].iloc[-1]
    fig.add_hline(y=static_median_val, line_color='red', line_dash='dash', annotation_text=f'Mediana ({static_median_val:.2f})', annotation_position="top left")
    fig.add_hline(y=df_metrics['Upper_Band_1x_Static'].iloc[-1], line_color='#2ca02c', line_dash='dot', annotation_text='+1 DP Estático', annotation_position="top left")
    fig.add_hline(y=df_metrics['Lower_Band_1x_Static'].iloc[-1], line_color='#2ca02c', line_dash='dot', annotation_text='-1 DP Estático', annotation_position="top left")
    fig.add_hline(y=df_metrics['Upper_Band_2x_Static'].iloc[-1], line_color='#d62728', line_dash='dot', annotation_text='+2 DP Estático', annotation_position="top left")
    fig.add_hline(y=df_metrics['Lower_Band_2x_Static'].iloc[-1], line_color='#d62728', line_dash='dot', annotation_text='-2 DP Estático', annotation_position="top left")
    fig.add_trace(go.Scatter(x=df_metrics.index, y=df_metrics['Upper_Band_2x_Rolling'], mode='lines', line_color='gray', line_width=1, name='Bollinger Superior', showlegend=False))
    fig.add_trace(go.Scatter(x=df_metrics.index, y=df_metrics['Lower_Band_2x_Rolling'], mode='lines', line_color='gray', line_width=1, name='Bollinger Inferior', fill='tonexty', fillcolor='rgba(128,128,128,0.1)', showlegend=False))
    fig.add_trace(go.Scatter(x=df_metrics.index, y=df_metrics['Rolling_Mean'], mode='lines', line_color='orange', line_dash='dash', name=f'Média Móvel ({window}d)'))
    fig.add_trace(go.Scatter(x=df_metrics.index, y=df_metrics['Ratio'], mode='lines', line_color='#636EFA', name='Ratio Atual', line_width=2.5))
    fig.update_layout(title_text=f'Análise de Ratio: {ticker_a} / {ticker_b}', template='plotly_dark', title_x=0, legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig

# --- Funções para Amplitude de Mercado ---
@st.cache_data(ttl=86400)
def obter_tickers_cvm_amplitude():
    st.info("Buscando lista de tickers da CVM... (rápido se em cache diário)")
    ano = datetime.now().year
    url = f'https://dados.cvm.gov.br/dados/CIA_ABERTA/DOC/FCA/DADOS/fca_cia_aberta_{ano}.zip'
    nome_arquivo_csv = f'fca_cia_aberta_valor_mobiliario_{ano}.csv'
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            with z.open(nome_arquivo_csv) as f:
                df = pd.read_csv(f, sep=';', encoding='ISO-8859-1', dtype={'Valor_Mobiliario': 'category', 'Mercado': 'category'})
        df_filtrado = df[(df['Valor_Mobiliario'].isin(['Ações Ordinárias', 'Ações Preferenciais'])) & (df['Mercado'] == 'Bolsa')]
        tickers = df_filtrado['Codigo_Negociacao'].dropna().unique().tolist()
        st.success(f"{len(tickers)} tickers encontrados na CVM.")
        return tickers
    except Exception as e:
        st.error(f"ERRO: Não foi possível obter os dados da CVM. {e}")
        return None

@st.cache_data(ttl=86400)
def obter_precos_historicos_amplitude(tickers, anos_historico=15):
    st.info(f"Buscando {anos_historico} anos de dados de preços para {len(tickers)} ativos... (Pode ser MUITO lento na primeira execução do dia)")
    tickers_sa = [ticker + ".SA" for ticker in tickers]
    data_final = datetime.now()
    data_inicial = data_final - timedelta(days=anos_historico*365)
    dados_completos = yf.download(tickers=tickers_sa, start=data_inicial, end=data_final, auto_adjust=True, progress=False)
    if not dados_completos.empty:
        precos_fechamento = dados_completos['Close'].astype('float32')
        st.success("Download dos dados de preços concluído.")
        return precos_fechamento
    else:
        st.error("ERRO: Falha no download dos dados de preços.")
        return pd.DataFrame()

@st.cache_data(ttl=86400)
def calcular_dados_amplitude(precos_fechamento):
    if precos_fechamento.empty: return pd.Series()
    st.info("Calculando o indicador de amplitude...")
    mma200 = precos_fechamento.rolling(window=200).mean()
    acima_da_media = precos_fechamento > mma200
    percentual_acima_media = (acima_da_media.sum(axis=1) / precos_fechamento.notna().sum(axis=1)) * 100
    percentual_acima_media.dropna(inplace=True)
    dados_filtrados = percentual_acima_media[percentual_acima_media.index >= '2014-01-01']
    return dados_filtrados

def gerar_grafico_amplitude(dados_amplitude, mediana):
    if dados_amplitude.empty: return None
    st.info("Gerando o gráfico de linha...")
    fig = go.Figure()
    fig.add_hline(y=70, line_color='red', line_dash='dash', annotation_text='Sobrecompra (70%)', annotation_position="bottom right")
    fig.add_hline(y=50, line_color='gray', line_dash='dash', annotation_text='Linha Central (50%)', annotation_position="bottom right")
    fig.add_hline(y=mediana, line_color="#a855f7", line_dash="dot", annotation_text=f"Mediana ({mediana:.1f}%)", annotation_position="bottom left", annotation_font=dict(color="#a855f7"))
    fig.add_hline(y=30, line_color='green', line_dash='dash', annotation_text='Sobrevenda (30%)', annotation_position="bottom right")
    fig.add_trace(go.Scatter(x=dados_amplitude.index, y=dados_amplitude, mode='lines', name='% Acima da MMA 200', line=dict(color='#636EFA', width=2)))
    fig.update_layout(title_text='Raio-X do Mercado (desde 2014)', title_x=0, yaxis_title='Percentual de Ativos (%)', xaxis_title='Data', template='plotly_dark', yaxis_range=[0, 100], legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig

def gerar_grafico_distribuicao_amplitude(dados_amplitude, mediana):
    if dados_amplitude.empty: return None
    st.info("Gerando o gráfico de distribuição...")
    valor_atual = dados_amplitude.iloc[-1]
    fig = px.histogram(dados_amplitude, nbins=50, title='Distribuição Histórica do Indicador', template='plotly_dark')
    fig.update_layout(showlegend=False, title_x=0, xaxis_title="Percentual de Ações Acima da MMA 200", yaxis_title="Frequência (Dias)")
    fig.add_vline(x=mediana, line_color="#a855f7", line_dash="dot", annotation_text=f" Mediana: {mediana:.1f}% ", annotation_position="top right", annotation_font=dict(color="#a855f7", size=14), annotation_bgcolor="rgba(0,0,0,0.7)")
    fig.add_vline(x=valor_atual, line_color="#fde047", line_dash="dash", annotation_text=f" Hoje: {valor_atual:.1f}% ", annotation_position="top left", annotation_font=dict(color="#fde047", size=14), annotation_bgcolor="rgba(0,0,0,0.7)")
    return fig
