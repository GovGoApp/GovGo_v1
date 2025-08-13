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
client = OpenAI(api_key="YOUR_API_KEY_HERE")

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

def summarize_document(doc_url):
    """
    Envia o link do documento para a API da OpenAI e retorna um sumário.
    """
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

def render_document(doc):
    """
    Renderiza cada documento com seu link e um botão para sumarização.
    Ao clicar em "Sumarizar", o link é enviado à OpenAI para gerar o sumário.
    Enquanto a sumarização ocorre, é exibido um indicador de progresso.
    Após, um expander com o sumário aparece.
    """
    titulo = doc.get("titulo", "Documento")
    doc_url = doc.get("url", "#")
    st.markdown(f'<a href="{doc_url}" target="_blank">{titulo}</a>', unsafe_allow_html=True)
    summary_key = f"summary_{hash(doc_url)}"
    if summary_key not in st.session_state:
        if st.button("Sumarizar", key=f"sum_btn_{doc_url}"):
            with st.spinner("Sumarizando..."):
                summary = summarize_document(doc_url)
                st.session_state[summary_key] = summary
            st.experimental_rerun()
    else:
        with st.expander("Sumário"):
            st.write(st.session_state[summary_key])

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
    # Gera a coluna de palavras-chave com base no campo "objeto"
    if 'objeto' in df.columns:
        df['palavras_chave'] = df['objeto'].apply(lambda x: generate_keywords(x) if isinstance(x, str) and x.strip() != "" else "")
    # NOVA ALTERAÇÃO: Adiciona a coluna "documentos" com os títulos concatenados dos documentos
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

def render_card(row):
    orgao = row.get("orgaoEntidade.razaoSocial", "N/D")
    uf = row.get("unidadeOrgao.ufSigla", "N/D")
    data_inclusao = row.get("dataInclusao", "N/D")
    processo = row.get("processo", "N/D")
    palavras_chave = row.get("palavras_chave", "N/D")
    valor_estimado = row.get("valorTotalEstimado", "N/D")
    if isinstance(valor_estimado, (int, float)):
        valor_estimado = locale.currency(valor_estimado, grouping=True)
    else:
        valor_estimado = "N/D"
    cnpj = row.get("orgaoEntidade.cnpj", "")
    ano = row.get("anoCompra", "")
    sequencial = row.get("sequencialCompra", "")
    
    card_html = f"""
    <div style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; margin-bottom: 10px;
                box-shadow: 2px 2px 5px rgba(0,0,0,0.1);">
      <h4 style="margin-bottom: 5px;">{orgao}</h4>
      <p style="margin: 2px 0;"><strong>UF:</strong> {uf}</p>
      <p style="margin: 2px 0;"><strong>Data Inclusão:</strong> {data_inclusao}</p>
      <p style="margin: 2px 0;"><strong>Processo:</strong> {processo}</p>
      <p style="margin: 2px 0;"><strong>Palavras-chave:</strong> {format_keywords(palavras_chave)}</p>
      <p style="margin: 2px 0;"><strong>Valor Estimado:</strong> {valor_estimado}</p>
    </div>
    """
    st.markdown(card_html, unsafe_allow_html=True)
    # Renderiza a seção de documentos com os botões de sumarização
    if cnpj and ano and sequencial:
        docs = fetch_documentos(cnpj, ano, sequencial)
        if docs:
            st.markdown("<strong>Documentos:</strong>", unsafe_allow_html=True)
            for doc in docs:
                render_document(doc)

def render_document(doc):
    titulo = doc.get("titulo", "Documento")
    doc_url = doc.get("url", "#")
    st.markdown(f'<a href="{doc_url}" target="_blank">{titulo}</a>', unsafe_allow_html=True)
    summary_key = f"summary_{hash(doc_url)}"
    if summary_key not in st.session_state:
        if st.button("Sumarizar", key=f"sum_btn_{doc_url}"):
            with st.spinner("Sumarizando..."):
                summary = summarize_document(doc_url)
                st.session_state[summary_key] = summary
            st.experimental_rerun()
    else:
        with st.expander("Sumário"):
            st.write(st.session_state[summary_key])

def summarize_document(doc_url):
    prompt = f"Por favor, leia o conteúdo do documento disponível no seguinte link: {doc_url} e resuma seu conteúdo detalhadamente, destacando os principais tópicos."
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
                if st.button(f"{kw} ×", key=f"kw_btn_{idx}", use_container_width=False):
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
    if "objeto" in df_all.columns and st.session_state.keywords:
        filtro = pd.Series([False]*len(df_all))
        for kw in st.session_state.keywords:
            filtro |= df_all["objeto"].str.lower().str.contains(kw.lower(), na=False)
        df_filtered = df_all[filtro]
    else:
        df_filtered = df_all.copy()

    st.subheader("Filtros Ativos")
    if st.session_state.keywords:
        st.write("Filtrando pelo campo 'objeto' contendo alguma das palavras:")
        keywords_chips = "<div style='display: flex; flex-wrap: wrap; gap: 5px;'>"
        for kw in st.session_state.keywords:
            keywords_chips += f"<div class='keyword-chip'>{kw}</div>"
        keywords_chips += "</div>"
        st.markdown(keywords_chips, unsafe_allow_html=True)
    else:
        st.write("Nenhuma palavra-chave definida.")

    st.subheader("Processos")
    if df_filtered.empty:
        st.write("Nenhum processo encontrado com os filtros aplicados.")
    else:
        for _, row in df_filtered.iterrows():
            render_card(row)

    excel_data = to_excel(df_all, df_filtered)
    st.download_button(
        label="Download Excel",
        data=excel_data,
        file_name=f"licitacoes_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
