import streamlit as st

# --- Imports da nova estrutura utils ---
from utils.acoes_br_utils import (
    executar_analise_insiders,
    gerar_graficos_insiders_plotly,
    carregar_dados_acoes,
    calcular_metricas_ratio,
    calcular_kpis_ratio,
    gerar_grafico_ratio,
    obter_tickers_cvm_amplitude,
    obter_precos_historicos_amplitude,
    calcular_dados_amplitude,
    gerar_grafico_amplitude,
    gerar_grafico_distribuicao_amplitude
)

# --- Configuração da Página ---
st.set_page_config(layout="wide", page_title="Ações BR")

# --- Conteúdo da Página ---
st.header("Ferramentas de Análise de Ações Brasileiras")
st.markdown("---")

# Seção 1: Análise de Ratio
with st.container():
    st.subheader("Análise de Ratio de Ativos (Long & Short)")
    st.info("Esta ferramenta calcula o ratio entre o preço de dois ativos. "
            "**Interpretação:** Quando o ratio está alto, o Ativo A está caro em relação ao Ativo B. "
            "Quando está baixo, está barato. As bandas mostram desvios padrão que podem indicar pontos de reversão à média.")

    def executar_analise_ratio():
        if 'ticker_a_key' not in st.session_state or 'ticker_b_key' not in st.session_state:
            st.session_state.ticker_a_key = "SMAL11.SA"
            st.session_state.ticker_b_key = "BOVA11.SA"
            st.session_state.window_size_key = 252

        st.session_state.spinner_placeholder.info(f"Buscando e processando dados para {st.session_state.ticker_a_key} e {st.session_state.ticker_b_key}...")
        close_prices = carregar_dados_acoes([st.session_state.ticker_a_key, st.session_state.ticker_b_key], period="max")
        if close_prices.empty or close_prices.shape[1] < 2:
            st.session_state.spinner_placeholder.error(f"Não foi possível obter dados para ambos os tickers. Verifique os códigos (ex: PETR4.SA) e tente novamente.")
            st.session_state.fig_ratio, st.session_state.kpis_ratio = None, None
        else:
            ratio_analysis = calcular_metricas_ratio(close_prices, st.session_state.ticker_a_key, st.session_state.ticker_b_key, window=st.session_state.window_size_key)
            st.session_state.fig_ratio = gerar_grafico_ratio(ratio_analysis, st.session_state.ticker_a_key, st.session_state.ticker_b_key, window=st.session_state.window_size_key)
            st.session_state.kpis_ratio = calcular_kpis_ratio(ratio_analysis)
            st.session_state.spinner_placeholder.empty()

    col1, col2, col3 = st.columns([0.4, 0.4, 0.2])
    with col1: st.text_input("Ticker do Ativo A (Numerador)", "SMAL11.SA", key="ticker_a_key")
    with col2: st.text_input("Ticker do Ativo B (Denominador)", "BOVA11.SA", key="ticker_b_key")
    with col3: st.number_input("Janela Móvel (dias)", min_value=20, max_value=500, value=252, key="window_size_key")
    
    st.button("Analisar Ratio", on_click=executar_analise_ratio, use_container_width=True)
    st.session_state.spinner_placeholder = st.empty()

    if 'fig_ratio' not in st.session_state:
        executar_analise_ratio()

    if st.session_state.get('kpis_ratio'):
        kpis = st.session_state.kpis_ratio
        cols = st.columns(5)
        cols[0].metric("Ratio Atual", f"{kpis['atual']:.2f}")
        cols[1].metric("Média Histórica", f"{kpis['media']:.2f}")
        cols[2].metric("Mínimo Histórico", f"{kpis['minimo']:.2f}", f"em {kpis['data_minimo'].strftime('%d/%m/%Y')}")
        cols[3].metric("Máximo Histórico", f"{kpis['maximo']:.2f}", f"em {kpis['data_maximo'].strftime('%d/%m/%Y')}")
        cols[4].metric(label="Variação p/ Média", value=f"{kpis['variacao_para_media']:.2f}%", help="Quanto o Ativo A (numerador) precisa variar para o ratio voltar à média.")

    if st.session_state.get('fig_ratio'):
        st.plotly_chart(st.session_state.fig_ratio, use_container_width=True, config={'modeBarButtonsToRemove': ['autoscale']})

st.markdown("---")

# Seção 2: Análise de Insiders
with st.container():
    st.subheader("Radar de Insiders (Movimentações CVM)")
    st.info("Analisa as movimentações de compra e venda de ações feitas por pessoas ligadas à empresa (Controladores, Diretores, etc.), com base nos dados públicos da CVM. Grandes volumes de compra podem indicar confiança na empresa.")
    
    if st.button("Analisar Movimentações de Insiders do Mês", use_container_width=True):
        with st.spinner("Baixando e processando dados da CVM e YFinance... Isso pode levar alguns minutos."):
            dados_insiders = executar_analise_insiders()
        if dados_insiders:
            df_controladores, df_outros, ultimo_mes = dados_insiders
            st.subheader(f"Dados de {ultimo_mes.strftime('%B de %Y')}")
            if not df_controladores.empty:
                st.write("#### Grupo: Controladores e Vinculados")
                fig_vol_ctrl, fig_rel_ctrl = gerar_graficos_insiders_plotly(df_controladores)
                col1_ctrl, col2_ctrl = st.columns(2)
                with col1_ctrl: st.plotly_chart(fig_vol_ctrl, use_container_width=True)
                with col2_ctrl: st.plotly_chart(fig_rel_ctrl, use_container_width=True)
            else:
                st.warning("Não foram encontrados dados de movimentação para Controladores no último mês.")
            
            st.markdown("---")
            
            if not df_outros.empty:
                st.write("#### Grupo: Demais Insiders (Diretores, Conselheiros, etc.)")
                fig_vol_outros, fig_rel_outros = gerar_graficos_insiders_plotly(df_outros)
                col1_outros, col2_outros = st.columns(2)
                with col1_outros: st.plotly_chart(fig_vol_outros, use_container_width=True)
                with col2_outros: st.plotly_chart(fig_rel_outros, use_container_width=True)
            else:
                st.warning("Não foram encontrados dados de movimentação para Demais Insiders no último mês.")
        else:
            st.error("Falha ao processar dados de insiders.")

st.markdown("---")

# Seção 3: Indicador de Amplitude de Mercado
with st.container():
    st.subheader("Raio-X do Mercado (Market Breadth)")
    st.info(
        "Este indicador mostra a porcentagem de ações da B3 negociadas acima da Média Móvel de 200 dias. "
        "É uma ferramenta para medir a saúde interna do mercado.\n\n"
        "- **Acima de 70%:** Pode indicar euforia ou sobrecompra.\n"
        "- **Abaixo de 30%:** Pode indicar pânico ou sobrevenda, geralmente associado a fundos de mercado."
    )

    if st.button("Analisar Amplitude do Mercado (Lento na 1ª vez)", use_container_width=True):
        with st.spinner("Executando análise de amplitude completa... Por favor, aguarde."):
            lista_tickers = obter_tickers_cvm_amplitude()
            if lista_tickers:
                precos = obter_precos_historicos_amplitude(lista_tickers)
                dados_amplitude = calcular_dados_amplitude(precos)
                
                if not dados_amplitude.empty:
                    mediana_amplitude = dados_amplitude.median()
                    st.session_state.mediana_amplitude = mediana_amplitude
                    st.session_state.dados_amplitude = dados_amplitude
                    st.session_state.fig_amplitude = gerar_grafico_amplitude(dados_amplitude, mediana_amplitude)
                    st.session_state.fig_dist_amplitude = gerar_grafico_distribuicao_amplitude(dados_amplitude, mediana_amplitude)
                else:
                    st.session_state.fig_amplitude = None
                    st.session_state.fig_dist_amplitude = None
                    st.error("Não foi possível gerar os gráficos pois os dados de amplitude não puderam ser calculados.")
            else:
                st.session_state.fig_amplitude = None
                st.session_state.fig_dist_amplitude = None

    if 'fig_amplitude' in st.session_state and st.session_state.fig_amplitude is not None:
        st.markdown("---")
        col_metrica1, col_metrica2, _ = st.columns([0.3, 0.3, 0.4])
        valor_atual = st.session_state.dados_amplitude.iloc[-1]
        mediana_valor = st.session_state.mediana_amplitude
        col_metrica1.metric("Valor Atual do Indicador", f"{valor_atual:.1f}%")
        col_metrica2.metric("Mediana Histórica (desde 2014)", f"{mediana_valor:.1f}%")
        st.markdown("---")

        col1, col2 = st.columns([0.6, 0.4])
        with col1:
            st.plotly_chart(st.session_state.fig_amplitude, use_container_width=True)
        with col2:
            st.plotly_chart(st.session_state.fig_dist_amplitude, use_container_width=True)
