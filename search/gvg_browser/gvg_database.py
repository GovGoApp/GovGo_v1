"""
gvg_database.py
Conexões e utilidades de banco (VERSÃO V1 – apenas schema novo).
"""

import os
import re
import psycopg2
import requests
from sqlalchemy import create_engine
from dotenv import load_dotenv
try:
    from search.gvg_browser.gvg_debug import debug_log as dbg  # type: ignore
except Exception:
    try:
        from .gvg_debug import debug_log as dbg  # type: ignore
    except Exception:
        from gvg_debug import debug_log as dbg  # type: ignore

# Carregar configurações
load_dotenv()

def _load_env_priority():
    """Carrega variáveis de ambiente seguindo prioridade V1.

    Ordem:
      1. supabase_v1.env (se existir)
      2. .env (já carregado inicialmente)
      3. supabase_v0.env (apenas fallback – não recomendado)
    """
    for candidate in ("supabase_v1.env", ".env", "supabase_v0.env"):
        if os.path.exists(candidate):
            load_dotenv(candidate, override=False)


def create_connection():
    """Cria conexão psycopg2 com base V1 (sem lógica de versão)."""
    try:
        _load_env_priority()
        connection = psycopg2.connect(
            host=os.getenv("SUPABASE_HOST", "aws-0-sa-east-1.pooler.supabase.com"),
            database=os.getenv("SUPABASE_DBNAME", os.getenv("SUPABASE_DB_NAME", "postgres")),
            user=os.getenv("SUPABASE_USER"),
            password=os.getenv("SUPABASE_PASSWORD"),
            port=os.getenv("SUPABASE_PORT", "6543"),
            connect_timeout=10
        )
        return connection
    except Exception as e:
        dbg('SQL', f"Erro ao conectar ao banco: {e}")
        return None

def create_engine_connection():
    """Cria engine SQLAlchemy (uso Pandas)."""
    try:
        _load_env_priority()
        host = os.getenv('SUPABASE_HOST', 'aws-0-sa-east-1.pooler.supabase.com')
        user = os.getenv('SUPABASE_USER')
        password = os.getenv('SUPABASE_PASSWORD')
        port = os.getenv('SUPABASE_PORT', '6543')
        dbname = os.getenv('SUPABASE_DBNAME', os.getenv('SUPABASE_DB_NAME', 'postgres'))
        connection_string = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
        return create_engine(connection_string, pool_pre_ping=True)
    except Exception as e:
        dbg('SQL', f"Erro ao criar engine SQLAlchemy: {e}")
        return None

def _parse_numero_controle_pncp(numero_controle: str):
    """Extrai (cnpj, sequencial, ano) do numeroControlePNCP.

    Formato esperado: 14d-1-SEQ/AAAA. Retorna (None, None, None) se inválido.
    """
    if not numero_controle:
        return None, None, None
    pattern = r"^(\d{14})-1-(\d+)/(\d{4})$"
    m = re.match(pattern, numero_controle.strip())
    if not m:
        return None, None, None
    return m.group(1), m.group(2), m.group(3)


def fetch_documentos(numero_controle: str):
    """Busca documentos de um processo (tentativa leve + fallback API PNCP).

    Nota: schema V1 não mantém tabela específica de documentos aqui; mantemos
    lógica best-effort (possível futura remoção). Otimização: não percorre
    information_schema mais de uma vez por invocação.
    """
    if not numero_controle:
        return []

    documentos = []
    conn = create_connection()
    if conn:
        try:
            cur = conn.cursor()
            # Tentar localizar colunas candidatas na tabela contratacao
            cur.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_schema='public' AND table_name='contratacao'
            """)
            cols = {r[0].lower() for r in cur.fetchall()}
            url_cols_priority = ['link_sistema_origem','url','link']
            url_cols = [c for c in url_cols_priority if c in cols]
            if url_cols:
                col = url_cols[0]
                cur.execute(f"SELECT {col} FROM contratacao WHERE numero_controle_pncp = %s LIMIT 1", (numero_controle,))
                for (url,) in cur.fetchall():
                    if url:
                        documentos.append({'url': url, 'nome': 'Link Sistema', 'tipo': 'origem', 'origem': 'db'})
            cur.close(); conn.close()
        except Exception as e:
            dbg('SQL', f"⚠️ fetch_documentos DB: {e}")
            try: conn.close()
            except Exception: pass

    if documentos:
        return documentos

    # Fallback API oficial
    cnpj, sequencial, ano = _parse_numero_controle_pncp(numero_controle)
    if not all([cnpj, sequencial, ano]):
        return []
    api_url = f"https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/arquivos"
    try:
        resp = requests.get(api_url, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list):
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    documentos.append({
                        'url': item.get('url') or item.get('uri') or '',
                        'nome': item.get('titulo') or 'Documento',
                        'tipo': item.get('tipoDocumentoNome') or 'N/I',
                        'tamanho': item.get('tamanhoArquivo'),
                        'modificacao': item.get('dataPublicacaoPncp'),
                        'sequencial': item.get('sequencialDocumento'),
                        'origem': 'api'
                    })
        else:
            dbg('DOCS', f"⚠️ API documentos status {resp.status_code} ({numero_controle})")
    except Exception as e:
        dbg('DOCS', f"⚠️ API documentos erro: {e}")
    return documentos
"""
gvg_database.py
Conexões e utilidades de banco (VERSÃO V1 – apenas schema novo).

Alterações Fase 2:
    • Remove referências a supabase_v0.env; prioriza supabase_v1.env ou .env.
    • Corrige nome de variável de ambiente SUPABASE_DBNAME.
    • Ajusta fetch_documentos para tabela 'contratacao' (antes 'contratacoes').
    • Garante comparação segura de datas (campos TEXT) usando expressão defensiva.
"""

import os
import re
import psycopg2
import requests
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Carregar configurações
load_dotenv()

def _load_env_priority():
    """Carrega variáveis de ambiente seguindo prioridade V1.

    Ordem:
      1. supabase_v1.env (se existir)
      2. .env (já carregado inicialmente)
      3. supabase_v0.env (apenas fallback – não recomendado)
    """
    for candidate in ("supabase_v1.env", ".env", "supabase_v0.env"):
        if os.path.exists(candidate):
            load_dotenv(candidate, override=False)


def create_connection():
    """Cria conexão psycopg2 com base V1 (sem lógica de versão)."""
    try:
        _load_env_priority()
        connection = psycopg2.connect(
            host=os.getenv("SUPABASE_HOST", "aws-0-sa-east-1.pooler.supabase.com"),
            database=os.getenv("SUPABASE_DBNAME", os.getenv("SUPABASE_DB_NAME", "postgres")),
            user=os.getenv("SUPABASE_USER"),
            password=os.getenv("SUPABASE_PASSWORD"),
            port=os.getenv("SUPABASE_PORT", "6543"),
            connect_timeout=10
        )
        return connection
    except Exception as e:
        dbg('SQL', f"Erro ao conectar ao banco: {e}")
        return None

def create_engine_connection():
    """Cria engine SQLAlchemy (uso Pandas)."""
    try:
        _load_env_priority()
        host = os.getenv('SUPABASE_HOST', 'aws-0-sa-east-1.pooler.supabase.com')
        user = os.getenv('SUPABASE_USER')
        password = os.getenv('SUPABASE_PASSWORD')
        port = os.getenv('SUPABASE_PORT', '6543')
        dbname = os.getenv('SUPABASE_DBNAME', os.getenv('SUPABASE_DB_NAME', 'postgres'))
        connection_string = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
        return create_engine(connection_string, pool_pre_ping=True)
    except Exception as e:
        dbg('SQL', f"Erro ao criar engine SQLAlchemy: {e}")
        return None

def _parse_numero_controle_pncp(numero_controle: str):
    """Extrai (cnpj, sequencial, ano) do numeroControlePNCP.

    Formato esperado: 14d-1-SEQ/AAAA. Retorna (None, None, None) se inválido.
    """
    if not numero_controle:
        return None, None, None
    pattern = r"^(\d{14})-1-(\d+)/(\d{4})$"
    m = re.match(pattern, numero_controle.strip())
    if not m:
        return None, None, None
    return m.group(1), m.group(2), m.group(3)


def fetch_documentos(numero_controle: str):
    """Busca documentos de um processo (tentativa leve + fallback API PNCP).

    Nota: schema V1 não mantém tabela específica de documentos aqui; mantemos
    lógica best-effort (possível futura remoção). Otimização: não percorre
    information_schema mais de uma vez por invocação.
    """
    if not numero_controle:
        return []

    documentos = []
    conn = create_connection()
    if conn:
        try:
            cur = conn.cursor()
            # Tentar localizar colunas candidatas na tabela contratacao
            cur.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_schema='public' AND table_name='contratacao'
            """)
            cols = {r[0].lower() for r in cur.fetchall()}
            url_cols_priority = ['link_sistema_origem','url','link']
            url_cols = [c for c in url_cols_priority if c in cols]
            if url_cols:
                col = url_cols[0]
                cur.execute(f"SELECT {col} FROM contratacao WHERE numero_controle_pncp = %s LIMIT 1", (numero_controle,))
                for (url,) in cur.fetchall():
                    if url:
                        documentos.append({'url': url, 'nome': 'Link Sistema', 'tipo': 'origem', 'origem': 'db'})
            cur.close(); conn.close()
        except Exception as e:
            dbg('SQL', f"⚠️ fetch_documentos DB: {e}")
            try: conn.close()
            except Exception: pass

    if documentos:
        return documentos

    # Fallback API oficial
    cnpj, sequencial, ano = _parse_numero_controle_pncp(numero_controle)
    if not all([cnpj, sequencial, ano]):
        return []
    api_url = f"https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/arquivos"
    try:
        resp = requests.get(api_url, timeout=20)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list):
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    documentos.append({
                        'url': item.get('url') or item.get('uri') or '',
                        'nome': item.get('titulo') or 'Documento',
                        'tipo': item.get('tipoDocumentoNome') or 'N/I',
                        'tamanho': item.get('tamanhoArquivo'),
                        'modificacao': item.get('dataPublicacaoPncp'),
                        'sequencial': item.get('sequencialDocumento'),
                        'origem': 'api'
                    })
        else:
            dbg('DOCS', f"⚠️ API documentos status {resp.status_code} ({numero_controle})")
    except Exception as e:
        dbg('DOCS', f"⚠️ API documentos erro: {e}")
    return documentos
