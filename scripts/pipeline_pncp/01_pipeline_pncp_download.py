#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Pipeline PNCP – Etapa 01: Download de contratações e itens (BDS1)
- Simples, rápido e sem DEPARA externo (mapeamento inline)
- Compatível com execução local e cron do Render
- Dependências mínimas: requests, psycopg2-binary, python-dotenv
"""

import os
import sys
import re
import json
import math
import time
import datetime as dt
import argparse
from typing import List, Dict, Any, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import psycopg2
from psycopg2.extras import execute_values
from dotenv import load_dotenv

# ---------------------------------------------------------------------
# Configuração de ambiente
# ---------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
V1_ROOT = os.path.dirname(os.path.dirname(SCRIPT_DIR))  # .../v1
LOGS_DIR = os.path.join(SCRIPT_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# Carrega .env local da pasta do pipeline e, como fallback, o .env da raiz v1
load_dotenv(os.path.join(SCRIPT_DIR, ".env"))
load_dotenv(os.path.join(V1_ROOT, ".env"))

DB_CONFIG = {
    "host": os.getenv("SUPABASE_HOST", "localhost"),
    "port": os.getenv("SUPABASE_PORT", "6543"),
    "database": os.getenv("SUPABASE_DBNAME", "postgres"),
    "user": os.getenv("SUPABASE_USER", "postgres"),
    "password": os.getenv("SUPABASE_PASSWORD", ""),
}

MAX_WORKERS_DEFAULT = int(os.getenv("PNCP_MAX_WORKERS", "20"))

# Log em arquivo simples (sem prefixos customizados)
PIPELINE_TIMESTAMP = os.getenv("PIPELINE_TIMESTAMP") or dt.datetime.now().strftime("%Y%m%d_%H%M%S")
LOG_FILE = os.path.join(LOGS_DIR, f"log_{PIPELINE_TIMESTAMP}.log")

def log_line(msg: str) -> None:
    try:
        print(msg, flush=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        # Evitar falhar por causa de logging
        pass

# ---------------------------------------------------------------------
# HTTP client com retry/backoff simples
# ---------------------------------------------------------------------

def build_session() -> requests.Session:
    sess = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=1.5,
        status_forcelist=[408, 429, 500, 502, 503, 504],
        allowed_methods=["HEAD", "GET", "OPTIONS", "GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=32, pool_maxsize=32)
    sess.mount("http://", adapter)
    sess.mount("https://", adapter)
    sess.headers.update({
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124 Safari/537.36",
        "Accept": "application/json",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
    })
    return sess

SESSION = build_session()

# ---------------------------------------------------------------------
# Utilidades de transformação (inline, sem DEPARA)
# ---------------------------------------------------------------------

def to_int(v):
    if v in (None, ""): return None
    try:
        return int(float(v))
    except Exception:
        return None

def to_dec(v):
    if v in (None, ""): return None
    try:
        x = float(v)
        if abs(x) > 9.999e11:  # limite seguro compatível com NUMERIC(15,4)
            return None
        return x
    except Exception:
        return None

def to_bool(v):
    if v in (None, ""): return None
    if isinstance(v, str):
        return v.strip().lower() in {"true", "1", "yes", "t", "sim"}
    return bool(v)

def get_nested(d: Dict[str, Any], path: str):
    cur = d
    for key in path.split('.'):
        if not isinstance(cur, dict):
            return None
        cur = cur.get(key)
    return cur

# ---------------------------------------------------------------------
# Mapeamentos inline API -> BDS1 (apenas campos usados)
# ---------------------------------------------------------------------

CONTRATACAO_FIELDS = [
    ("numeroControlePNCP", "numero_controle_pncp", None),
    ("modoDisputaId", "modo_disputa_id", to_int),
    ("dataAberturaProposta", "data_abertura_proposta", None),
    ("dataEncerramentoProposta", "data_encerramento_proposta", None),
    ("srp", "srp", to_bool),
    ("anoCompra", "ano_compra", to_int),
    ("sequencialCompra", "sequencial_compra", to_int),
    ("processo", "processo", None),
    ("objetoCompra", "objeto_compra", None),
    ("valorTotalHomologado", "valor_total_homologado", to_dec),
    ("dataInclusao", "data_inclusao", None),
    ("dataPublicacaoPncp", "data_publicacao_pncp", None),
    ("dataAtualizacao", "data_atualizacao", None),
    ("numeroCompra", "numero_compra", None),
    ("modalidadeId", "modalidade_id", to_int),
    ("dataAtualizacaoGlobal", "data_atualizacao_global", None),
    ("tipoInstrumentoConvocatorioCodigo", "tipo_instrumento_convocatorio_codigo", None),
    ("valorTotalEstimado", "valor_total_estimado", to_dec),
    ("situacaoCompraId", "situacao_compra_id", to_int),
    ("informacaoComplementar", "informacao_complementar", None),
    ("justificativaPresencial", "justificativa_presencial", None),
    ("linkSistemaOrigem", "link_sistema_origem", None),
    ("linkProcessoEletronico", "link_processo_eletronico", None),
    ("modalidadeNome", "modalidade_nome", None),
    ("modoDisputaNome", "modo_disputa_nome", None),
    ("tipoInstrumentoConvocatorioNome", "tipo_instrumento_convocatorio_nome", None),
    ("situacaoCompraNome", "situacao_compra_nome", None),
    ("existeResultado", "existe_resultado", to_bool),
    ("orcamentoSigilosoCodigo", "orcamento_sigiloso_codigo", to_int),
    ("orcamentoSigilosoDescricao", "orcamento_sigiloso_descricao", None),
    ("usuarioNome", "usuario_nome", None),
    ("fontesOrcamentarias", "fontes_orcamentarias", lambda v: json.dumps(v, ensure_ascii=False) if isinstance(v, list) and v else None),
    # Amparo legal
    ("amparoLegal.codigo", "amparo_legal_codigo", None),
    ("amparoLegal.nome", "amparo_legal_nome", None),
    ("amparoLegal.descricao", "amparo_legal_descricao", None),
    # Orgao Entidade
    ("orgaoEntidade.cnpj", "orgao_entidade_cnpj", None),
    ("orgaoEntidade.razaoSocial", "orgao_entidade_razao_social", None),
    ("orgaoEntidade.poderId", "orgao_entidade_poder_id", to_int),
    ("orgaoEntidade.esferaId", "orgao_entidade_esfera_id", to_int),
    # Unidade Orgao
    ("unidadeOrgao.ufNome", "unidade_orgao_uf_nome", None),
    ("unidadeOrgao.ufSigla", "unidade_orgao_uf_sigla", None),
    ("unidadeOrgao.municipioNome", "unidade_orgao_municipio_nome", None),
    ("unidadeOrgao.codigoUnidade", "unidade_orgao_codigo_unidade", None),
    ("unidadeOrgao.nomeUnidade", "unidade_orgao_nome_unidade", None),
    ("unidadeOrgao.codigoIbge", "unidade_orgao_codigo_ibge", None),
    # Orgao Sub-rogado
    ("orgaoSubRogado.cnpj", "orgao_subrogado_cnpj", None),
    ("orgaoSubRogado.razaoSocial", "orgao_subrogado_razao_social", None),
    ("orgaoSubRogado.poderId", "orgao_subrogado_poder_id", to_int),
    ("orgaoSubRogado.esferaId", "orgao_subrogado_esfera_id", to_int),
    # Unidade Sub-rogada
    ("unidadeSubRogada.ufNome", "unidade_subrogada_uf_nome", None),
    ("unidadeSubRogada.ufSigla", "unidade_subrogada_uf_sigla", None),
    ("unidadeSubRogada.municipioNome", "unidade_subrogada_municipio_nome", None),
    ("unidadeSubRogada.codigoUnidade", "unidade_subrogada_codigo_unidade", None),
    ("unidadeSubRogada.nomeUnidade", "unidade_subrogada_nome_unidade", None),
    ("unidadeSubRogada.codigoIbge", "unidade_subrogada_codigo_ibge", None),
]

ITEM_FIELDS = [
    # numero_controle_pncp é injetado pelo script
    ("numeroItem", "numero_item", to_int),
    ("descricao", "descricao_item", None),
    ("materialOuServico", "material_ou_servico", None),
    ("valorUnitarioEstimado", "valor_unitario_estimado", to_dec),
    ("valorTotal", "valor_total_estimado", to_dec),
    ("quantidade", "quantidade_item", to_dec),
    ("unidadeMedida", "unidade_medida", None),
    ("itemCategoriaId", "item_categoria_id", to_int),
    ("itemCategoriaNome", "item_categoria_nome", None),
    ("criterioJulgamentoId", "criterio_julgamento_id", to_int),
    ("situacaoCompraItem", "situacao_item", None),
    ("tipoBeneficio", "tipo_beneficio", None),
    ("dataInclusao", "data_inclusao", None),
    ("dataAtualizacao", "data_atualizacao", None),
    ("ncmNbsCodigo", "ncm_nbs_codigo", None),
    ("catalogo", "catalogo", None),
]

# ---------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------

def get_conn(max_attempts: int = 3, retry_delay: int = 5):
    attempt = 1
    while attempt <= max_attempts:
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            conn.set_session(autocommit=False)
            return conn
        except psycopg2.Error as e:
            log_line(f"Erro ao conectar ao banco (tentativa {attempt}/{max_attempts}): {e}")
            if attempt < max_attempts:
                time.sleep(retry_delay)
                attempt += 1
            else:
                raise


def ensure_conn_open(conn):
    """Garante que a conexão esteja aberta; tenta um ping simples e reconecta se necessário."""
    try:
        if conn.closed:
            return get_conn()
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        return conn
    except Exception:
        try:
            conn.close()
        except Exception:
            pass
        return get_conn()


def get_last_processed_date(conn) -> str | None:
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT value FROM system_config WHERE key = 'last_processed_date'")
            row = cur.fetchone()
            return row[0] if row else None
    except Exception as e:
        log_line(f"Aviso ao ler last_processed_date: {e}")
        return None


def save_last_processed_date(conn, date_str: str) -> None:
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO system_config (key, value, description, updated_at)
                VALUES ('last_processed_date', %s, 'Última data processada (pipeline 01)', CURRENT_TIMESTAMP)
                ON CONFLICT (key)
                DO UPDATE SET value = EXCLUDED.value, updated_at = CURRENT_TIMESTAMP
                """,
                (date_str,),
            )
        conn.commit()
    except Exception as e:
        conn.rollback()
        log_line(f"Erro ao salvar last_processed_date: {e}")

# ---------------------------------------------------------------------
# Normalização inline (API -> BDS1)
# ---------------------------------------------------------------------

def normalize_contratacao(api_obj: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    for api_key, db_key, fn in CONTRATACAO_FIELDS:
        val = get_nested(api_obj, api_key) if "." in api_key else api_obj.get(api_key)
        if fn:
            val = fn(val)
        out[db_key] = val
    return out


def normalize_item(api_obj: Dict[str, Any], numero_controle_pncp: str) -> Dict[str, Any]:
    out = {"numero_controle_pncp": numero_controle_pncp}
    for api_key, db_key, fn in ITEM_FIELDS:
        val = api_obj.get(api_key)
        if fn:
            val = fn(val)
        out[db_key] = val
    return out

# ---------------------------------------------------------------------
# Busca API
# ---------------------------------------------------------------------

BASE_CONTRATACOES = "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"
BASE_ITENS = "https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/compras/{ano}/{seq}/itens"


def fetch_api_modalidade_totals(date_str: str, codigo: int) -> Tuple[int, int]:
    """Busca apenas a 1ª página para obter totalRegistros/totalPaginas de uma modalidade/dia.
    Retorna (totalRegistros, totalPaginas). Em caso de 204, retorna (0, 0).
    """
    params = {
        "dataInicial": date_str,
        "dataFinal": date_str,
        "codigoModalidadeContratacao": codigo,
        "pagina": 1,
        "tamanhoPagina": 10,  # mínimo aceito pela API
    }
    res = SESSION.get(BASE_CONTRATACOES, params=params, timeout=60)
    if res.status_code == 204:
        return 0, 0
    if res.status_code != 200:
        log_line(f"Modalidade {codigo}: HTTP {res.status_code} (totais)")
        return 0, 0
    jd = res.json() or {}
    total_reg = int(jd.get("totalRegistros", 0) or 0)
    total_pag = int(jd.get("totalPaginas", 0) or 0)
    return total_reg, total_pag


def fetch_contratacoes_by_modalidade(date_str: str, codigo: int) -> List[Dict[str, Any]]:
    params = {
        "dataInicial": date_str,
        "dataFinal": date_str,
        "codigoModalidadeContratacao": codigo,
        "pagina": 1,
        "tamanhoPagina": 50,
    }
    res = SESSION.get(BASE_CONTRATACOES, params=params, timeout=60)
    if res.status_code == 204:
        return []
    if res.status_code != 200:
        log_line(f"Modalidade {codigo}: HTTP {res.status_code}")
        return []
    data = res.json() or {}
    out = list(data.get("data", []))
    total_pag = int(data.get("totalPaginas", 1) or 1)
    for page in range(2, total_pag + 1):
        params["pagina"] = page
        r = SESSION.get(BASE_CONTRATACOES, params=params, timeout=60)
        if r.status_code != 200:
            break
        jd = r.json() or {}
        out.extend(jd.get("data", []))
    return out


def fetch_contratacoes_pages(date_str: str, codigo: int, tamanho_pagina: int = 50):
    """Gera páginas de contratações para a modalidade/código informados.
    Retorna via gerador listas de registros por página.
    """
    params = {
        "dataInicial": date_str,
        "dataFinal": date_str,
        "codigoModalidadeContratacao": codigo,
        "pagina": 1,
        "tamanhoPagina": tamanho_pagina,
    }
    res = SESSION.get(BASE_CONTRATACOES, params=params, timeout=60)
    if res.status_code == 204:
        return
    if res.status_code != 200:
        log_line(f"Modalidade {codigo}: HTTP {res.status_code}")
        return
    jd = res.json() or {}
    data = list(jd.get("data", []) or [])
    total_pag = int(jd.get("totalPaginas", 0) or 0)
    yield data
    for page in range(2, total_pag + 1):
        params["pagina"] = page
        r = SESSION.get(BASE_CONTRATACOES, params=params, timeout=60)
        if r.status_code != 200:
            break
        jd = r.json() or {}
        yield list(jd.get("data", []) or [])


def partition_list(lst: List[Any], max_workers: int) -> List[List[Any]]:
    if not lst:
        return []
    workers = max(1, min(max_workers, len(lst)))
    size = math.ceil(len(lst) / workers)
    return [lst[i:i + size] for i in range(0, len(lst), size)]


def parse_numero_controle(numero: str) -> Tuple[str, str, str] | None:
    # formato esperado: CNPJ-???-SEQ/ANO (ex: 01123456000199-123-000123/2025)
    if not isinstance(numero, str):
        return None
    if not re.match(r"^\d+-\d+-\d+/\d+$", numero):
        return None
    try:
        cnpj, _, right = numero.split("-")
        seq, ano = right.split("/")
        seq_clean = str(int(seq))  # remove zeros à esquerda
        return cnpj, ano, seq_clean
    except Exception:
        return None


def fetch_itens_batch(numeros: List[str]) -> List[Dict[str, Any]]:
    itens: List[Dict[str, Any]] = []
    for numero in numeros:
        parsed = parse_numero_controle(numero)
        if not parsed:
            continue
        cnpj, ano, seq = parsed
        url = BASE_ITENS.format(cnpj=cnpj, ano=ano, seq=seq)
        r = SESSION.get(url, timeout=60)
        if r.status_code == 200:
            jd = r.json() or []
            for it in jd:
                it["numero_controle_pncp"] = numero
                itens.append(it)
        # 404: sem itens; demais códigos: silenciar para seguir
    return itens

# ---------------------------------------------------------------------
# Inserções no banco
# ---------------------------------------------------------------------

def insert_contratacoes(conn, contratos: List[Dict[str, Any]]) -> int:
    if not contratos:
        return 0
    cols = [db for _, db, _ in CONTRATACAO_FIELDS]
    values = []
    for c in contratos:
        row = []
        for col in cols:
            v = c.get(col)
            if isinstance(v, (dict, list)):
                v = json.dumps(v, ensure_ascii=False)
            row.append(v)
        values.append(tuple(row))
    sql = f"""
        INSERT INTO contratacao ({', '.join(cols)})
        VALUES %s
        ON CONFLICT (numero_controle_pncp) DO NOTHING
        RETURNING 1
    """
    inserted = 0
    with conn.cursor() as cur:
        execute_values(cur, sql, values, page_size=1000)
        rows = cur.fetchall() or []
        inserted += len(rows)
    conn.commit()
    return inserted


def insert_itens(conn, itens_norm: List[Dict[str, Any]]) -> int:
    if not itens_norm:
        return 0
    cols = ["numero_controle_pncp"] + [db for _, db, _ in ITEM_FIELDS]
    values = []
    for it in itens_norm:
        row = []
        for col in cols:
            v = it.get(col)
            if isinstance(v, (dict, list)):
                v = json.dumps(v, ensure_ascii=False)
            row.append(v)
        values.append(tuple(row))
    sql = f"""
        INSERT INTO item_contratacao ({', '.join(cols)})
        VALUES %s
        ON CONFLICT (numero_controle_pncp, numero_item) DO NOTHING
        RETURNING 1
    """
    total_inserted = 0
    batch = 3000
    with conn.cursor() as cur:
        if len(values) > batch:
            for i in range(0, len(values), batch):
                execute_values(cur, sql, values[i:i+batch], page_size=1000)
                rows = cur.fetchall() or []
                total_inserted += len(rows)
        else:
            execute_values(cur, sql, values, page_size=1000)
            rows = cur.fetchall() or []
            total_inserted += len(rows)
    conn.commit()
    return total_inserted


def insert_pipeline_run_stats(conn, stage: str, date_ref: str, inserted_contr: int, inserted_itens: int) -> None:
    """Registra estatísticas de execução por data/etapa."""
    try:
        # Usar conexão curta própria para evitar efeitos de transação anterior
        short_conn = get_conn()
        with short_conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pipeline_run_stats (stage, date_ref, inserted_contratacoes, inserted_itens)
                VALUES (%s, %s, %s, %s)
                """,
                (stage, date_ref, int(inserted_contr or 0), int(inserted_itens or 0)),
            )
        short_conn.commit()
    except Exception as e:
        log_line(f"Aviso: falha ao registrar pipeline_run_stats ({stage} {date_ref}): {e}")
    finally:
        try:
            short_conn.close()
        except Exception:
            pass

# ---------------------------------------------------------------------
# Processamento por data
# ---------------------------------------------------------------------

def process_date(conn, date_str: str, max_workers: int, refresh_items: bool = False) -> Tuple[int, int]:
    log_line(f"Processando {date_str}...")

    # 1) Contagem no BD por modalidade
    db_counts: Dict[int, int] = {}
    with conn.cursor() as cur:
        for cod in range(1, 15):
            cur.execute(
                """
                SELECT COUNT(*)
                  FROM contratacao
                 WHERE DATE(data_publicacao_pncp) = %s::date
                   AND modalidade_id = %s
                """,
                (date_str, str(cod)),
            )
            db_counts[cod] = cur.fetchone()[0]

    # 2) Ler totais da API por modalidade com ThreadPool fixo de 14
    mod_info: Dict[int, Tuple[int, int]] = {}  # cod -> (api_total, total_paginas)
    with ThreadPoolExecutor(max_workers=14) as ex:
        futures = {ex.submit(fetch_api_modalidade_totals, date_str, cod): cod for cod in range(1, 15)}
        mod_total = len(futures)
        mod_done = 0
        for fut in as_completed(futures):
            cod = futures[fut]
            api_total, total_pag = 0, 0
            try:
                api_total, total_pag = fut.result()
            except Exception as e:
                log_line(f"Erro ao ler totais da modalidade {cod}: {e}")
            mod_info[cod] = (api_total, total_pag)
            db_total = db_counts.get(cod, 0)
            missing = max(0, api_total - db_total)
            mod_done += 1
            pct = int((mod_done * 100) / max(1, mod_total))
            fill = int(round(pct * 20 / 100))
            bar = "█" * fill + "░" * (20 - fill)
            log_line(f"1) Contagem de Contratações: {pct}% [{bar}] ({mod_done}/{mod_total}) (mod {cod}: API={api_total}, DB={db_total}, +{missing})")

    # Espaço entre fase 1 (totais) e fase 2 (páginas)
    log_line("")

    # Se não houver faltantes e não for para forçar itens, encerra cedo
    total_missing = 0
    for cod in range(1, 15):
        api_total, _ = mod_info.get(cod, (0, 0))
        db_total = db_counts.get(cod, 0)
        total_missing += max(0, api_total - db_total)

    if total_missing == 0 and not refresh_items:
        log_line("Sem faltantes; pulando processamento desta data.")
        insert_pipeline_run_stats(conn, stage="01", date_ref=date_str, inserted_contr=0, inserted_itens=0)
        return 0, 0

    # 3) Processar cada modalidade em paralelo (14 workers fixos) – apenas CONTRATAÇÕES
    def worker_modalidade(cod: int) -> Tuple[int, int]:
        api_total, total_pag = mod_info.get(cod, (0, 0))
        db_total = db_counts.get(cod, 0)
        missing = max(0, api_total - db_total)
        inserted_c = 0
        local_conn = get_conn()
        try:
            numeros_baixados: List[str] = []
            # Quando há faltantes, baixar página a página e inserir imediatamente
            if missing > 0 and total_pag > 0:
                page_idx = 0
                last_pct = -1  # baseado em inserted_c/missing
                for page_data in fetch_contratacoes_pages(date_str, cod, tamanho_pagina=50):
                    page_idx += 1
                    if not page_data:
                        continue
                    # Dedup da página
                    uniq: Dict[str, Dict[str, Any]] = {}
                    for c_raw in page_data:
                        nc = c_raw.get("numeroControlePNCP")
                        if nc and nc not in uniq:
                            uniq[nc] = c_raw
                    page_unique = list(uniq.values())
                    numeros = [c.get("numeroControlePNCP") for c in page_unique if c.get("numeroControlePNCP")]
                    numeros_baixados.extend(numeros)
                    # Inserir contratações da página
                    contratos_norm = [normalize_contratacao(c) for c in page_unique]
                    try:
                        inserted_c += insert_contratacoes(local_conn, contratos_norm)
                    except Exception as e:
                        log_line(f"Modalidade {cod} pág {page_idx}: erro ao inserir contratações: {e}")
                        # tentar reconectar e seguir
                        try:
                            local_conn.close()
                        except Exception:
                            pass
                        local_conn = get_conn()
                    # Progresso por CONTRATOS faltantes (não por páginas)
                    if missing > 0:
                        pct = min(100, int((inserted_c * 100) / max(1, missing)))
                        if pct == 100 or pct - last_pct >= 10:
                            fill = int(round(pct * 20 / 100))
                            bar = "█" * fill + "░" * (20 - fill)
                            log_line(f"2) Download Contratações: {pct}% [{bar}] (mod {cod}: {inserted_c}/{missing})")
                            last_pct = pct

            # Fase 3 (itens) será executada depois para todas as modalidades
        finally:
            try:
                local_conn.close()
            except Exception:
                pass
        return inserted_c, 0

    total_inserted_c = 0
    total_inserted_i = 0
    with ThreadPoolExecutor(max_workers=14) as ex:
        futures = {ex.submit(worker_modalidade, cod): cod for cod in range(1, 15)}
        for fut in as_completed(futures):
            cod = futures[fut]
            try:
                c_add, i_add = fut.result()
                total_inserted_c += c_add
            except Exception as e:
                log_line(f"Erro na modalidade {cod}: {e}")

    # Espaço entre fase 2 (contratações) e fase 3 (itens)
    log_line("")

    # 4) Fase 3 – ITENS pendentes por modalidade (ordem estrita após fase 2)
    def worker_itens(cod: int) -> int:
        inserted_i_local = 0
        local_conn = get_conn()
        try:
            with local_conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT c.numero_controle_pncp
                      FROM contratacao c
                     WHERE DATE(c.data_publicacao_pncp) = %s::date
                       AND c.modalidade_id = %s
                       AND NOT EXISTS (
                           SELECT 1 FROM item_contratacao i
                            WHERE i.numero_controle_pncp = c.numero_controle_pncp
                       )
                    """,
                    (date_str, str(cod)),
                )
                pendentes = [r[0] for r in cur.fetchall()]
            total_p = len(pendentes)
            if total_p == 0:
                return 0
            processed = 0
            last_pct_loc = -1
            chunks = [pendentes[i:i+200] for i in range(0, total_p, 200)]
            for ch in chunks:
                try:
                    itens_raw = fetch_itens_batch(ch)
                    itens_norm: List[Dict[str, Any]] = []
                    seen: set[Tuple[str, int]] = set()
                    for it in itens_raw:
                        nc = it.get("numero_controle_pncp")
                        ni = to_int(it.get("numeroItem"))
                        if not nc or ni is None:
                            continue
                        key = (nc, ni)
                        if key in seen:
                            continue
                        seen.add(key)
                        itens_norm.append(normalize_item(it, nc))
                    inserted_i_local += insert_itens(local_conn, itens_norm)
                except Exception as e:
                    log_line(f"Modalidade {cod}: erro ao inserir itens (pendentes): {e}")
                    try:
                        local_conn.close()
                    except Exception:
                        pass
                    local_conn = get_conn()
                processed += len(ch)
                # Progresso por CONTRATOS pendentes (não por páginas/chunks)
                pct_loc = min(100, int((processed * 100) / max(1, total_p)))
                if pct_loc == 100 or pct_loc - last_pct_loc >= 10:
                    fill = int(round(pct_loc * 20 / 100))
                    bar = "█" * fill + "░" * (20 - fill)
                    log_line(f"3) Download Itens: {pct_loc}% [{bar}] (mod {cod}: {processed}/{total_p})")
                    last_pct_loc = pct_loc
        finally:
            try:
                local_conn.close()
            except Exception:
                pass
        return inserted_i_local

    if refresh_items or total_inserted_c > 0:
        with ThreadPoolExecutor(max_workers=14) as ex:
            futures = {ex.submit(worker_itens, cod): cod for cod in range(1, 15)}
            for fut in as_completed(futures):
                cod = futures[fut]
                try:
                    i_add = fut.result()
                    total_inserted_i += i_add
                except Exception as e:
                    log_line(f"Erro na modalidade (itens) {cod}: {e}")

    log_line(f"Inseridos: {total_inserted_c} contratações, {total_inserted_i} itens")

    # 4) Registrar estatísticas da execução para a data/etapa 01
    insert_pipeline_run_stats(conn, stage="01", date_ref=date_str, inserted_contr=total_inserted_c, inserted_itens=total_inserted_i)

    return total_inserted_c, total_inserted_i

# ---------------------------------------------------------------------
# Datas
# ---------------------------------------------------------------------

def build_dates(start: str | None, end: str | None) -> List[str]:
    if start is None:
        start = dt.datetime.now().strftime("%Y%m%d")
    if end is None:
        # Sem --end, processa até hoje (múltiplos dias)
        end = dt.datetime.now().strftime("%Y%m%d")
    dates: List[str] = []
    cur = dt.datetime.strptime(start, "%Y%m%d")
    end_dt = dt.datetime.strptime(end, "%Y%m%d")
    while cur <= end_dt:
        dates.append(cur.strftime("%Y%m%d"))
        cur += dt.timedelta(days=1)
    return dates

# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Pipeline PNCP 01 – Download")
    parser.add_argument("--start", help="Data inicial YYYYMMDD")
    parser.add_argument("--end", help="Data final YYYYMMDD")
    parser.add_argument("--test", help="Rodar apenas uma data YYYYMMDD")
    parser.add_argument("--workers", type=int, default=MAX_WORKERS_DEFAULT, help="Máximo de workers")
    parser.add_argument("--refresh-items", action="store_true", help="Força verificação e (re)download de itens mesmo sem novos contratos")
    args = parser.parse_args()

    log_line("[1/3] DOWNLOAD PNCP INICIADO (LPD)")

    conn = get_conn()
    try:
        if args.test:
            dates = [args.test]
            log_line(f"Modo teste: {args.test}")
        else:
            # LPD = last_processed_date
            last_date = get_last_processed_date(conn)
            if not last_date:
                last_date = dt.datetime.now().strftime("%Y%m%d")
                save_last_processed_date(conn, last_date)
            log_line(f"LPD atual: {last_date}")
            if args.start:
                start = args.start
            else:
                today = dt.datetime.now().strftime("%Y%m%d")
                if last_date == today:
                    # Opção B: incluir o dia atual quando LPD == hoje
                    start = last_date
                else:
                    last_dt = dt.datetime.strptime(last_date, "%Y%m%d")
                    start = (last_dt + dt.timedelta(days=1)).strftime("%Y%m%d")
            end = args.end or dt.datetime.now().strftime("%Y%m%d")
            dates = build_dates(start, end)

        if dates:
            log_line(f"Intervalo de datas para 01 (LPD): {dates[0]} .. {dates[-1]} ({len(dates)})")

        if not dates:
            log_line("Nenhuma data para processar.")
            return

        total_c = 0
        total_i = 0
        failed: List[str] = []
        for d in dates:
            try:
                conn = ensure_conn_open(conn)
                c, i = process_date(conn, d, max_workers=max(1, args.workers), refresh_items=bool(args.refresh_items))
                total_c += c
                total_i += i
                if not args.test:
                    conn = ensure_conn_open(conn)
                    save_last_processed_date(conn, d)
                    log_line(f"LPD atualizado: {d}")
            except Exception as e:
                log_line(f"Erro ao processar data {d}: {e}")
                try:
                    conn.rollback()
                except Exception:
                    pass
                failed.append(d)

        log_line("DOWNLOAD PNCP FINALIZADO")
        log_line(f"Datas: {len(dates)} | Contratações: {total_c} | Itens: {total_i}")
        if failed:
            log_line(f"Falhas em {len(failed)} datas: {', '.join(failed)}")
        log_line(f"Log: {os.path.basename(LOG_FILE)}")

    finally:
        try:
            conn.close()
        except Exception:
            pass


if __name__ == "__main__":
    main()
