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
    """Busca documentos de um processo (tentativa leve em DB + fallback API PNCP)."""
    if not numero_controle:
        return []

    documentos: List[dict] = []
    try:
        # Colunas existentes em contratacao
        col_rows = db_fetch_all(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_schema='public' AND table_name='contratacao'
            """,
            ctx="DOCS.fetch_documentos:columns"
        )
        cols = {r[0].lower() for r in (col_rows or [])}
        url_cols_priority = ['link_sistema_origem', 'url', 'link']
        url_cols = [c for c in url_cols_priority if c in cols]
        if url_cols:
            col = url_cols[0]
            url_rows = db_fetch_all(
                f"SELECT {col} FROM contratacao WHERE numero_controle_pncp = %s LIMIT 1",
                (numero_controle,), ctx="DOCS.fetch_documentos:select_url"
            ) or []
            for r in url_rows:
                # rows vem como tuplas (as_dict False)
                try:
                    url = r[0]
                except Exception:
                    url = None
                if url:
                    # Usar a própria URL (sem protocolo) como nome em vez de placeholder genérico
                    try:
                        display = url.split('://',1)[-1]
                    except Exception:
                        display = url
                    documentos.append({'url': url, 'nome': display, 'tipo': 'origem', 'origem': 'db'})
    except Exception as e:
        try:
            dbg('SQL', f"fetch_documentos DB: {e}")
        except Exception:
            pass

    if documentos:
        return documentos

    # Fallback API oficial (somente se não achou nada no DB)
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
                        'origem': 'api',
                    })
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
