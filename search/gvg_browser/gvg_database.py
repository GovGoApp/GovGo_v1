"""
Utilidades de banco de dados (V1) — conexão, engine, helpers e wrappers padronizados.

Objetivos:
- Centralizar conexões (psycopg2) e engine (SQLAlchemy) com carregamento de env.
- Expor wrappers com métricas de desempenho via categoria de debug "DB":
  - db_fetch_all, db_fetch_one, db_execute, db_execute_many, db_read_df
- Manter utilidades já existentes (fetch_documentos, get_user_resumo, upsert_user_resumo).

Observações:
- Não altera schema; apenas organiza e padroniza I/O de DB.
- Logs [DB] mostram tempo (ms) e contagem de linhas/afetadas. Logs [SQL] seguem separados.
"""
from __future__ import annotations

import os
import re
import time
from typing import Any, Iterable, List, Optional, Sequence

import psycopg2
import requests
from sqlalchemy import create_engine
from dotenv import load_dotenv

try:
    # Preferência por import absoluto quando presente no pacote
    from search.gvg_browser.gvg_debug import debug_log as dbg  # type: ignore
except Exception:  # pragma: no cover - fallback em runtime
    try:
        from .gvg_debug import debug_log as dbg  # type: ignore
    except Exception:
        from gvg_debug import debug_log as dbg  # type: ignore

# =====================
# Carregamento de envs
# =====================
load_dotenv()

def _load_env_priority() -> None:
    """Carrega variáveis de ambiente seguindo prioridade V1.

    Ordem de busca:
      1. supabase_v1.env (se existir)
      2. .env (já carregado inicialmente)
      3. supabase_v0.env (apenas fallback)
    """
    for candidate in ("supabase_v1.env", ".env", "supabase_v0.env"):
        try:
            if os.path.exists(candidate):
                load_dotenv(candidate, override=False)
        except Exception:
            pass

# =====================
# Conexões
# =====================

def create_connection() -> Optional[psycopg2.extensions.connection]:
    """Cria conexão psycopg2 com base V1."""
    try:
        _load_env_priority()
        connection = psycopg2.connect(
            host=os.getenv("SUPABASE_HOST", "aws-0-sa-east-1.pooler.supabase.com"),
            database=os.getenv("SUPABASE_DBNAME", os.getenv("SUPABASE_DB_NAME", "postgres")),
            user=os.getenv("SUPABASE_USER"),
            password=os.getenv("SUPABASE_PASSWORD"),
            port=os.getenv("SUPABASE_PORT", "6543"),
            connect_timeout=10,
        )
        return connection
    except Exception as e:
        try:
            dbg('SQL', f"Erro ao conectar ao banco: {e}")
        except Exception:
            pass
        return None


def create_engine_connection():
    """Cria engine SQLAlchemy (para uso com pandas, etc.)."""
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
        try:
            dbg('SQL', f"Erro ao criar engine SQLAlchemy: {e}")
        except Exception:
            pass
        return None

# =====================
# Helpers internos
# =====================

def _rows_to_dicts(cur, rows: Sequence[Sequence[Any]]) -> List[dict]:
    """Converte tuplas de cursor em dicts usando cursor.description."""
    try:
        cols = [d[0] for d in (cur.description or [])]
        return [dict(zip(cols, r)) for r in rows]
    except Exception:
        # fallback: melhor devolver dados crus a perder tudo
        return [dict(enumerate(r)) for r in rows]

# =====================
# Wrappers com métricas [DB]
# =====================

def db_fetch_all(sql: str, params: Optional[Sequence[Any]] = None, *, as_dict: bool = False, ctx: Optional[str] = None) -> List[Any]:
    """Executa SELECT e retorna todas as linhas. Quando as_dict=True, retorna List[dict].

    ctx: rótulo de contexto para enriquecer logs [DB] (ex.: "GSB._sql_only_search").
    """
    t0 = time.perf_counter()
    conn = create_connection()
    if not conn:
        dbg('DB', f'fetch_all{("="+ctx) if ctx else ""} FAIL: sem conexão')
        return []
    cur = None
    try:
        cur = conn.cursor()
        cur.execute(sql, params or None)
        rows = cur.fetchall()
        out = _rows_to_dicts(cur, rows) if as_dict else rows
        ms = int((time.perf_counter() - t0) * 1000)
        dbg('DB', f'fetch_all{("="+ctx) if ctx else ""} ms={ms} rows={len(rows)}')
        from gvg_usage import _get_current_aggregator  # import tardio para evitar ciclos
        aggr = _get_current_aggregator()
        if aggr:
            aggr.add_db_read(len(rows))

        return out
    except Exception as e:
        dbg('DB', f'fetch_all{("="+ctx) if ctx else ""} ERRO: {e}')
        return []
    finally:
        try:
            if cur:
                cur.close()
        finally:
            try:
                conn.close()
            except Exception:
                pass


def db_fetch_one(sql: str, params: Optional[Sequence[Any]] = None, *, as_dict: bool = False, ctx: Optional[str] = None) -> Any:
    """Executa SELECT e retorna uma única linha (ou None). Quando as_dict=True, retorna dict.

    ctx: rótulo de contexto para enriquecer logs [DB] (ex.: "GSB.get_details").
    """
    t0 = time.perf_counter()
    conn = create_connection()
    if not conn:
        dbg('DB', f'fetch_one{("="+ctx) if ctx else ""} FAIL: sem conexão')
        return None
    cur = None
    try:
        cur = conn.cursor()
        cur.execute(sql, params or None)
        row = cur.fetchone()
        ms = int((time.perf_counter() - t0) * 1000)
        dbg('DB', f'fetch_one{("="+ctx) if ctx else ""} ms={ms} row={(1 if row else 0)}')
        try:
            from gvg_usage import _get_current_aggregator
            aggr = _get_current_aggregator()
            if aggr and row is not None:
                aggr.add_db_read(1)
        except Exception:
            pass
        if row is None:
            return None
        if not as_dict:
            return row
        return _rows_to_dicts(cur, [row])[0]
    except Exception as e:
        try:
            dbg('DB', f'fetch_one{("="+ctx) if ctx else ""} ERRO: {e}')
        except Exception:
            pass
        return None
    finally:
        try:
            if cur:
                cur.close()
        finally:
            try:
                conn.close()
            except Exception:
                pass


def db_execute(sql: str, params: Optional[Sequence[Any]] = None, *, ctx: Optional[str] = None) -> int:
    """Executa comando DML e commita. Retorna número de linhas afetadas (ou 0).

    ctx: rótulo de contexto para enriquecer logs [DB].
    """
    t0 = time.perf_counter()
    conn = create_connection()
    if not conn:
        dbg('DB', f'execute{("="+ctx) if ctx else ""} FAIL: sem conexão')
        return 0
    cur = None
    try:
        cur = conn.cursor()
        cur.execute(sql, params or None)
        affected = cur.rowcount if cur.rowcount is not None else 0
        conn.commit()
        ms = int((time.perf_counter() - t0) * 1000)
        dbg('DB', f'execute{("="+ctx) if ctx else ""} ms={ms} affected={affected}')
        try:
            from gvg_usage import _get_current_aggregator
            aggr = _get_current_aggregator()
            if aggr and affected:
                aggr.add_db_written(int(affected))
        except Exception:
            pass
        return int(affected)
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        try:
            dbg('DB', f'execute{("="+ctx) if ctx else ""} ERRO: {e}')
        except Exception:
            pass
        return 0
    finally:
        try:
            if cur:
                cur.close()
        finally:
            try:
                conn.close()
            except Exception:
                pass


def db_execute_many(sql: str, seq_params: Iterable[Sequence[Any]], *, ctx: Optional[str] = None) -> int:
    """Executa executemany e commita. Retorna total afetado (se disponível).

    ctx: rótulo de contexto para enriquecer logs [DB].
    """
    t0 = time.perf_counter()
    conn = create_connection()
    if not conn:
        dbg('DB', f'execute_many{("="+ctx) if ctx else ""} FAIL: sem conexão')
        return 0
    cur = None
    try:
        cur = conn.cursor()
        cur.executemany(sql, list(seq_params))
        affected = cur.rowcount if cur.rowcount is not None else 0
        conn.commit()
        ms = int((time.perf_counter() - t0) * 1000)
        dbg('DB', f'execute_many{("="+ctx) if ctx else ""} ms={ms} affected={affected}')
        try:
            from gvg_usage import _get_current_aggregator
            aggr = _get_current_aggregator()
            if aggr and affected:
                aggr.add_db_written(int(affected))
        except Exception:
            pass
        return int(affected)
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        try:
            dbg('DB', f'execute_many{("="+ctx) if ctx else ""} ERRO: {e}')
        except Exception:
            pass
        return 0
    finally:
        try:
            if cur:
                cur.close()
        finally:
            try:
                conn.close()
            except Exception:
                pass


def db_execute_returning_one(sql: str, params: Optional[Sequence[Any]] = None, *, as_dict: bool = False, ctx: Optional[str] = None) -> Any:
    """Executa DML com RETURNING e commita; retorna a linha retornada (ou None).

    Exemplo: INSERT ... RETURNING id
    Útil quando precisamos do ID já persistido antes de operações dependentes.
    """
    t0 = time.perf_counter()
    conn = create_connection()
    if not conn:
        dbg('DB', f'execute_returning_one{("="+ctx) if ctx else ""} FAIL: sem conexão')
        return None
    cur = None
    try:
        cur = conn.cursor()
        cur.execute(sql, params or None)
        row = cur.fetchone()
        conn.commit()
        ms = int((time.perf_counter() - t0) * 1000)
        dbg('DB', f'execute_returning_one{("="+ctx) if ctx else ""} ms={ms} row={(1 if row else 0)}')
        try:
            from gvg_usage import _get_current_aggregator
            aggr = _get_current_aggregator()
            if aggr and row is not None:
                aggr.add_db_written(1)
        except Exception:
            pass
        if row is None:
            return None
        if not as_dict:
            return row
        return _rows_to_dicts(cur, [row])[0]
    except Exception as e:
        try:
            conn.rollback()
        except Exception:
            pass
        try:
            dbg('DB', f'execute_returning_one{("="+ctx) if ctx else ""} ERRO: {e}')
        except Exception:
            pass
        return None
    finally:
        try:
            if cur:
                cur.close()
        finally:
            try:
                conn.close()
            except Exception:
                pass


def db_read_df(sql: str, params: Optional[Sequence[Any]] = None, *, ctx: Optional[str] = None):
    """Executa SELECT e retorna pandas.DataFrame, ou None se pandas/engine indisponíveis.

    ctx: rótulo de contexto para enriquecer logs [DB].
    """
    try:
        import pandas as pd  # type: ignore
    except Exception:
        dbg('DB', f'read_df{("="+ctx) if ctx else ""} SKIP: pandas indisponível')
        return None
    engine = create_engine_connection()
    if engine is None:
        dbg('DB', f'read_df{("="+ctx) if ctx else ""} FAIL: engine indisponível')
        return None
    t0 = time.perf_counter()
    try:
        # Evita listas simples que podem ser interpretadas como executemany;
        # converte para tupla quando apropriado.
        if params is None:
            sql_params = None
        elif isinstance(params, dict):
            sql_params = params
        else:
            # Para sequência de parâmetros, preferir tupla (query única)
            try:
                sql_params = tuple(params)
            except Exception:
                sql_params = params
        df = pd.read_sql_query(sql, engine, params=sql_params)
        ms = int((time.perf_counter() - t0) * 1000)
        try:
            rows = len(df)
        except Exception:
            rows = 0
        dbg('DB', f'read_df{("="+ctx) if ctx else ""} ms={ms} rows={rows}')
        try:
            from gvg_usage import _get_current_aggregator
            aggr = _get_current_aggregator()
            if aggr and rows:
                aggr.add_db_read(int(rows))
        except Exception:
            pass
        return df
    except Exception as e:
        dbg('DB', f'read_df{("="+ctx) if ctx else ""} ERRO: {e}')
        return None

# =====================
# Documentos — best-effort (DB -> fallback API PNCP)
# =====================

def _parse_numero_controle_pncp(numero_controle: str):
    """Extrai (cnpj, sequencial, ano) do numeroControlePNCP.

    Formato esperado: 14d-1-SEQ/AAAA. Retorna (None, None, None) se inválido.
    """
    if not numero_controle:
        return None, None, None
    pattern = r"^(\d{14})-1-(\d+)/(\d{4})$"
    m = re.match(pattern, str(numero_controle).strip())
    if not m:
        return None, None, None
    return m.group(1), m.group(2), m.group(3)


def fetch_documentos(numero_controle: str) -> List[dict]:
    """Busca documentos de um processo com cache em BD (lista_documentos) e fallback para API.

    Estratégia:
    - Tenta ler public.contratacao.lista_documentos pelo numero_controle_pncp.
    - Se não houver, chama API PNCP, persiste em lista_documentos e usa o resultado.
    - Em qualquer falha de BD, cai para API sem quebrar a UI.
    - Normaliza saída (url, nome, tipo, tamanho, modificacao, sequencial, origem) e ordena por sequencial.
    """
    if not numero_controle:
        return []

    documentos: List[dict] = []

    # 1) Tentar ler do BD (lista_documentos)
    src_list = None
    came_from = None
    try:
        row = db_fetch_one(
            """
            SELECT lista_documentos
            FROM public.contratacao
            WHERE numero_controle_pncp = %s
            LIMIT 1
            """,
            (numero_controle,), as_dict=False, ctx="DOCS.fetch_documentos:read_json"
        )
        if row is not None:
            try:
                val = row[0]
                # psycopg2 já desserializa jsonb para tipos Python (list/dict)
                if isinstance(val, list):
                    src_list = val
                    came_from = 'bd'
            except Exception:
                src_list = None
    except Exception as e:
        # Coluna pode não existir ou BD indisponível — seguir para API
        try:
            dbg('DOCS', f"fetch_documentos BD skip: {e}")
        except Exception:
            pass
        src_list = None

    # 2) Se não houver no BD, chamar API e tentar persistir
    if not src_list:
        cnpj, sequencial, ano = _parse_numero_controle_pncp(numero_controle)
        if not all([cnpj, sequencial, ano]):
            return []
        api_url = (
            f"https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}/arquivos"
        )
        try:
            resp = requests.get(api_url, timeout=20)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    src_list = [item for item in data if isinstance(item, dict)]
                    came_from = 'api'
                # contabilizar bytes baixados
                try:
                    from gvg_usage import _get_current_aggregator
                    aggr = _get_current_aggregator()
                    if aggr:
                        aggr.add_file_in(len(resp.content or b''))
                except Exception:
                    pass
            else:
                dbg('DOCS', f"API documentos status {resp.status_code} ({numero_controle})")
        except Exception as e:
            dbg('DOCS', f"API documentos erro: {e}")

        # Persistir no BD se veio da API e houver conexão/coluna
        if src_list and came_from == 'api':
            try:
                # Usar psycopg2.extras.Json para garantir serialização correta
                from psycopg2.extras import Json  # type: ignore
                affected = db_execute(
                    """
                    UPDATE public.contratacao
                    SET lista_documentos = %s, updated_at = COALESCE(updated_at, now())
                    WHERE numero_controle_pncp = %s
                    """,
                    (Json(src_list), numero_controle),
                    ctx="DOCS.fetch_documentos:write_json"
                )
                if not affected:
                    # Caso não atualize (registro não encontrado), tentar um UPSERT mínimo se permitido
                    pass
            except Exception as e:
                try:
                    dbg('DOCS', f"persist lista_documentos FAIL: {e}")
                except Exception:
                    pass

    # 3) Normalizar saída
    for item in (src_list or []):
        try:
            url = item.get('url') or item.get('uri') or ''
            if not url:
                continue
            nome = item.get('titulo') or 'Documento'
            documentos.append({
                'url': url,
                'nome': nome,
                'tipo': item.get('tipoDocumentoNome') or 'N/I',
                'tamanho': item.get('tamanhoArquivo'),
                'modificacao': item.get('dataPublicacaoPncp'),
                'sequencial': item.get('sequencialDocumento'),
                'origem': came_from or 'api',
            })
        except Exception:
            continue

    # 4) Ordenar por sequencial quando disponível
    try:
        documentos.sort(key=lambda x: int(x.get('sequencial') or 0))
    except Exception:
        pass

    return documentos

# =====================
# Resumos por usuário (CRUD)
# =====================

def get_user_resumo(user_id: str, numero_pncp: str) -> Optional[str]:
    """Retorna o resumo Markdown salvo para (user_id, numero_pncp) ou None.

    Requer a tabela public.user_resumos com UNIQUE(user_id, numero_controle_pncp).
    """
    if not user_id or not numero_pncp:
        return None
    conn = None
    cur = None
    try:
        conn = create_connection()
        if not conn:
            return None
        cur = conn.cursor()
        cur.execute(
            """
            SELECT resumo_md
              FROM public.user_resumos
             WHERE user_id = %s AND numero_controle_pncp = %s
             LIMIT 1
            """,
            (user_id, str(numero_pncp)),
        )
        row = cur.fetchone()
        return row[0] if row and row[0] else None
    except Exception as e:
        try:
            dbg('SQL', f"get_user_resumo erro: {e}")
        except Exception:
            pass
        return None
    finally:
        try:
            if cur:
                cur.close()
        finally:
            if conn:
                conn.close()


def upsert_user_resumo(user_id: str, numero_pncp: str, resumo_md: str) -> bool:
    """Insere/atualiza o resumo Markdown para (user_id, numero_pncp).

    Usa ON CONFLICT (user_id, numero_controle_pncp) DO UPDATE para deduplicar.
    """
    if not user_id or not numero_pncp or not isinstance(resumo_md, str) or not resumo_md.strip():
        return False
    conn = None
    cur = None
    try:
        conn = create_connection()
        if not conn:
            return False
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO public.user_resumos (user_id, numero_controle_pncp, resumo_md)
            VALUES (%s, %s, %s)
            ON CONFLICT (user_id, numero_controle_pncp)
            DO UPDATE SET resumo_md = EXCLUDED.resumo_md, updated_at = now()
            """,
            (user_id, str(numero_pncp), resumo_md),
        )
        conn.commit()
        return True
    except Exception as e:
        try:
            if conn:
                conn.rollback()
        except Exception:
            pass
        try:
            dbg('SQL', f"upsert_user_resumo erro: {e}")
        except Exception:
            pass
        return False
    finally:
        try:
            if cur:
                cur.close()
        finally:
            if conn:
                conn.close()


# =====================
# Storage genérico (Supabase Python SDK)
# =====================

_SUPABASE_CLIENT = None

def get_supabase_client():
    """Retorna cliente Supabase (singleton simples)."""
    global _SUPABASE_CLIENT
    if _SUPABASE_CLIENT is not None:
        return _SUPABASE_CLIENT
    try:
        from supabase import create_client  # type: ignore
    except Exception as e:
        dbg('DB', f"Supabase SDK indisponível: {e}")
        return None
    _load_env_priority()
    url = os.getenv('SUPABASE_URL')
    k_srv = os.getenv('SUPABASE_KEY')
    k_anon = os.getenv('SUPABASE_ANON_KEY')
    
    def _looks_jwt(s: str | None) -> bool:
        try:
            return bool(s and s.strip().startswith('eyJ'))
        except Exception:
            return False
    key = k_srv if _looks_jwt(k_srv) else (k_anon if _looks_jwt(k_anon) else (k_srv or k_anon))
    if not url or not key:
        dbg('DB', 'get_supabase_client FAIL: SUPABASE_URL/KEY ausentes')
        return None
    try:
        _SUPABASE_CLIENT = create_client(url, key)
        dbg('DB', f'supabase client ok url={url} key_type={"service" if key==k_srv else "anon"}')
        return _SUPABASE_CLIENT
    except Exception as e:
        dbg('DB', f"Erro ao criar Supabase client: {e}")
        return None

def storage_get_public_url(bucket: str, key: str) -> Optional[str]:
    client = get_supabase_client()
    if not client:
        return None
    try:
        url = client.storage.from_(bucket).get_public_url(key)
        # Sanitiza URLs que venham com '?' vazio ao final
        try:
            if isinstance(url, str):
                if url.endswith('?'):
                    return url[:-1]
                # Normaliza '?download=' vazio
                if url.endswith('?download='):
                    return url[:-10]
            return url
        except Exception:
            return url
    except Exception as e:
        dbg('DB', f'storage_get_public_url ERRO: {e}')
        return None

def storage_put_bytes(bucket: str, key: str, data: bytes, content_type: str = 'application/octet-stream', upsert: bool = False) -> tuple[bool, Optional[str], int]:
    client = get_supabase_client()
    if not client:
        return False, None, 0
    try:
        # SDK Python v2: upload(path, file, file_options={"contentType": "...", "upsert": True})
        opts = {"contentType": content_type, "upsert": "true" if upsert else "false"}
        dbg('DB', f'storage upload: bucket={bucket} key={key} size={len(data or b"" )} upsert={opts.get("upsert")}')
        res = client.storage.from_(bucket).upload(key, data, file_options=opts)
        # upload retorna dict ou None; se sem exceção, consideramos OK
        size = len(data or b'')
        public_url = storage_get_public_url(bucket, key)
        dbg('DB', f'storage upload ok: public_url={public_url}')
        try:
            from gvg_usage import _get_current_aggregator
            aggr = _get_current_aggregator()
            if aggr:
                aggr.add_file_out(size)
        except Exception:
            pass
        return True, public_url, size
    except Exception as e:
        dbg('DB', f'storage_put_bytes ERRO: {e}')
        return False, None, 0

def storage_put_text(bucket: str, key: str, text: str, content_type: str = 'text/markdown; charset=utf-8', upsert: bool = False) -> tuple[bool, Optional[str], int]:
    # Inclui BOM para melhor compatibilidade no Windows ao abrir .md diretamente
    bom = b"\xef\xbb\xbf" if isinstance(text, str) and content_type.startswith('text/') else b''
    data = bom + (text or '').encode('utf-8')
    return storage_put_bytes(bucket, key, data, content_type=content_type, upsert=upsert)

def storage_download(bucket: str, key: str) -> tuple[bool, Optional[bytes], Optional[str]]:
    client = get_supabase_client()
    if not client:
        return False, None, 'no-client'
    try:
        data = client.storage.from_(bucket).download(key)
        return True, data, None
    except Exception as e:
        return False, None, str(e)

def storage_list(bucket: str, prefix: str = '') -> list:
    client = get_supabase_client()
    if not client:
        return []
    try:
        return client.storage.from_(bucket).list(prefix)
    except Exception as e:
        dbg('DB', f'storage_list ERRO: {e}')
        return []

def storage_remove(bucket: str, keys: list[str]) -> bool:
    client = get_supabase_client()
    if not client:
        return False
    try:
        client.storage.from_(bucket).remove(keys)
        return True
    except Exception as e:
        dbg('DB', f'storage_remove ERRO: {e}')
        return False


def upsert_user_document(user_id: str, numero_pncp: str, doc_name: str, doc_type: str | None, storage_url: str, size_bytes: int | None = None) -> bool:
    """Insere registro em public.user_documents.

    Requer que a tabela exista no BD. Se não existir ou falhar, retorna False sem quebrar o fluxo.
    """
    if not user_id or not numero_pncp or not storage_url or not doc_name:
        return False
    conn = None
    cur = None
    try:
        conn = create_connection()
        if not conn:
            return False
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO public.user_documents
                (user_id, numero_controle_pncp, doc_name, doc_type, storage_url, size_bytes, created_at, updated_at)
            VALUES (%s, %s, %s, %s, %s, %s, now(), now())
            """,
            (user_id, str(numero_pncp), doc_name, (doc_type or None), storage_url, int(size_bytes or 0))
        )
        conn.commit()
        return True
    except Exception as e:
        try:
            if conn:
                conn.rollback()
        except Exception:
            pass
        try:
            dbg('DB', f"upsert_user_document erro: {e}")
        except Exception:
            pass
        return False
    finally:
        try:
            if cur:
                cur.close()
        finally:
            if conn:
                conn.close()


# =====================
# Mensagens do usuário (insert)
# =====================

def insert_user_message(user_id: str, user_name: str, message: str, resolved_status: int = 0) -> Optional[dict]:
    """Insere uma mensagem do usuário e retorna {'id': ..., 'created_at': ...} ou None.

    Requer tabela public.user_message com colunas:
      (id, user_id uuid, user_name text, message text, resolved_status smallint, created_at, updated_at)
    """
    try:
        uid = (user_id or '').strip()
        uname = (user_name or '').strip()
        msg = (message or '').strip()
        if not uid or not uname or not msg:
            return None
        row = db_execute_returning_one(
            """
            INSERT INTO public.user_message (user_id, user_name, message, resolved_status, created_at, updated_at)
            VALUES (%s, %s, %s, %s, now(), now())
            RETURNING id, created_at
            """,
            (uid, uname, msg, int(resolved_status)),
            as_dict=False,
            ctx="MSG.insert_user_message",
        )
        if not row:
            return None
        try:
            _id = row[0]
            _ts = row[1]
        except Exception:
            return None
        try:
            created_iso = _ts.isoformat() if hasattr(_ts, 'isoformat') else str(_ts)
        except Exception:
            created_iso = None
        return {'id': _id, 'created_at': created_iso}
    except Exception as e:
        try:
            dbg('DB', f"insert_user_message ERRO: {e}")
        except Exception:
            pass
        return None
