import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go

@st.cache_data(ttl=3600*4)
def obter_dados_tesouro():
    url = 'https://www.tesourotransparente.gov.br/ckan/dataset/df56aa42-484a-4a59-8184-7676580c81e3/resource/796d2059-14e9-44e3-80c9-2d9e30b405c1/download/precotaxatesourodireto.csv'
    st.info("Carregando dados do Tesouro Direto... (Cache de 4h)")
    try:
        df = pd.read_csv(url, sep=';', decimal=',')
        df['Data Vencimento'] = pd.to_datetime(df['Data Vencimento'], format='%d/%m/%Y')
        df['Data Base'] = pd.to_datetime(df['Data Base'], format='%d/%m/%Y')
        df['Tipo Titulo'] = df['Tipo Titulo'].astype('category')
        return df
    except Exception as e:
        st.error(f"Erro ao baixar dados do Tesouro: {e}")
        return pd.DataFrame()

@st.cache_data
def calcular_juro_real_10a_br(df_tesouro):
    df_ntnb = df_tesouro[df_tesouro['Tipo Titulo'] == 'Tesouro IPCA+ com Juros Semestrais'].copy()
    if df_ntnb.empty: return pd.Series(dtype=float)
    resultados = {}
    for data_base in df_ntnb['Data Base'].unique():
        df_dia = df_ntnb[df_ntnb['Data Base'] == data_base]
        vencimentos_do_dia = df_dia['Data Vencimento'].unique()
        if len(vencimentos_do_dia) > 0:
            target_10y = pd.to_datetime(data_base) + pd.DateOffset(years=10)
            venc_10y = min(vencimentos_do_dia, key=lambda d: abs(d - target_10y))
            taxa = df_dia[df_dia['Data Vencimento'] == venc_10y]['Taxa Compra Manha'].iloc[0]
            resultados[data_base] = taxa
    return pd.Series(resultados).sort_index()

@st.cache_data
def calcular_juro_prefixado_10a_br(df_tesouro):
    """Calcula a série histórica do juro prefixado para o vencimento mais próximo de 10 anos."""
    df_prefixado = df_tesouro[df_tesouro['Tipo Titulo'] == 'Tesouro Prefixado'].copy()
    if df_prefixado.empty: return pd.Series(dtype=float)
    
    resultados = {}
    datas_base = df_prefixado['Data Base'].unique()
    
    for data_base in datas_base:
        df_dia = df_prefixado[df_prefixado['Data Base'] == data_base]
        vencimentos_do_dia = df_dia['Data Vencimento'].unique()
        
        if len(vencimentos_do_dia) > 0:
            target_10y = pd.to_datetime(data_base) + pd.DateOffset(years=10)
            
            # Encontra o vencimento mais próximo de 10 anos
            venc_10y_proximo = min(vencimentos_do_dia, key=lambda d: abs(d - target_10y))
            
            taxa = df_dia[df_dia['Data Vencimento'] == venc_10y_proximo]['Taxa Compra Manha'].iloc[0]
            resultados[data_base] = taxa
            
    return pd.Series(resultados).sort_index()

def gerar_grafico_ntnb_multiplos_vencimentos(df_ntnb_all, vencimentos, metrica):
    fig = go.Figure()
    if not vencimentos:
        return fig.update_layout(title_text="Selecione um ou mais vencimentos para visualizar", template="plotly_dark", title_x=0.5)
    for venc in vencimentos:
        df_venc = df_ntnb_all[df_ntnb_all['Data Vencimento'] == venc].sort_values('Data Base')
        if not df_venc.empty:
            nome_base = df_venc['Tipo Titulo'].iloc[0].replace("Tesouro ", "")
            fig.add_trace(go.Scatter(x=df_venc['Data Base'], y=df_venc[metrica], mode='lines', name=f'{nome_base} {venc.year}'))
    titulo = f'Histórico da Taxa de Compra' if metrica == 'Taxa Compra Manha' else f'Histórico do Preço Unitário (PU)'
    eixo_y = "Taxa de Compra (% a.a.)" if metrica == 'Taxa Compra Manha' else "Preço Unitário (R$)"
    fig.update_layout(title_text=titulo, title_x=0, yaxis_title=eixo_y, xaxis_title="Data", template='plotly_dark', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    fig.update_xaxes(
        rangeselector=dict(
            buttons=list([
                dict(count=1, label="1a", step="year", stepmode="backward"),
                dict(count=3, label="3a", step="year", stepmode="backward"),
                dict(count=5, label="5a", step="year", stepmode="backward"),
                dict(count=1, label="YTD", step="year", stepmode="todate"),
                dict(step="all", label="Tudo")
            ]),
            bgcolor="#333952", font=dict(color="white")
        )
    )
    if not df_ntnb_all.empty:
        end_date = df_ntnb_all['Data Base'].max()
        start_date = end_date - pd.DateOffset(years=5)
        fig.update_xaxes(range=[start_date, end_date])
    return fig

@st.cache_data
def calcular_inflacao_implicita(df):
    df_recente = df[df['Data Base'] == df['Data Base'].max()].copy()
    tipos_ipca = ['Tesouro IPCA+ com Juros Semestrais', 'Tesouro IPCA+']
    df_ipca_raw = df_recente[df_recente['Tipo Titulo'].isin(tipos_ipca)]
    df_prefixados = df_recente[df_recente['Tipo Titulo'] == 'Tesouro Prefixado'].set_index('Data Vencimento')
    df_ipca = df_ipca_raw.sort_values('Tipo Titulo', ascending=False).drop_duplicates('Data Vencimento').set_index('Data Vencimento')
    if df_prefixados.empty or df_ipca.empty: return pd.DataFrame()
    inflacao_implicita = []
    for venc_prefixado, row_prefixado in df_prefixados.iterrows():
        venc_ipca_proximo = min(df_ipca.index, key=lambda d: abs(d - venc_prefixado))
        if abs((venc_ipca_proximo - venc_prefixado).days) < 550:
            taxa_prefixada, taxa_ipca = row_prefixado['Taxa Compra Manha'], df_ipca.loc[venc_ipca_proximo]['Taxa Compra Manha']
            breakeven = (((1 + taxa_prefixada / 100) / (1 + taxa_ipca / 100)) - 1) * 100
            inflacao_implicita.append({'Vencimento do Prefixo': venc_prefixado, 'Inflação Implícita (% a.a.)': breakeven})
    if not inflacao_implicita: return pd.DataFrame()
    return pd.DataFrame(inflacao_implicita).sort_values('Vencimento do Prefixo').set_index('Vencimento do Prefixo')

def gerar_grafico_ettj_curto_prazo(df):
    df_prefixado = df[df['Tipo Titulo'] == 'Tesouro Prefixado'].copy()
    if df_prefixado.empty: return go.Figure().update_layout(title_text="Não há dados para 'Tesouro Prefixado'.")
    datas_disponiveis = sorted(df_prefixado['Data Base'].unique())
    data_recente = datas_disponiveis[-1]
    targets = {f'Hoje ({data_recente.strftime("%d/%m/%Y")})': data_recente, '1 dia Atrás': data_recente - pd.DateOffset(days=1),'2 dias Atrás': data_recente - pd.DateOffset(days=2),'3 dias Atrás': data_recente - pd.DateOffset(days=3),'4 dias Atrás': data_recente - pd.DateOffset(days=4),'5 dias Atrás': data_recente - pd.DateOffset(days=5)}
    datas_para_plotar = {}
    for legenda_base, data_alvo in targets.items():
        datas_validas = [d for d in datas_disponiveis if d <= data_alvo]
        if datas_validas:
            data_real = max(datas_validas)
            if data_real not in datas_para_plotar.values():
                legenda_final = f'{" ".join(legenda_base.split(" ")[:2])} ({data_real.strftime("%d/%m/%Y")})' if 'Atrás' in legenda_base else legenda_base
                datas_para_plotar[legenda_final] = data_real
    fig = go.Figure()
    for legenda, data_base in datas_para_plotar.items():
        df_data = df_prefixado[df_prefixado['Data Base'] == data_base].sort_values('Data Vencimento')
        df_data['Dias Uteis'] = np.busday_count(df_data['Data Base'].values.astype('M8[D]'), df_data['Data Vencimento'].values.astype('M8[D]'))
        line_style = dict(dash='dash') if not legenda.startswith('Hoje') else {}
        fig.add_trace(go.Scatter(x=df_data['Dias Uteis'], y=df_data['Taxa Compra Manha'], mode='lines+markers', name=legenda, line=line_style))
    fig.update_layout(title_text='Curva de Juros (ETTJ) - Curto Prazo (últimos 5 dias)', title_x=0, xaxis_title='Dias Úteis até o Vencimento', yaxis_title='Taxa (% a.a.)', template='plotly_dark', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig

def gerar_grafico_ettj_longo_prazo(df):
    df_prefixado = df[df['Tipo Titulo'] == 'Tesouro Prefixado'].copy()
    if df_prefixado.empty: return go.Figure().update_layout(title_text="Não há dados para 'Tesouro Prefixado'.")
    datas_disponiveis = sorted(df_prefixado['Data Base'].unique())
    data_recente = datas_disponiveis[-1]
    targets = {f'Hoje ({data_recente.strftime("%d/%m/%Y")})': data_recente, '1 Semana Atrás': data_recente - pd.DateOffset(weeks=1), '1 Mês Atrás': data_recente - pd.DateOffset(months=1), '3 Meses Atrás': data_recente - pd.DateOffset(months=3), '6 Meses Atrás': data_recente - pd.DateOffset(months=6), '1 Ano Atrás': data_recente - pd.DateOffset(years=1)}
    datas_para_plotar = {}
    for legenda_base, data_alvo in targets.items():
        datas_validas = [d for d in datas_disponiveis if d <= data_alvo]
        if datas_validas:
            data_real = max(datas_validas)
            if data_real not in datas_para_plotar.values():
                legenda_final = f'{" ".join(legenda_base.split(" ")[:2])} ({data_real.strftime("%d/%m/%Y")})' if not legenda_base.startswith('Hoje') else legenda_base
                datas_para_plotar[legenda_final] = data_real
    fig = go.Figure()
    for legenda, data_base in datas_para_plotar.items():
        df_data = df_prefixado[df_prefixado['Data Base'] == data_base].sort_values('Data Vencimento')
        df_data['Dias Uteis'] = np.busday_count(df_data['Data Base'].values.astype('M8[D]'), df_data['Data Vencimento'].values.astype('M8[D]'))
        line_style = dict(dash='dash') if not legenda.startswith('Hoje') else {}
        fig.add_trace(go.Scatter(x=df_data['Dias Uteis'], y=df_data['Taxa Compra Manha'], mode='lines+markers', name=legenda, line=line_style))
    fig.update_layout(title_text='Curva de Juros (ETTJ) - Longo Prazo (Comparativo Histórico)', title_x=0, xaxis_title='Dias Úteis até o Vencimento', yaxis_title='Taxa (% a.a.)', template='plotly_dark', legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
    return fig

def gerar_grafico_juro_real_10a_br(series_juro_10a):
    """Gera um gráfico de linha para a série de juros de 10 anos do Brasil."""
    if series_juro_10a.empty:
        return go.Figure().update_layout(title_text="Dados para o juro de 10 anos não encontrados.")
    
    fig = px.line(series_juro_10a, title='Juro Real de 10 Anos (NTN-B)', template='plotly_dark')
    
    end_date = series_juro_10a.index.max()
    buttons = []
    periods = {'6M': 182, '1A': 365, '2A': 730, '5A': 1825, '10A': 3650, 'Máx': 'max'}
    
    for label, days in periods.items():
        start_date = series_juro_10a.index.min() if days == 'max' else end_date - pd.Timedelta(days=days)
        buttons.append(dict(method='relayout', label=label, args=[{'xaxis.range': [start_date, end_date], 'yaxis.autorange': True}]))
    
    fig.update_layout(
        title_x=0, 
        yaxis_title="Taxa (% a.a.)", 
        xaxis_title="Data", 
        showlegend=False,
        updatemenus=[dict(type="buttons", direction="right", showactive=True, x=1, xanchor="right", y=1.05, yanchor="bottom", buttons=buttons)]
    )
    
    start_date_1y = end_date - pd.Timedelta(days=365)
    fig.update_xaxes(range=[start_date_1y, end_date])

    filtered_series = series_juro_10a.loc[start_date_1y:end_date].dropna()
    if not filtered_series.empty:
        min_y, max_y = filtered_series.min(), filtered_series.max()
        padding = (max_y - min_y) * 0.10 if (max_y - min_y) > 0 else 0.5
        fig.update_yaxes(range=[min_y - padding, max_y + padding])

    return fig

def gerar_grafico_juro_prefixado_10a_br(series_juro_10a):
    """Gera um gráfico de linha para a série de juros prefixados de 10 anos do Brasil."""
    if series_juro_10a.empty:
        return go.Figure().update_layout(title_text="Dados para o juro prefixado de 10 anos não encontrados.")
    
    fig = px.line(series_juro_10a, title='Juro Prefixado de 10 Anos (LTN/NTN-F)', template='plotly_dark')
    
    end_date = series_juro_10a.index.max()
    buttons = []
    periods = {'6M': 182, '1A': 365, '2A': 730, '5A': 1825, '10A': 3650, 'Máx': 'max'}
    
    for label, days in periods.items():
        start_date = series_juro_10a.index.min() if days == 'max' else end_date - pd.Timedelta(days=days)
        buttons.append(dict(method='relayout', label=label, args=[{'xaxis.range': [start_date, end_date], 'yaxis.autorange': True}]))
    
    fig.update_layout(
        title_x=0, 
        yaxis_title="Taxa (% a.a.)", 
        xaxis_title="Data", 
        showlegend=False,
        updatemenus=[dict(type="buttons", direction="right", showactive=True, x=1, xanchor="right", y=1.05, yanchor="bottom", buttons=buttons)]
    )
    
    start_date_1y = end_date - pd.Timedelta(days=365)
    fig.update_xaxes(range=[start_date_1y, end_date])

    filtered_series = series_juro_10a.loc[start_date_1y:end_date].dropna()
    if not filtered_series.empty:
        min_y, max_y = filtered_series.min(), filtered_series.max()
        padding = (max_y - min_y) * 0.10 if (max_y - min_y) > 0 else 0.5
        fig.update_yaxes(range=[min_y - padding, max_y + padding])

    return fig
