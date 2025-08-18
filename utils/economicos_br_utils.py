import streamlit as st
import pandas as pd
from bcb import sgs

@st.cache_data(ttl=3600*4)
def carregar_dados_bcb():
    SERIES_CONFIG = {'Spread Bancário': {'id': 20783}, 'Inadimplência': {'id': 21082}, 'Crédito/PIB': {'id': 20622}, 'Juros Médio': {'id': 20714}, 'Confiança Consumidor': {'id': 4393}, 'IPCA': {'id': 16122}, 'Atraso 15-90d Total': {'id': 21006}, 'Atraso 15-90d Agro': {'id': 21069}, 'Inadimplência Crédito Rural': {'id': 21146}}
    lista_dfs_sucesso, config_sucesso = [], {}
    for name, config in SERIES_CONFIG.items():
        try:
            df_temp = sgs.get({name: config['id']}, start='2010-01-01')
            lista_dfs_sucesso.append(df_temp)
            config_sucesso[name] = config
        except Exception as e:
            st.warning(f"Não foi possível carregar o indicador '{name}': {e}")
    if not lista_dfs_sucesso:
        return pd.DataFrame(), {}
    df_full = pd.concat(lista_dfs_sucesso, axis=1)
    df_full.ffill(inplace=True)
    df_full.dropna(inplace=True)
    return df_full, config_sucesso
