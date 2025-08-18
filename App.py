import streamlit as st
from datetime import datetime

# --- CONFIGURAÇÃO GERAL DA PÁGINA ---
st.set_page_config(
    layout="wide",
    page_title="MOBBT",
    page_icon="📊"
)

# --- CONTEÚDO DA PÁGINA PRINCIPAL ---
st.title("MOBBT - Monitor de Mercado Brasileiro")
st.caption(f"Última atualização: {datetime.now().strftime('%d/%m/%Y %H:%M')}")

st.markdown("---")

st.header("Bem-vindo ao seu Dashboard de Investimentos!")
st.info(
    """
    Utilize o menu de navegação na barra lateral à esquerda para explorar as diferentes análises disponíveis.
    
    **Páginas Disponíveis:**
    - **NTN-Bs:** Análise detalhada dos títulos Tesouro IPCA+.
    - **Curva de Juros:** Estrutura a Termo da Taxa de Juros (ETTJ) com base nos títulos prefixados.
    - **Crédito Privado:** Acompanhamento de indicadores de crédito privado como o IDEX JGP.
    - **Econômicos BR:** Indicadores macroeconômicos do Brasil via Banco Central.
    - **Commodities:** Painel completo com preços e variações de diversas commodities.
    - **Internacional:** Principais indicadores econômicos dos EUA via FRED.
    - **Ações BR:** Ferramentas para análise de ações, incluindo Ratio, Insiders e Amplitude de Mercado.
    """
)

st.success("Projeto refatorado para uma estrutura de múltiplas páginas para facilitar a manutenção e o desenvolvimento!")
