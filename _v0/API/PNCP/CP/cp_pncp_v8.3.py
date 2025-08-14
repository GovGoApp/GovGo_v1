import streamlit as st
import pandas as pd
import requests
import re
import io
from datetime import datetime, date
from dateutil.relativedelta import relativedelta
import locale
from openai import OpenAI

# Configuração da API da OpenAI – substitua pela sua chave real
client = OpenAI(
  #organization='org-2YkkE6qieHaCmPXsYoFecOsw',
  api_key = "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"  
)

# Define a localidade para o Brasil
locale.setlocale(locale.LC_ALL, 'pt_BR.UTF-8')

# CSS personalizado
st.markdown("""
<style>
    /* 1) Remover espaço superior do título e do subheader da sidebar */
    .block-container, .sidebar .block-container {
        padding-top: 0 !important;
        margin-top: 0 !important;
    }
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
        font-size: 0.2rem !important;
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
    .stButton button[aria-label="Buscar Processos"] {
        background-color: #ffffff !important;
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
    .sidebar .block-container h1, 
    .sidebar .block-container h2,
    .sidebar .block-container h3,
    .sidebar .block-container h4 {
        font-size: 1em;
    }
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
    /* Estilo para os cards */
    .processo-card {
        background-color: #f5f5f5; 
        padding: 10px; 
        border-radius: 5px; 
        margin-bottom: 15px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
    }
    .keywords-card {
        background-color: #f0f7ff; 
        padding: 10px; 
        border-radius: 5px; 
        margin-bottom: 15px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
        height: 100%;
    }
    .summary-card {
        background-color: #f0fff0; 
        padding: 10px; 
        border-radius: 5px; 
        margin-bottom: 15px;
        box-shadow: 2px 2px 5px rgba(0,0,0,0.1);
        height: 100%;
    }
    .arquivo-item {
        display: flex;
        align-items: center;
        margin: 5px 0;
    }
    .arquivo-link {
        flex: 1;
    }
    .doc-section {
        margin-top: 8px;
        border-top: 1px solid #ddd;
        padding-top: 8px;
    }
    .doc-list {
        list-style-type: none;
        padding-left: 0;
        margin-top: 5px;
    }
    .doc-item {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 5px;
        padding: 4px 0;
        border-bottom: 1px dotted #ddd;
    }
</style>
""", unsafe_allow_html=True)

# ============================================
# Funções auxiliares
# ============================================

def fetch_processos(data_inicial, data_final, codigo_modalidade, tamanho_pagina, ufs):
    base_url = 'https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao'
    processos = []
    for uf in ufs:
        url_inicial = (f"{base_url}?dataInicial={data_inicial}&dataFinal={data_final}"
                       f"&codigoModalidadeContratacao={codigo_modalidade}&uf={uf}"
                       f"&tamanhoPagina={tamanho_pagina}&pagina=1")
        response_inicial = requests.get(url_inicial)
        if response_inicial.status_code == 200:
            json_inicial = response_inicial.json()
            total_paginas = json_inicial.get("totalPaginas", 1)
            for pagina in range(1, total_paginas + 1):
                url = (f"{base_url}?dataInicial={data_inicial}&dataFinal={data_final}"
                       f"&codigoModalidadeContratacao={codigo_modalidade}&uf={uf}"
                       f"&tamanhoPagina={tamanho_pagina}&pagina={pagina}")
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
    if isinstance(s, str):
        return re.sub(r'[\x00-\x1F]+', ' ', s)
    return s

def generate_keywords(text):
    prompt = f"""
Resuma o conteúdo a seguir em 5 a 10 tópicos de palavras-chave separados por ponto e vírgula, sem numeração.
Comece com o título, o tipo e o propósito, e depois destaque os principais tópicos abordados.
Use apenas palavras-chave. Limite: 200 caracteres.
Texto: {text}
Exemplo: "Edital; Pregão Eletrônico; Aquisição de Equipamentos; Especificações Técnicas; Critérios de Avaliação"
"""
    try:
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Você é um assistente que resume textos em palavras-chave."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=100
        )
        keywords = completion.choices[0].message.content.strip()
        return keywords
    except Exception as e:
        return "Erro ao gerar palavras-chave"

def format_keywords(keywords_str):
    if not keywords_str:
        return "N/D"
    keywords = [kw.strip() for kw in keywords_str.split(";") if kw.strip()]
    chips = " ".join([f"<span class='keyword-chip'>{kw}</span>" for kw in keywords])
    return chips

def fetch_documentos(cnpj, ano, sequencial):
    base_url = "https://pncp.gov.br/api/pncp/v1"
    url = f"{base_url}/orgaos/{cnpj}/compras/{ano}/{sequencial}/arquivos"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json()  # Retorna a lista de documentos
    else:
        st.error(f"Erro na consulta de documentos para {cnpj}/{ano}/{sequencial}: {response.status_code} - {response.text}")
        return []
#XERXES\API\PNCP\CP\cp_pncp_v8.3.py
def summarize_document(doc_url):
    prompt = f"Por favor, leia o conteúdo do documento disponível no seguinte link: {doc_url}. Resuma o conteúdo detalhadamente em tópicos e parágrafos, destacando os principais pontos."
    try:
        completion = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "Você é um assistente que sumariza documentos."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.5,
            max_tokens=300
        )
        summary = completion.choices[0].message.content.strip()
        return summary
    except Exception as e:
        return f"Erro ao sumarizar: {str(e)}"

def process_data(processos):
    df = pd.json_normalize(processos)
    if 'objetoCompra' in df.columns:
        df.rename(columns={'objetoCompra': 'objeto'}, inplace=True)
    if 'valorTotalEstimado' in df.columns:
        df['valorTotalEstimado'] = pd.to_numeric(df['valorTotalEstimado'], errors='coerce')
    if 'dataAberturaProposta' in df.columns:
        df['dataAberturaProposta'] = pd.to_datetime(df['dataAberturaProposta'], format='%Y-%m-%dT%H:%M:%S', errors='coerce')
    if 'dataInclusao' in df.columns:
        df['dataInclusao'] = pd.to_datetime(df['dataInclusao'], format='%Y-%m-%dT%H:%M:%S', errors='coerce')
    if 'dataEncerramentoProposta' in df.columns:
        df['dataEncerramentoProposta'] = pd.to_datetime(df['dataEncerramentoProposta'], format='%Y-%m-%dT%H:%M:%S', errors='coerce')
    for col in df.select_dtypes(include='object').columns:
        df[col] = df[col].apply(clean_illegal_chars)
    
    # Não gera mais palavras-chave automaticamente
    # Serão geradas apenas quando o botão for clicado
    
    def get_documentos(row):
        cnpj = row.get("orgaoEntidade.cnpj", "")
        ano = row.get("anoCompra", "")
        sequencial = row.get("sequencialCompra", "")
        if cnpj and ano and sequencial:
            docs = fetch_documentos(cnpj, ano, sequencial)
            if docs:
                return " | ".join([doc.get("titulo", "Documento") for doc in docs])
        return ""
    df["documentos"] = df.apply(get_documentos, axis=1)
    return df

def to_excel(df_all, df_filtered):
    output = io.BytesIO()
    writer = pd.ExcelWriter(output, engine='xlsxwriter')
    df_all.to_excel(writer, sheet_name='Todos', index=False)
    df_filtered.to_excel(writer, sheet_name='Filtrados', index=False)
    writer.close()
    processed_data = output.getvalue()
    return processed_data

def render_card(row, idx):
    orgao = row.get("orgaoEntidade.razaoSocial", "N/D")
    uf = row.get("unidadeOrgao.ufSigla", "N/D")
    data_inclusao = row.get("dataInclusao", "N/D")
    processo = row.get("processo", "N/D")
    objeto = row.get("objeto", "N/D")  # Adicionado o campo objeto
    valor_estimado = row.get("valorTotalEstimado", "N/D")
    if isinstance(valor_estimado, (int, float)):
        valor_estimado = locale.currency(valor_estimado, grouping=True)
    else:
        valor_estimado = "N/D"
    cnpj = row.get("orgaoEntidade.cnpj", "")
    ano = row.get("anoCompra", "")
    sequencial = row.get("sequencialCompra", "")

    # Criamos duas colunas: para o card principal + documentos e para cards de keywords/sumário
    col1, col2 = st.columns([3, 2])

    # Coluna 1: Card principal do processo
    with col1:
        st.markdown(f"""
        <div class="processo-card">
          <h4 style="margin-bottom: 5px;">{orgao}</h4>
          <p style="margin: 2px 0;"><strong>UF:</strong> {uf}</p>
          <p style="margin: 2px 0;"><strong>Data Inclusão:</strong> {data_inclusao}</p>
          <p style="margin: 2px 0;"><strong>Processo:</strong> {processo}</p>
          <p style="margin: 2px 0;"><strong>Objeto:</strong> {objeto}</p>
          <p style="margin: 2px 0;"><strong>Valor Estimado:</strong> {valor_estimado}</p>
        """, unsafe_allow_html=True)
        
        # Documentos dentro do card
        docs = []
        if cnpj and ano and sequencial:
            docs = fetch_documentos(cnpj, ano, sequencial)
            if docs:
                st.markdown("<div class='doc-section'><strong>Documentos:</strong></div>", unsafe_allow_html=True)
                st.markdown("<ul class='doc-list'>", unsafe_allow_html=True)
                
                for i, doc in enumerate(docs):
                    doc_id = f"doc_{idx}_{i}"
                    titulo = doc.get("titulo", "Documento")
                    doc_url = doc.get("url", "#")
                    
                    # Layout de cada item de documento como uma linha na lista
                    st.markdown(f"""
                    <li class='doc-item'>
                        <span class='arquivo-link'><a href="{doc_url}" target="_blank">{titulo}</a></span>
                    </li>
                    """, unsafe_allow_html=True)
                    
                    # Botão de sumarizar para cada documento (com chave única)
                    if st.button("Sumarizar", key=f"sum_btn_proc_{idx}_doc_{i}"):
                        # Armazena o índice do documento para ser usado pela coluna 2
                        st.session_state[f"summarize_doc_{idx}_{i}"] = True
                        st.experimental_rerun()
                
                st.markdown("</ul>", unsafe_allow_html=True)
        
        # Botão para gerar palavras-chave (com chave única)
        if st.button("Gerar Palavras-Chave", key=f"genkw_btn_proc_{idx}"):
            if objeto and isinstance(objeto, str):
                keywords = generate_keywords(objeto)
                # Armazena as palavras-chave para serem exibidas na coluna 2
                st.session_state[f"keywords_{idx}"] = keywords
                st.experimental_rerun()
            else:
                st.error("Objeto não disponível para gerar palavras-chave")
        
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Coluna 2: Cards de palavras-chave e sumário
    with col2:
        # Card de palavras-chave (aparece se o botão foi clicado)
        if f"keywords_{idx}" in st.session_state:
            keywords = st.session_state[f"keywords_{idx}"]
            st.markdown(f"""
            <div class="keywords-card">
              <h5>Palavras-Chave</h5>
              {format_keywords(keywords)}
            </div>
            """, unsafe_allow_html=True)
        
        # Cards de sumários (aparece quando um documento é sumarizado)
        if docs:
            for i, doc in enumerate(docs):
                doc_id = f"doc_{idx}_{i}"
                if f"summarize_doc_{idx}_{i}" in st.session_state:
                    # Se o botão de sumarizar foi clicado
                    titulo = doc.get("titulo", "Documento")
                    doc_url = doc.get("url", "#")
                    summary_key = f"summary_doc_{idx}_{i}"
                    
                    if summary_key not in st.session_state:
                        with st.spinner("Sumarizando..."):
                            summary = summarize_document(doc_url)
                            st.session_state[summary_key] = summary
                    
                    st.markdown(f"""
                    <div class="summary-card">
                      <h5>Sumário: {titulo}</h5>
                      <p>{st.session_state[summary_key]}</p>
                    </div>
                    """, unsafe_allow_html=True)

# ============================================
# Interface do Aplicativo com Streamlit
# ============================================
st.title("Visualização de Processos - PNCP")

if 'keywords' not in st.session_state:
    st.session_state.keywords = []
if 'keyword_input' not in st.session_state:
    st.session_state.keyword_input = ""

def add_keywords():
    text = st.session_state.keyword_input.strip()
    if text:
        splitted = re.split(r'[\s,;]+', text)
        splitted = [s for s in splitted if s]
        for kw in splitted:
            if kw.lower() not in [x.lower() for x in st.session_state.keywords]:
                st.session_state.keywords.append(kw)
    st.session_state.keyword_input = ""

def remove_keyword(index):
    st.session_state.keywords.pop(index)
    st.experimental_rerun()

st.sidebar.text_input(
    "Digite palavras-chave",
    placeholder="Aperte Enter para inserir",
    key="keyword_input",
    on_change=add_keywords
)

if st.session_state.keywords:
    chips_container = st.sidebar.container()
    for i in range(0, len(st.session_state.keywords), 10):
        batch = st.session_state.keywords[i:i+10]
        cols = chips_container.columns([0.1] * len(batch))
        for j, kw in enumerate(batch):
            idx = i + j
            with cols[j]:
                # Use um prefixo diferente para os botões de filtro para evitar conflito com outros botões
                if st.button(f"{kw} ×", key=f"filter_kw_btn_{idx}", use_container_width=False):
                    remove_keyword(idx)
                    
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
modalidade_escolhida = st.sidebar.selectbox(
    "Selecione a Modalidade",
    list(modalidades.keys()),
    index=5
)
codigo_modalidade = modalidades[modalidade_escolhida]
tamanho_pagina = st.sidebar.number_input("Tamanho da Página", value=50, step=10)

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
ufs_selecionadas = st.sidebar.multiselect(
    "Selecione as UFs",
    list(ufs_brasil.keys()),
    default=["ES", "SP"]
)
ufs_input = ",".join(ufs_selecionadas)
ufs = [uf.strip() for uf in ufs_input.split(",") if uf.strip()]

buscar_processos = st.sidebar.button(
    label="Buscar Processos",
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

if 'processos' in st.session_state:
    df_all = process_data(st.session_state['processos'])
    
    # Se não houver palavras-chave ou o campo objeto não existir, mostrar todos os processos
    if not st.session_state.keywords or "objeto" not in df_all.columns:
        df_filtered = df_all.copy()
    else:
        # Se houver palavras-chave, filtra os processos
        filtro = pd.Series([False]*len(df_all))
        for kw in st.session_state.keywords:
            filtro |= df_all["objeto"].str.lower().str.contains(kw.lower(), na=False)
        df_filtered = df_all[filtro]

    st.subheader("Filtros Ativos")
    if st.session_state.keywords:
        st.write("Filtrando pelo campo 'objeto' contendo alguma das palavras:")
        keywords_chips = "<div style='display: flex; flex-wrap: wrap; gap: 5px;'>"
        for kw in st.session_state.keywords:
            keywords_chips += f"<div class='keyword-chip'>{kw}</div>"
        keywords_chips += "</div>"
        st.markdown(keywords_chips, unsafe_allow_html=True)
    else:
        st.write("Nenhuma palavra-chave definida. Mostrando todos os processos.")

    st.subheader("Processos")
    if df_filtered.empty:
        st.write("Nenhum processo encontrado com os filtros aplicados.")
    else:
        for idx, (_, row) in enumerate(df_filtered.iterrows()):
            render_card(row, idx)

    excel_data = to_excel(df_all, df_filtered)
    st.download_button(
        label="Download Excel",
        data=excel_data,
        file_name=f"licitacoes_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )