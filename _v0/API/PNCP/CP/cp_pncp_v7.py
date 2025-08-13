import streamlit as st
import pandas as pd
import requests
import re
import io
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import locale

# Define a localidade para o Brasil
locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

# Ajusta o tamanho da fonte e espaçamento com CSS personalizado
st.markdown("""
<style>
    /* 1) Remover espaço superior do título e do subheader da sidebar */
    .block-container, .sidebar .block-container {
        padding-top: 0 !important;
        margin-top: 0 !important;
    }
    /* Força o subheader na sidebar a não ter margem/padding extra */
    .sidebar .block-container h2 {
        margin-top: 0 !important;
        padding-top: 0 !important;
    }

            
    div[data-testid="stHorizontalBlock"] {
        flex-wrap: wrap;
        gap: 2px;
        margin: 0;
        padding: 0;
    }
    
    div[data-testid="column"] {
        min-width: auto !important;
        width: auto !important;
        flex: 0 1 auto !important;
        padding: 0 !important;
    }
    
     /* 2) Diminui a fonte dos chips para 0.2rem */
    .stButton button.chip-button {
        font-size: 0.2rem !important;  /* Menor que a fonte do filtro */
        padding: 0px 4px !important;
        border-radius: 12px !important;
        background-color: #e0e0e0 !important;
        color: #333 !important;
        border: none !important;
        margin: 2px !important;
        height: 14px !important;
        line-height: 14px !important;
        white-space: nowrap !important;
    }
            
    /* 4) Botão "Buscar Processos" maior e cor diferente */
    /* Usa o atributo aria-label para diferenciar */
    .stButton button[aria-label="Buscar Processos"] {
        background-color: #ffffff !important; /* Cor laranja */
        color: #f7951e !important;
        font-size: 1.5rem !important;
        padding: 8px 16px !important;
        border-radius: 8px !important;
        margin-top: 0.5rem !important;
        height: auto !important;
        line-height: normal !important;
        border: none !important;
        box-shadow: none !important;
    }
    
    /* Reduz tamanho dos títulos na sidebar */
    .sidebar .block-container h1, 
    .sidebar .block-container h2,
    .sidebar .block-container h3,
    .sidebar .block-container h4 {
        font-size: 1em;
    }
    
    /* Reduz tamanho do espaçamento entre elementos */
    .sidebar .element-container {
        margin-top: 0.1rem;
        margin-bottom: 0.1rem;
    }
    
    /* Estilo para chips no filtro ativo */
    .keyword-chip {
        display: inline-block;
        background: #e0e0e0;
        border-radius: 16px;
        padding: 1px 8px;
        margin: 1px;
        font-size: 0.7rem;
        line-height: 20px;
        white-space: nowrap;
    }
</style>
""", unsafe_allow_html=True)

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

    # Formata o valor estimado como moeda brasileira
    if isinstance(valor_estimado, (int, float)):
        valor_estimado = locale.currency(valor_estimado, grouping=True)
    else:
        valor_estimado = "N/D"
    
    
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
#st.sidebar.header("Parâmetros de Consulta")

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

def remove_keyword(index):
    st.session_state.keywords.pop(index)
    st.experimental_rerun()

#st.sidebar.subheader("Palavras-chave")

# Campo de texto com placeholder e callback "on_change"
st.sidebar.text_input(
    "Digite palavras-chave",
    placeholder="Aperte Enter para inserir",
    key="keyword_input",
    on_change=add_keywords
)

# NOVA IMPLEMENTAÇÃO: Exibe as palavras-chave como chips em fluxo horizontal
if st.session_state.keywords:
    # Usa um container que permita flex wrap automático
    chips_container = st.sidebar.container()
    
    # Criamos várias linhas com no máximo 10 colunas por linha
    for i in range(0, len(st.session_state.keywords), 10):
        # Pega apenas até 10 keywords por linha
        batch = st.session_state.keywords[i:i+10]
        cols = chips_container.columns([0.1] * len(batch))
        
        # Coloca um chip em cada coluna desta linha
        for j, kw in enumerate(batch):
            idx = i + j
            with cols[j]:
                if st.button(f"{kw} ×", key=f"kw_btn_{idx}", use_container_width=False):
                    remove_keyword(idx)
                

# Datas: exibidas em formato dd/mm/yyyy e convertidas para yyyymmdd para a API
data_inicial_date = st.sidebar.date_input("Data Inicial (dd/mm/yyyy)", value=date(datetime.now().year, datetime.now().month, 1), format="DD/MM/YYYY")
data_final_date = st.sidebar.date_input("Data Final (dd/mm/yyyy)", value=datetime.now(), format="DD/MM/YYYY")
data_inicial_str = data_inicial_date.strftime("%Y%m%d")
data_final_str = data_final_date.strftime("%Y%m%d")

modalidades = {
    "1 - Leilão - Eletrônico": 1,
    "2 - Diálogo Competitivo": 2,
    "3 - Concurso": 3,
    "4 - Concorrência - Eletrônica": 4,
    "5 - Concorrência - Presencial": 5,
    "6 - Pregão - Eletrônico": 6,
    "7 - Pregão - Presencial": 7,
    "8 - Dispensa de Licitação": 8,
    "9 - Inexigibilidade": 9,
    "10 - Manifestação de Interesse": 10,
    "11 - Pré-qualificação": 11,
    "12 - Credenciamento": 12,
    "13 - Leilão - Presencial": 13
}

#codigo_modalidade = st.sidebar.number_input("Código Modalidade", value=6, step=1)

modalidade_escolhida = st.sidebar.selectbox(
    "Selecione a Modalidade",
    list(modalidades.keys()),
    index=5  # 6 - Pregão - Eletrônico como padrão (índice 5 na lista acima)
)

# Captura o código numérico para uso na API
codigo_modalidade = modalidades[modalidade_escolhida]

tamanho_pagina = st.sidebar.number_input("Tamanho da Página", value=50, step=10)

# Dicionário completo UFs com Nome e Sigla
ufs_brasil = {
    "AL": "Alagoas",
    "AM": "Amazonas",
    "AP": "Amapá",
    "BA": "Bahia",
    "CE": "Ceará",
    "DF": "Distrito Federal",
    "ES": "Espírito Santo",
    "GO": "Goiás",
    "MA": "Maranhão",
    "MG": "Minas Gerais",
    "MS": "Mato Grosso do Sul",
    "MT": "Mato Grosso",
    "PA": "Pará",
    "PB": "Paraíba",
    "PE": "Pernambuco",
    "PI": "Piauí",
    "PR": "Paraná",
    "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte",
    "RO": "Rondônia",
    "RR": "Roraima",
    "RS": "Rio Grande do Sul",
    "SC": "Santa Catarina",
    "SE": "Sergipe",
    "SP": "São Paulo",
    "TO": "Tocantins"
}

# Multi-select para escolher siglas
ufs_selecionadas = st.sidebar.multiselect(
    "Selecione as UFs",
    list(ufs_brasil.keys()),
    default=["ES", "SP"]
)

# Converte a lista de siglas selecionadas em string (separada por vírgulas)
ufs_input = ",".join(ufs_selecionadas)

# Em seguida, usamos ufs_input para repassar à API
ufs = [uf.strip() for uf in ufs_input.split(",") if uf.strip()]

#poderes = {
#    "L": "Legislativo",
#    "E": "Executivo",
#    "J": "Judiciário",
#    "N": "Não se aplica"
#}

##esferas = {
#    "F": "Federal",
#    "E": "Estadual",
#    "M": "Municipal",
#    "D": "Distrital",
#    "N": "Não se aplica"
#}

#poderes_selecionados = st.sidebar.multiselect(
#    "Selecione os Poderes",
#    list(poderes.keys()),
#    default=list(poderes.keys())
#)

#esferas_selecionadas = st.sidebar.multiselect(
#    "Selecione as Esferas",
#    list(esferas.keys()),
#    default=list(esferas.keys())
#)


# ------------------------------
# Botão para buscar os processos via API
# ------------------------------

buscar_processos = st.sidebar.button(
    label="Buscar Processos",
    #type="primary",
    use_container_width=True
)

if buscar_processos:
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
    
    # A partir daqui, usamos df_filtered e não alteramos df_all
    df_filtered = df_all.copy()

    # Filtro pelo poder
    #if "orgaoEntidade.poderId" in df_filtered.columns:
    #    poderes_siglas = [poderes[p] for p in poderes_selecionados]
    #    df_filtered = df_filtered[df_filtered["orgaoEntidade.poderId"].isin(poderes_siglas)]

    # Filtro pela esfera
    #if "orgaoEntidade.esferaId" in df_filtered.columns:
    #    esferas_siglas = [esferas[e] for e in esferas_selecionadas]
    #    df_filtered = df_filtered[df_filtered["orgaoEntidade.esferaId"].isin(esferas_siglas)]

    # Agora exibe "Filtros Ativos" abaixo do bloco principal
    st.subheader("Filtros Ativos")
    # Mostra a lista de palavras-chave
    if st.session_state.keywords:
        st.write("Filtrando pelo campo 'objeto' contendo alguma das palavras:")
        keywords_chips = "<div style='display: flex; flex-wrap: wrap; gap: 5px;'>"
        for kw in st.session_state.keywords:
            keywords_chips += f"<div class='keyword-chip'>{kw}</div>"
        keywords_chips += "</div>"
        st.markdown(keywords_chips, unsafe_allow_html=True)
    else:
        st.write("Nenhuma palavra-chave definida.")

    # Bloco principal: Exibição dos cards
    st.subheader("Processos")
    # Filtramos antes de exibir
    if "objeto" in df_all.columns and st.session_state.keywords:
        filtro = pd.Series([False]*len(df_all))
        for kw in st.session_state.keywords:
            filtro |= df_all["objeto"].str.lower().str.contains(kw.lower(), na=False)
        df_filtered = df_all[filtro]
    else:
        df_filtered = df_all.copy()

    if df_filtered.empty:
        st.write("Nenhum processo encontrado com os filtros aplicados.")
    else:
        for _, row in df_filtered.iterrows():
            render_card(row)


    # Botão para download do Excel com dados completos e filtrados
    excel_data = to_excel(df_all, df_filtered)
    st.download_button(
        label="Download Excel",
        data=excel_data,
        file_name=f"licitacoes_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )