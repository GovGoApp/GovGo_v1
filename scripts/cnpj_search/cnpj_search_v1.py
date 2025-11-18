#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cnpj_search_v1

Objetivo
- Dado um CNPJ, gerar um "perfil semântico" a partir dos embeddings dos seus contratos
  (public.contrato_emb) e, em seguida, buscar contratações similares em
  public.contratacao_emb, retornando lista de resultados semelhante ao GST/GSB.

Entradas (CLI)
- --cnpj (obrigatório): CNPJ do fornecedor (dígitos ou formatado)
- --top-k (opcional, default=30): quantidade de contratações a retornar
- --timeout-ms (opcional, default=90000): timeout da consulta de similaridade (ms)
- --fallback-sample-pct (opcional, default=2.0): porcentagem do TABLESAMPLE no fallback

Ambiente (.env em v1/scripts)
- SUPABASE_HOST, SUPABASE_PORT, SUPABASE_DBNAME, SUPABASE_USER, SUPABASE_PASSWORD
- REQUEST_TIMEOUT=30 (opcional)
- USER_AGENT="GovGo-CNPJ/1.0" (opcional)

Saída
- JSON impresso no stdout com chaves: company (se obtido via OpenCNPJ), stats, results

Observações
- Se a API do OpenCNPJ falhar (ex.: 403/404), o fluxo continua sem o bloco company.
- Se não houver contratos com embeddings, retorna lista vazia com stats explicando o motivo.
"""
import os
import re
import json
import argparse
import logging
from typing import List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import errors as pg_errors
from dotenv import load_dotenv
import sys
from pathlib import Path

# -------------------- gvg_debug (import resiliente) --------------------
# Tenta ajustar sys.path para encontrar search/gvg_browser/gvg_debug.py
try:
    _here = Path(__file__).resolve()
    _root = _here.parents[2]  # .../v1
    _gvg_path = _root / "search" / "gvg_browser"
    if _gvg_path.exists() and str(_gvg_path) not in sys.path:
        sys.path.insert(0, str(_gvg_path))
except Exception:
    pass
try:
    # Caminho quando executado fora do pacote
    from search.gvg_browser.gvg_debug import debug_log as dbg, is_debug_enabled as isdbg, debug_sql as dbg_sql  # type: ignore
except Exception:
    try:
        # Caminho simples se PYTHONPATH já inclui a pasta
        from gvg_debug import debug_log as dbg, is_debug_enabled as isdbg, debug_sql as dbg_sql  # type: ignore
    except Exception:
        # No-op fallbacks
        def dbg(area: str, *args, **kwargs):
            return None
        def isdbg(area: str) -> bool:
            return False
        def dbg_sql(label: str, sql: str, params: Optional[List] = None, names: Optional[List[str]] = None):
            return None

# -------------------- Config e utilitários --------------------

API_BASE = "https://api.opencnpj.org"


def load_env():
    env_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".env"))
    load_dotenv(env_path)
    # Indica caminho do .env carregado quando em DEBUG
    dbg('SEARCH', 'ENV carregado de', env_path)


def get_db_conn():
    return psycopg2.connect(
        host=os.environ.get("SUPABASE_HOST"),
        port=int(os.environ.get("SUPABASE_PORT", "6543")),
        dbname=os.environ.get("SUPABASE_DBNAME"),
        user=os.environ.get("SUPABASE_USER"),
        password=os.environ.get("SUPABASE_PASSWORD"),
    )


def normalize_cnpj(cnpj: str) -> Optional[str]:
    if not cnpj:
        return None
    digits = re.sub(r"\D", "", str(cnpj))
    ok = digits if len(digits) == 14 else None
    if ok:
        dbg('SEARCH', 'CNPJ normalizado =', ok)
    else:
        dbg('SEARCH', 'CNPJ inválido recebido =', cnpj)
    return ok


def build_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=3,
        backoff_factor=1.5,
        status_forcelist=[408, 429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    ua = os.environ.get("USER_AGENT", "GovGo-CNPJ/1.0")
    s.headers.update({
        "accept": "application/json",
        "user-agent": ua,
        "accept-language": "pt-BR,pt;q=0.9",
        "connection": "keep-alive",
    })
    return s


# -------------------- OpenCNPJ (contexto) --------------------

def fetch_company(session: requests.Session, cnpj: str, timeout: float) -> Optional[dict]:
    url = f"{API_BASE}/{cnpj}"
    try:
        resp = session.get(url, timeout=timeout)
    except requests.RequestException as e:
        logging.warning("OpenCNPJ indisponível: %s", e)
        dbg('SEARCH', 'OpenCNPJ indisponível para', cnpj, '| erro:', e)
        return None
    if resp.status_code == 200:
        try:
            j = resp.json()
            dbg('SEARCH', 'OpenCNPJ 200 para', cnpj, '| campos:', list(j.keys())[:6])
            return j
        except Exception:
            logging.warning("Resposta 200 inválida da API para %s", cnpj)
            dbg('SEARCH', 'OpenCNPJ 200, mas JSON inválido para', cnpj)
            return None
    # 404/403/429/outros: seguir sem bloquear
    logging.info("OpenCNPJ retorno %s para %s (seguindo sem company)", resp.status_code, cnpj)
    dbg('SEARCH', 'OpenCNPJ', resp.status_code, 'para', cnpj, '(seguindo sem company)')
    return None


# -------------------- Embeddings e busca --------------------

def get_contrato_ids_for_cnpj(conn, cnpj14: str) -> List[str]:
    sql = """
        SELECT numero_controle_pncp
        FROM public.contrato
        WHERE ni_fornecedor = %s
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        if isdbg('SQL'):
            dbg_sql('cnpj->contratos', sql, [cnpj14], names=['ni_fornecedor'])
        cur.execute(sql, (cnpj14,))
        rows = cur.fetchall()
        ids = [r["numero_controle_pncp"] for r in rows if r.get("numero_controle_pncp")]
        dbg('SEARCH', 'Contratos encontrados =', len(ids))
        return ids


def parse_vector_text(txt: str) -> Optional[List[float]]:
    """Converte representação textual do pgvector/halfvec para lista de floats.
    Espera formato "[0.1, 0.2, ...]".
    """
    if not txt:
        return None
    txt = txt.strip()
    if not (txt.startswith("[") and txt.endswith("]")):
        return None
    body = txt[1:-1].strip()
    if not body:
        return []
    try:
        return [float(x) for x in body.split(",")]
    except Exception:
        return None


def get_contrato_embeddings(conn, pncp_ids: List[str]) -> List[List[float]]:
    if not pncp_ids:
        return []
    # Uso obrigatório de halfvec(3072)
    sql = f"""
        SELECT embeddings_hv::text AS emb
        FROM public.contrato_emb
        WHERE numero_controle_pncp = ANY(%s)
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        if isdbg('SQL'):
            dbg_sql('load contrato_emb (halfvec)', sql, [pncp_ids], names=['pncp_ids'])
        cur.execute(sql, (pncp_ids,))
        rows = cur.fetchall()
        out: List[List[float]] = []
        for r in rows:
            vec = parse_vector_text(r.get("emb"))
            if vec is not None and len(vec) > 0:
                out.append(vec)
        dbg('SEARCH', 'Embeddings carregados =', len(out))
        return out


def mean_vector(vectors: List[List[float]]) -> Optional[List[float]]:
    if not vectors:
        return None
    dim = len(vectors[0])
    acc = [0.0] * dim
    n = 0
    for v in vectors:
        if len(v) != dim:
            continue
        for i in range(dim):
            acc[i] += v[i]
        n += 1
    if n == 0:
        return None
    return [x / n for x in acc]


def to_vector_literal(vec: List[float]) -> str:
    # Formato literal do pgvector: "[v1,v2,...]"
    return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"


def search_similar_contratacoes(conn, vec_lit: str, top_k: int, timeout_ms: int, sample_pct: float) -> List[dict]:
    # Uso obrigatório de halfvec(3072) na busca
    emb_dim = int(os.environ.get("EMB_DIM", "3072"))
    col = "embeddings_hv"
    cast = f"::halfvec({emb_dim})"

    base_sql = f"""
        SELECT c.numero_controle_pncp,
               c.orgao_entidade_razao_social,
               c.unidade_orgao_municipio_nome,
               c.unidade_orgao_uf_sigla,
               c.objeto_compra,
               c.data_encerramento_proposta,
               (1 - (ce.{col} <=> %s{cast})) AS similarity
        FROM public.contratacao_emb ce
        JOIN public.contratacao c USING (numero_controle_pncp)
        ORDER BY ce.{col} <=> %s{cast} ASC
        LIMIT %s
    """
    if isdbg('SQL'):
        dbg_sql('similarity-search (halfvec)', base_sql, [vec_lit, vec_lit, top_k], names=['vec','vec','top_k'])

    # Sempre tentar usar índice pgvector; desabilitar seqscan localmente
    use_sample_on_timeout = True
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            try:
                cur.execute(f"SET LOCAL statement_timeout = {timeout_ms}")
            except Exception:
                pass
            try:
                cur.execute("SET LOCAL enable_seqscan = off")
            except Exception:
                pass
            # Aviso caso não exista índice IVFFLAT em embeddings_hv
            try:
                with conn.cursor() as icur:
                    icur.execute(
                        """
                        SELECT COUNT(*)
                        FROM pg_indexes
                        WHERE schemaname='public'
                          AND tablename='contratacao_emb'
                          AND indexdef ILIKE '%USING ivfflat%'
                          AND indexdef ILIKE '%(embeddings_hv)%'
                        """
                    )
                    idx_count = icur.fetchone()[0]
                    if not idx_count:
                        logging.warning("Sem índice IVFFLAT em contratacao_emb(embeddings_hv); a busca pode ser lenta.")
            except Exception:
                pass
            cur.execute(base_sql, (vec_lit, vec_lit, top_k))
            return cur.fetchall()
    except pg_errors.QueryCanceled:
        logging.warning("Similarity search cancelada por timeout (%sms)", timeout_ms)
        dbg('SEARCH', 'Timeout na busca; aplicando rollback e fallback por TABLESAMPLE', sample_pct)
        # IMPORTANTE: rollback antes de tentar nova consulta
        try:
            conn.rollback()
        except Exception:
            pass
        # Fallback com TABLESAMPLE para reduzir escopo
        sample_sql = f"""
            WITH sample AS (
                SELECT numero_controle_pncp, {col}
                FROM public.contratacao_emb TABLESAMPLE BERNOULLI ({sample_pct})
            )
            SELECT c.numero_controle_pncp,
                   c.orgao_entidade_razao_social,
                   c.unidade_orgao_municipio_nome,
                   c.unidade_orgao_uf_sigla,
                   c.objeto_compra,
                   c.data_encerramento_proposta,
                   (1 - (s.{col} <=> %s{cast})) AS similarity
            FROM sample s
            JOIN public.contratacao c USING (numero_controle_pncp)
            ORDER BY s.{col} <=> %s{cast} ASC
            LIMIT %s
        """
        if isdbg('SQL'):
            dbg_sql('similarity-search-sample (halfvec)', sample_sql, [vec_lit, vec_lit, top_k], names=['vec','vec','top_k'])
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            try:
                cur.execute(f"SET LOCAL statement_timeout = {timeout_ms}")
            except Exception:
                pass
            try:
                cur.execute("SET LOCAL enable_seqscan = off")
            except Exception:
                pass
            cur.execute(sample_sql, (vec_lit, vec_lit, top_k))
            return cur.fetchall()


# -------------------- Main --------------------

def main():
    load_env()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="Busca por similaridade a partir de CNPJ (v1)")
    parser.add_argument("--cnpj", required=True, help="CNPJ do fornecedor (14 dígitos ou formatado)")
    parser.add_argument("--top-k", type=int, default=30, help="Quantidade de resultados (default=30)")
    parser.add_argument("--timeout-ms", type=int, default=90000, help="Timeout da consulta (ms). Default=90000")
    parser.add_argument("--fallback-sample-pct", type=float, default=2.0, help="TABLESAMPLE pct no fallback. Default=2.0")
    parser.add_argument("--debug", action="store_true", help="Ativa logs detalhados (gvg_debug + info)")
    args = parser.parse_args()

    # Toggle de debug por arg (gvg_debug lê DEBUG=1)
    if args.debug:
        os.environ["DEBUG"] = "1"
        logging.getLogger().setLevel(logging.INFO)

    cnpj14 = normalize_cnpj(args.cnpj)
    if not cnpj14:
        print(json.dumps({"error": "CNPJ inválido; informe 14 dígitos"}, ensure_ascii=False))
        return

    # Uso fixo de halfvec(3072) conforme BDS1_v6
    EMB_TYPE = "halfvec"
    REQ_TIMEOUT = float(os.environ.get("REQUEST_TIMEOUT", "30"))
    dbg('SEARCH', 'Iniciando v1 com', 'cnpj=', cnpj14, 'top_k=', args.top_k, 'emb_type=', EMB_TYPE, 'timeout_ms=', args.timeout_ms, 'fallback_sample_pct=', args.fallback_sample_pct)

    # 1) Company (contexto)
    session = build_session()
    logging.info("Consultando OpenCNPJ (timeout=%ss)...", REQ_TIMEOUT)
    company = fetch_company(session, cnpj14, timeout=REQ_TIMEOUT)
    if args.debug and company:
        # Mostra alguns campos relevantes
        dbg('SEARCH', 'API uf=', company.get('uf'), 'municipio=', company.get('municipio'),
            'capital_social=', company.get('capital_social'),
            'opcao_mei=', company.get('opcao_mei'), 'opcao_simples=', company.get('opcao_simples'))

    # 2) Contratos e embeddings
    logging.info("Conectando ao banco...")
    try:
        conn = get_db_conn()
    except Exception as e:
        logging.error("Falha ao conectar no banco: %s", e)
        print(json.dumps({"error": f"DB connection failed: {e}"}, ensure_ascii=False))
        return
    try:
        with conn:
            pncp_ids = get_contrato_ids_for_cnpj(conn, cnpj14)
            logging.info("Contratos localizados: %s", len(pncp_ids))
            if args.debug and pncp_ids:
                dbg('SEARCH', 'Amostra PNCP IDs:', pncp_ids[:5])
            emb_list = get_contrato_embeddings(conn, pncp_ids)
            logging.info("Embeddings carregados: %s", len(emb_list))
            if args.debug and emb_list:
                dbg('SEARCH', 'Dimensão do 1º embedding:', len(emb_list[0]))
            emb_mean = mean_vector(emb_list)
            if args.debug and emb_mean:
                dbg('SEARCH', 'Perfil CNPJ gerado por média (dim):', len(emb_mean))

            if not emb_mean:
                out = {
                    "company": company,
                    "stats": {
                        "cnpj": cnpj14,
                        "contratos_encontrados": len(pncp_ids),
                        "contratos_com_embedding": len(emb_list),
                        "mensagem": "Sem embeddings de contratos para gerar perfil do CNPJ",
                    },
                    "results": [],
                }
                dbg('SEARCH', 'Sem embeddings de contratos; retornando vazio')
                print(json.dumps(out, ensure_ascii=False, default=str))
                return

            vec_lit = to_vector_literal(emb_mean)
            logging.info("Executando busca por similaridade (top_k=%s, timeout=%sms)...", max(1, int(args.__dict__.get('top_k', 30))), int(args.timeout_ms))
            results = search_similar_contratacoes(conn, vec_lit, max(1, int(args.__dict__.get('top_k', 30))), int(args.timeout_ms), float(args.fallback_sample_pct))
    finally:
        try:
            conn.close()
        except Exception:
            pass

    out = {
        "company": company,
        "stats": {
            "cnpj": cnpj14,
            "contratos_encontrados": len(pncp_ids),
            "contratos_com_embedding": len(emb_list),
            "embedding_dim": len(emb_mean),
        "emb_type": EMB_TYPE,
        },
        "results": results,
    }
    dbg('SEARCH', 'Resultados retornados =', len(results))
    print(json.dumps(out, ensure_ascii=False, default=str))


if __name__ == "__main__":
    main()