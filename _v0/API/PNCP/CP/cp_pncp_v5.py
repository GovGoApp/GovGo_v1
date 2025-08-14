import streamlit as st
import pandas as pd
import requests
import re
import io
from datetime import datetime, date
from dateutil.relativedelta import relativedelta

# ============================================
# Funções auxiliares
# ============================================

def fetch_processos(data_inicial, data_final, codigo_modalidade, tamanho_pagina, ufs):
    """
    Realiza a consulta na API PNCP para cada UF informada.
    Para cada UF, obtém o total de páginas e itera por todas elas,
    coletando o dicionário completo de cada processo.
    """
    base_url = 'https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao'
    processos = []
    for uf in ufs:
        url_inicial = (
            f"{base_url}?dataInicial={data_inicial}&dataFinal={data_final}"
            f"&codigoModalidadeContratacao={codigo_modalidade}&uf={uf}"
            f"&tamanhoPagina={tamanho_pagina}&pagina=1"
        )
        response_inicial = requests.get(url_inicial)
        if response_inicial.status_code == 200:
            json_inicial = response_inicial.json()
            total_paginas = json_inicial.get("totalPaginas", 1)
            for pagina in range(1, total_paginas + 1):
                url = (
                    f"{base_url}?dataInicial={data_inicial}&dataFinal={data_final}"
                    f"&codigoModalidadeContratacao={codigo_modalidade}&uf={uf}"
                    f"&tamanhoPagina={tamanho_pagina}&pagina={pagina}"
                )
                response = requests.get(url)
                if response.status_code == 200:
                    dados = response.json().get("data", [])
                    processos.extend(dados)
                else:
                    st.error(f"Erro na requisição para {url}: {response.status_code} - {response.text}")
        else:
            st.error(f"Erro na requisição para {url_inicial}: {response_inicial.status_code} - {response_inicial.text}")
    return processos

def clean_illegal_chars(s):
    """
    Remove caracteres de controle (ASCII < 32) de uma string.
    """
    if isinstance(s, str):
        return re.sub(r'[\x00-\x1F]+', ' ', s)
    return s

def process_data(processos):
    """
    Converte a lista de processos (dicionários) em DataFrame, realiza
    a normalização, renomeia a coluna 'objetoCompra' para 'objeto' (se existir),
    converte tipos e realiza a limpeza dos dados.
    """
    df = pd.json_normalize(processos)
    if 'objetoCompra' in df.columns:
        df.rename(columns={'objetoCompra': 'objeto'}, inplace=True)
    # Conversões de tipo
    if 'valorTotalEstimado' in df.columns:
        df['valorTotalEstimado'] = pd.to_numeric(df['valorTotalEstimado'], errors='coerce')
    if 'dataAberturaProposta' in df.columns:
        df['dataAberturaProposta'] = pd.to_datetime(df['dataAberturaProposta'], format='%Y-%m-%dT%H:%M:%S', errors='coerce')
    if 'dataInclusao' in df.columns:
        df['dataInclusao'] = pd.to_datetime(df['dataInclusao'], format='%Y-%m-%dT%H:%M:%S', errors='coerce')
    if 'dataEncerramentoProposta' in df.columns:
        df['dataEncerramentoProposta'] = pd.to_datetime(df['dataEncerramentoProposta'], format='%Y-%m-%dT%H:%M:%S', errors='coerce')
    # Limpeza de caracteres em colunas de texto
    for col in df.select_dtypes(include='object').columns:
        df[col] = df[col].apply(clean_illegal_chars)
    return df

def to_excel(df_all, df_filtered):
    """
    Gera um arquivo Excel em memória contendo duas planilhas:
      - 'Todos' com todos os processos coletados
      - 'Filtrados' com os processos após aplicação dos filtros.
    """
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df_all.to_excel(writer, sheet_name='Todos', index=False)
    df_filtered.to_excel(writer, sheet_name='Filtrados', index=False)
    writer.close()
    processed_data = output.getvalue()
    return processed_data


def render_card(row):
    """
    Renderiza um "card" HTML para exibir os dados principais de um processo.
    """
    orgao = row.get("orgaoEntidade.razaoSocial", "N/D")
    uf = row.get("unidadeOrgao.ufSigla", "N/D")
    data_inclusao = row.get("dataInclusao", "N/D")
    processo = row.get("processo", "N/D")
    objeto = row.get("objeto", "N/D")
    valor_estimado = row.get("valorTotalEstimado", "N/D")
    
    card_html = f"""
    <div style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; margin-bottom: 10px;
                box-shadow: 2px 2px 5px rgba(0,0,0,0.1);">
      <h4 style="margin-bottom: 5px;">{orgao}</h4>
      <p style="margin: 2px 0;"><strong>UF:</strong> {uf}</p>
      <p style="margin: 2px 0;"><strong>Data Inclusão:</strong> {data_inclusao}</p>
      <p style="margin: 2px 0;"><strong>Processo:</strong> {processo}</p>
      <p style="margin: 2px 0;"><strong>Objeto:</strong> {objeto}</p>
      <p style="margin: 2px 0;"><strong>Valor Estimado:</strong> {valor_estimado}</p>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)

# ============================================
# Interface do Aplicativo com Streamlit
# ============================================

st.title("Visualização de Processos - PNCP")

# ------------------------------
# Parâmetros de Consulta na Sidebar
# ------------------------------
st.sidebar.header("Parâmetros de Consulta")

# Datas: exibidas em formato dd/mm/yyyy e convertidas para yyyymmdd para a API
data_inicial_date = st.sidebar.date_input("Data Inicial (dd/mm/yyyy)", value=date(2025, 1, 1))
data_final_date   = st.sidebar.date_input("Data Final (dd/mm/yyyy)", value=date(2025, 3, 31))
data_inicial_str = data_inicial_date.strftime("%Y%m%d")
data_final_str   = data_final_date.strftime("%Y%m%d")

codigo_modalidade = st.sidebar.number_input("Código Modalidade", value=6, step=1)
tamanho_pagina = st.sidebar.number_input("Tamanho da Página", value=50, step=10)
ufs_input = st.sidebar.text_input("UFs (separadas por vírgula)", "ES,SP")
ufs = [uf.strip() for uf in ufs_input.split(",") if uf.strip()]

# ------------------------------
# Palavras-chave em formato "chips"
# ------------------------------
if 'keywords' not in st.session_state:
    st.session_state.keywords = []

if 'keyword_input' not in st.session_state:
    st.session_state.keyword_input = ""

def add_keywords():
    """Callback para adicionar as novas palavras-digitadas ao pressionar Enter."""
    text = st.session_state.keyword_input.strip()
    if text:
        # Divide usando espaço, vírgula ou ponto-e-vírgula
        splitted = re.split(r'[\s,;]+', text)
        splitted = [s for s in splitted if s]  # remove strings vazias
        for kw in splitted:
            # Evita duplicar a palavra se já existir (case-insensitive)
            if kw.lower() not in [x.lower() for x in st.session_state.keywords]:
                st.session_state.keywords.append(kw)
    # Limpa o campo de entrada
    st.session_state.keyword_input = ""

st.sidebar.subheader("Palavras-chave")

# Campo de texto com placeholder e callback "on_change"
st.sidebar.text_input(
    "Digite palavras-chave (use espaço, vírgula ou ponto-e-vírgula)",
    placeholder="Aperte Enter para inserir",
    key="keyword_input",
    on_change=add_keywords
)

# Exibe cada palavra como um "chip" com botão para remover
chip_container = st.sidebar.container()
for i, kw in enumerate(st.session_state.keywords):
    cols = chip_container.columns([0.8, 0.2])
    with cols[0]:
        st.write(f"• {kw}")
    with cols[1]:
        if st.button("x", key=f"remove_kw_{i}"):
            st.session_state.keywords.pop(i)
            st.experimental_rerun()

# ------------------------------
# Botão para buscar os processos via API
# ------------------------------
if st.sidebar.button("Buscar Processos"):
    with st.spinner("Buscando processos via API..."):
        processos = fetch_processos(data_inicial_str, data_final_str, codigo_modalidade, tamanho_pagina, ufs)
        if processos:
            st.session_state['processos'] = processos
            st.success(f"Foram coletados {len(processos)} processos.")
        else:
            st.error("Nenhum processo foi coletado.")

# ------------------------------
# Exibição dos Processos e Download do Excel
# ------------------------------
if 'processos' in st.session_state:
    df_all = process_data(st.session_state['processos'])
    
    # Layout em duas colunas: principal (cards) e uma para exibir apenas o texto do filtro
    col_main, col_filters = st.columns([3, 1])
    
    with col_filters:
        st.subheader("Filtros Ativos")
        # Mostra a lista de palavras-chave que serão usadas no filtro
        if st.session_state.keywords:
            st.write("Filtrando pelo campo 'objeto' contendo alguma das palavras:")
            for kw in st.session_state.keywords:
                st.write(f"• {kw}")
        else:
            st.write("Nenhuma palavra-chave definida.")
    
    # Filtra os registros com base na coluna "objeto" e nas palavras-chave definidas
    if "objeto" in df_all.columns and st.session_state.keywords:
        # Monta uma expressão que exibe o registro se contiver ao menos uma das keywords
        # (operador OR). Para isso, criamos um filtro cumulativo
        filtro = pd.Series([False]*len(df_all))
        for kw in st.session_state.keywords:
            filtro |= df_all["objeto"].str.lower().str.contains(kw.lower(), na=False)
        df_filtered = df_all[filtro]
    else:
        df_filtered = df_all.copy()
    
    with col_main:
        st.subheader("Processos")
        if df_filtered.empty:
            st.write("Nenhum processo encontrado com os filtros aplicados.")
        else:
            for _, row in df_filtered.iterrows():
                render_card(row)
    
    # Botão para download do Excel com os dados completos e filtrados
    excel_data = to_excel(df_all, df_filtered)
    st.download_button(
        label="Download Excel",
        data=excel_data,
        file_name=f"licitacoes_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
