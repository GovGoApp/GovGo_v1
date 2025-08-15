"""
gvg_database.py
Módulo otimizado para conexões com banco de dados GvG
Contém apenas as funções de banco realmente utilizadas
"""

import os
import psycopg2
from sqlalchemy import create_engine
from dotenv import load_dotenv
import re
import requests

# Carregar configurações
load_dotenv()

def create_connection():
    """
    Cria conexão direta com PostgreSQL via psycopg2
    
    Returns:
        psycopg2.connection: Conexão com o banco ou None se erro
    """
    try:
        # Carregar configurações do arquivo .env
        env_file_path = "supabase_v0.env"
        if os.path.exists(env_file_path):
            from dotenv import load_dotenv
            load_dotenv(env_file_path)
        
        connection = psycopg2.connect(
            host=os.getenv("SUPABASE_HOST", "aws-0-sa-east-1.pooler.supabase.com"),
            database=os.getenv("SUPABASE_DB_NAME", "postgres"),  
            user=os.getenv("SUPABASE_USER", "postgres.bzgtlersjbetwilubnng"),
            password=os.getenv("SUPABASE_PASSWORD", "GovGo2025!!"),
            port=os.getenv("SUPABASE_PORT", "6543")
        )
        
        return connection
        
    except Exception as e:
        print(f"Erro ao conectar ao banco: {e}")
        return None

def create_engine_connection():
    """
    Cria engine SQLAlchemy para uso com Pandas
    
    Returns:
        sqlalchemy.engine.Engine: Engine do SQLAlchemy ou None se erro
    """
    try:
        # Carregar configurações do arquivo .env
        env_file_path = "supabase_v0.env"
        if os.path.exists(env_file_path):
            from dotenv import load_dotenv
            load_dotenv(env_file_path)
        
        # Construir URL de conexão
        host = os.getenv('SUPABASE_HOST', 'aws-0-sa-east-1.pooler.supabase.com')
        user = os.getenv('SUPABASE_USER', 'postgres.bzgtlersjbetwilubnng')
        password = os.getenv('SUPABASE_PASSWORD', 'GovGo2025!!')
        port = os.getenv('SUPABASE_PORT', '6543')
        dbname = os.getenv('SUPABASE_DB_NAME', 'postgres')
        
        connection_string = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
        
        engine = create_engine(connection_string)
        return engine
        
    except Exception as e:
        print(f"Erro ao criar engine SQLAlchemy: {e}")
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
    """Busca documentos de um processo PNCP.

    Estratégia:
      1. (Legacy) Tentativa de buscar no banco (caso a tabela possua colunas de documentos).
         A coluna 'urldownload' não existe mais; tentar colunas alternativas dinamicamente.
      2. Fallback oficial: consumir API pública PNCP /arquivos (v9 style) garantindo
         sempre retorno consistente.

    Retorna lista de dicts com chaves: nome, url, tipo, tamanho, modificacao, origem.
    """
    if not numero_controle:
        return []

    documentos = []

    # 1) Tentativa banco (best-effort) -------------------------------
    conn = create_connection()
    if conn:
        try:
            cursor = conn.cursor()
            # Descobrir se existem colunas candidatas a URL via information_schema
            cursor.execute("""
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'contratacoes'
            """)
            cols = {r[0].lower() for r in cursor.fetchall()}
            url_cols_priority = [
                'urldownload', 'url', 'linkdocumento', 'linksistemaorigem',
                'linksistema_origem', 'linksistema', 'link'
            ]
            url_cols = [c for c in url_cols_priority if c in cols]

            if url_cols:
                # Montar select dinâmico apenas com colunas existentes relevantes
                select_cols = [f"{c} as url" for c in url_cols[:1]]  # primeira coluna válida como url
                extra_cols = [c for c in ['nome', 'tipo', 'tamanhoarquivo', 'ultimamodificacao'] if c in cols]
                select_cols.extend(extra_cols)
                dynamic_query = f"SELECT DISTINCT {', '.join(select_cols)} FROM contratacoes WHERE numerocontrolepncp = %s"
                cursor.execute(dynamic_query, (numero_controle,))
                for row in cursor.fetchall():
                    # Mapear posições
                    base = {
                        'url': row[0],
                        'nome': None,
                        'tipo': None,
                        'tamanho': None,
                        'modificacao': None,
                        'origem': 'db'
                    }
                    # Preencher extras se presentes
                    for idx, col in enumerate(extra_cols, start=1):
                        if col == 'nome':
                            base['nome'] = row[idx]
                        elif col == 'tipo':
                            base['tipo'] = row[idx]
                        elif col == 'tamanhoarquivo':
                            base['tamanho'] = row[idx]
                        elif col == 'ultimamodificacao':
                            base['modificacao'] = row[idx]
                    if base.get('url'):
                        base['nome'] = base.get('nome') or 'Documento'
                        base['tipo'] = base.get('tipo') or 'N/I'
                        documentos.append(base)
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"⚠️ Aviso (fetch_documentos DB): {e}")
            try:
                conn.close()
            except Exception:
                pass

    # Se já encontramos documentos válidos no banco, retornar
    if documentos:
        return documentos

    # 2) Fallback API oficial PNCP ----------------------------------
    cnpj, sequencial, ano = _parse_numero_controle_pncp(numero_controle)
    if not all([cnpj, sequencial, ano]):
        # Formato inesperado – não falhar, apenas retornar vazio
        return []

    api_url = f"https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/arquivos"
    try:
        resp = requests.get(api_url, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list):
                for item in data:
                    if not isinstance(item, dict):
                        continue
                    documentos.append({
                        'url': item.get('url') or item.get('uri') or '',
                        'nome': item.get('titulo') or f"Documento_{item.get('sequencialDocumento', len(documentos)+1)}",
                        'tipo': item.get('tipoDocumentoNome') or item.get('tipoDocumentoDescricao') or 'N/I',
                        'tamanho': item.get('tamanhoArquivo') or item.get('tamanho'),
                        'modificacao': item.get('dataPublicacaoPncp'),
                        'sequencial': item.get('sequencialDocumento'),
                        'origem': 'api'
                    })
        else:
            print(f"⚠️ API PNCP retornou status {resp.status_code} para documentos de {numero_controle}")
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Erro de rede ao acessar API PNCP: {e}")
    except Exception as e:
        print(f"⚠️ Erro inesperado no fallback API documentos: {e}")

    return documentos
