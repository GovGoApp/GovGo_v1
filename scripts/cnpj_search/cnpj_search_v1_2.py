#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cnpj_search_v1_2

Extensão da versão v1_1 adicionando blending geográfico opcional (--pos) entre similaridade semântica e proximidade espacial.

Pipeline geográfico (ativado somente com --pos):
1. Carrega amostra de embeddings de contratos do CNPJ para gerar vetor médio (perfil semântico).
2. Busca candidatos semânticos ampliados (top-candidates) via embeddings_hv (halfvec(3072)).
3. Calcula centróide geográfico do fornecedor (média lat/lon dos municípios dos seus contratos amostrados - join em public.municipios).
4. Enriquecimento dos candidatos: latitude/longitude do município do órgão (join em public.municipios).
5. Distância Haversine (km) entre centróide fornecedor e cada candidato.
6. Similaridade geográfica: sim_geo = exp(-dist_km / geo_tau). dist faltante => sim_geo=0.
7. Blending final: final_score = (1 - geo_weight) * sim_sem + geo_weight * sim_geo.
8. Reordena resultados por final_score e exibe métricas agregadas.

Defaults:
- Sem geografia por padrão (não passa --pos => ranking somente semântico).
- --geo-weight=0.25, --geo-tau=300, --top-candidates=800.

Uso rápido:
- Interativo: python scripts/cnpj_search/cnpj_search_v1_2.py
- Direto:     python scripts/cnpj_search/cnpj_search_v1_2.py --cnpj 11164874000109 --pos
"""
import os
import re
import json
import argparse
import logging
from typing import List, Optional, Tuple, Dict, Any
from datetime import datetime
import math
from time import perf_counter

from dotenv import load_dotenv
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2 import errors as pg_errors

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt
from rich.progress import Progress, SpinnerColumn, TextColumn

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# -------------------- Console --------------------
console = Console(width=96)

# -------------------- gvg_debug (resiliente) --------------------
import sys
from pathlib import Path
try:
    _here = Path(__file__).resolve()
    _root = _here.parents[2]
    _gvg_path = _root / "search" / "gvg_browser"
    if _gvg_path.exists() and str(_gvg_path) not in sys.path:
        sys.path.insert(0, str(_gvg_path))
except Exception:
    pass
try:
    from search.gvg_browser.gvg_debug import debug_log as dbg, is_debug_enabled as isdbg, debug_sql as dbg_sql  # type: ignore
except Exception:
    try:
        from gvg_debug import debug_log as dbg, is_debug_enabled as isdbg, debug_sql as dbg_sql  # type: ignore
    except Exception:
        def dbg(area: str, *args, **kwargs):
            return None
        def isdbg(area: str) -> bool:
            return False
        def dbg_sql(label: str, sql: str, params=None, names=None):
            return None

API_BASE = "https://api.opencnpj.org"

# -------------------- Ambiente --------------------

def load_env():
    env_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".env"))
    load_dotenv(env_path)
    dbg('SEARCH', 'ENV carregado de', env_path)


def get_db_conn():
    return psycopg2.connect(
        host=os.environ.get("SUPABASE_HOST"),
        port=int(os.environ.get("SUPABASE_PORT", "6543")),
        dbname=os.environ.get("SUPABASE_DBNAME"),
        user=os.environ.get("SUPABASE_USER"),
        password=os.environ.get("SUPABASE_PASSWORD"),
    )

# -------------------- Util CNPJ --------------------

def normalize_cnpj(cnpj: str) -> Optional[str]:
    if not cnpj:
        return None
    digits = re.sub(r"\D", "", str(cnpj))
    return digits if len(digits) == 14 else None


def format_cnpj(cnpj14: str) -> str:
    if not cnpj14 or len(cnpj14) != 14 or not cnpj14.isdigit():
        return cnpj14 or ""
    return f"{cnpj14[0:2]}.{cnpj14[2:5]}.{cnpj14[5:8]}/{cnpj14[8:12]}-{cnpj14[12:14]}"

# -------------------- HTTP / OpenCNPJ --------------------

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


def fetch_company(session: requests.Session, cnpj: str, timeout: float) -> Optional[dict]:
    url = f"{API_BASE}/{cnpj}"
    try:
        resp = session.get(url, timeout=timeout)
    except requests.RequestException as e:
        logging.info("OpenCNPJ indisponível: %s", e)
        return None
    if resp.status_code == 200:
        try:
            return resp.json()
        except Exception:
            return None
    return None

# -------------------- Embeddings / Vetores --------------------

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
        return [r["numero_controle_pncp"] for r in rows if r.get("numero_controle_pncp")]


def parse_vector_text(txt: str) -> Optional[List[float]]:
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


def get_contrato_embeddings_sampled(conn, cnpj14: str, sample_n: int) -> List[List[float]]:
    if not cnpj14 or sample_n <= 0:
        return []
    sql = """
        SELECT ce.embeddings_hv::text AS emb, c.unidade_orgao_codigo_ibge
        FROM public.contrato c
        JOIN public.contrato_emb ce USING (numero_controle_pncp)
        WHERE c.ni_fornecedor = %s
        ORDER BY random()
        LIMIT %s
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        if isdbg('SQL'):
            dbg_sql('load contrato_emb sample (halfvec + ibge)', sql, [cnpj14, sample_n], names=['cnpj','limit'])
        t0 = perf_counter()
        cur.execute(sql, (cnpj14, sample_n))
        rows = cur.fetchall()
        dt_ms = (perf_counter() - t0) * 1000
        out: List[List[float]] = []
        ibges: List[int] = []
        for r in rows:
            vec = parse_vector_text(r.get("emb"))
            if vec is not None and len(vec) > 0:
                out.append(vec)
            ibge = r.get("unidade_orgao_codigo_ibge")
            if ibge is not None:
                try:
                    ibges.append(int(ibge))
                except Exception:
                    pass
        logging.info("Amostra contratos: embeddings=%s, ibge_codes=%s distintos=%s tempo=%.1fms", len(out), len(ibges), len(set(ibges)), dt_ms)
        return out, ibges


def get_all_ibge_for_cnpj(conn, cnpj14: str) -> List[Any]:
    """Retorna todos os códigos IBGE (DISTINCT) dos contratos do CNPJ."""
    sql = """
        SELECT DISTINCT unidade_orgao_codigo_ibge AS ibge
        FROM public.contrato
        WHERE ni_fornecedor = %s AND unidade_orgao_codigo_ibge IS NOT NULL
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        if isdbg('SQL'):
            dbg_sql('cnpj->ibge_all', sql, [cnpj14], names=['ni_fornecedor'])
        t0 = perf_counter()
        cur.execute(sql, (cnpj14,))
        rows = cur.fetchall()
        dt_ms = (perf_counter() - t0) * 1000
        vals: List[Any] = [r.get('ibge') for r in rows if r.get('ibge') is not None]
        logging.info("IBGE all: distintos=%s tempo=%.1fms", len(vals), dt_ms)
        return vals


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
    return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"

# -------------------- Similaridade semântica principal --------------------

def search_similar_contratacoes(conn, vec_lit: str, top_k: int, timeout_ms: int, sample_pct: float) -> List[dict]:
    emb_dim = int(os.environ.get("EMB_DIM", "3072"))
    col = "embeddings_hv"
    cast = f"::halfvec({emb_dim})"
    base_sql = f"""
        WITH params AS (
            SELECT %s{cast} AS q
        ), topk AS (
            SELECT ce.numero_controle_pncp,
                   (ce.{col} <=> (SELECT q FROM params)) AS dist
            FROM public.contratacao_emb ce
            ORDER BY dist ASC
            LIMIT %s
        )
        SELECT c.numero_controle_pncp,
               c.orgao_entidade_razao_social,
               c.unidade_orgao_municipio_nome,
               c.unidade_orgao_uf_sigla,
               c.unidade_orgao_codigo_ibge,
               c.objeto_compra,
               c.data_encerramento_proposta,
               c.valor_total_homologado,
               c.link_sistema_origem,
               (1 - topk.dist) AS similarity
        FROM topk
        JOIN public.contratacao c USING (numero_controle_pncp)
        ORDER BY topk.dist ASC
    """
    if isdbg('SQL'):
        dbg_sql('similarity-search (halfvec)', base_sql, [vec_lit, top_k], names=['vec','top_k'])
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
            probes = os.environ.get("IVFFLAT_PROBES")
            if probes and probes.isdigit():
                try:
                    cur.execute(f"SET LOCAL ivfflat.probes = {int(probes)}")
                    logging.info("ivfflat.probes=%s aplicado", int(probes))
                except Exception:
                    pass
            logging.info("Executando busca (IVFFLAT) top_k=%s timeout_ms=%s", top_k, timeout_ms)
            cur.execute(base_sql, (vec_lit, top_k))
            return cur.fetchall()
    except pg_errors.QueryCanceled:
        logging.warning("Similarity search cancelada por timeout (%sms)", timeout_ms)
        try:
            conn.rollback()
        except Exception:
            pass
        sample_sql = f"""
            WITH params AS (
                SELECT %s{cast} AS q
            ), sample AS (
                SELECT numero_controle_pncp, {col}
                FROM public.contratacao_emb TABLESAMPLE BERNOULLI ({sample_pct})
            ), topk AS (
                SELECT s.numero_controle_pncp,
                       (s.{col} <=> (SELECT q FROM params)) AS dist
                FROM sample s
                ORDER BY dist ASC
                LIMIT %s
            )
            SELECT c.numero_controle_pncp,
                   c.orgao_entidade_razao_social,
                   c.unidade_orgao_municipio_nome,
                   c.unidade_orgao_uf_sigla,
                   c.unidade_orgao_codigo_ibge,
                   c.objeto_compra,
                   c.data_encerramento_proposta,
                   c.valor_total_homologado,
                   c.link_sistema_origem,
                   (1 - topk.dist) AS similarity
            FROM topk
            JOIN public.contratacao c USING (numero_controle_pncp)
            ORDER BY topk.dist ASC
        """
        if isdbg('SQL'):
            dbg_sql('similarity-search-sample (halfvec)', sample_sql, [vec_lit, top_k], names=['vec','top_k'])
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            try:
                cur.execute(f"SET LOCAL statement_timeout = {timeout_ms}")
            except Exception:
                pass
            try:
                cur.execute("SET LOCAL enable_seqscan = off")
            except Exception:
                pass
            logging.info("Executando fallback TABLESAMPLE=%.2f%% top_k=%s", sample_pct, top_k)
            cur.execute(sample_sql, (vec_lit, top_k))
            return cur.fetchall()

# -------------------- Geografia --------------------

def load_municipios_coords(conn, ibge_codes: List[Any]) -> Dict[str, Tuple[float, float]]:
    if not ibge_codes:
        return {}
    # Normaliza para texto e remove inválidos/duplicados
    clean_codes_set: set[str] = set()
    for c in ibge_codes:
        if c is None:
            continue
        try:
            clean_codes_set.add(str(int(c)))  # força numérico como string (sem zeros à esquerda)
        except Exception:
            try:
                s = str(c).strip()
                if s:
                    clean_codes_set.add(s)
            except Exception:
                continue
    unique_codes = list(clean_codes_set)
    sql = """
        SELECT municipio, lat, lon
        FROM public.municipios
        WHERE municipio::text = ANY(%s)
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        if isdbg('SQL'):
            dbg_sql('load municipios coords (lat/lon)', sql, [unique_codes], names=['ibge_codes'])
        t0 = perf_counter()
        cur.execute(sql, (unique_codes,))
        rows = cur.fetchall()
        dt_ms = (perf_counter() - t0) * 1000
        logging.info("Municipios coords: solicitados=%s, encontrados=%s, tempo=%.1fms", len(unique_codes), len(rows), dt_ms)
        out: Dict[str, Tuple[float, float]] = {}
        for r in rows:
            lat = r.get('lat')
            lon = r.get('lon')
            if lat is not None and lon is not None:
                try:
                    out[str(r['municipio'])] = (float(lat), float(lon))
                except Exception:
                    pass
        return out


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    # Raio médio da Terra em km
    R = 6371.0
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2)**2
    c = 2*math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def compute_centroid(coords: List[Tuple[float, float]]) -> Optional[Tuple[float, float]]:
    if not coords:
        return None
    sx = 0.0
    sy = 0.0
    n = 0
    for (lat, lon) in coords:
        if lat is None or lon is None:
            continue
        sx += lat
        sy += lon
        n += 1
    if n == 0:
        return None
    return (sx / n, sy / n)


def compute_median(values: List[float]) -> Optional[float]:
    arr = [float(v) for v in values if v is not None]
    if not arr:
        return None
    arr.sort()
    n = len(arr)
    mid = n // 2
    if n % 2 == 1:
        return arr[mid]
    return (arr[mid - 1] + arr[mid]) / 2.0


def compute_median_coord(coords: List[Tuple[float, float]]) -> Optional[Tuple[float, float]]:
    if not coords:
        return None
    lats = [c[0] for c in coords if c and c[0] is not None]
    lons = [c[1] for c in coords if c and c[1] is not None]
    if not lats or not lons:
        return None
    return (compute_median(lats), compute_median(lons))


def enrich_with_geo_and_rescore(results: List[dict], centroid: Optional[Tuple[float,float]], geo_weight: float, geo_tau: float, coords_map: Dict[str, Tuple[float,float]]) -> Dict[str, Any]:
    if not results:
        return {"results": results, "geo_stats": {}}
    if centroid is None:
        # Sem centróide => sim_geo = 0 para todos
        for r in results:
            r['geo_distance_km'] = None
            r['geo_similarity'] = 0.0
            r['final_score'] = r.get('similarity', 0.0)
        return {"results": results, "geo_stats": {"centroid": None, "ignored": len(results), "geo_weight": geo_weight, "geo_tau": geo_tau}}
    c_lat, c_lon = centroid
    dist_values: List[float] = []
    ignored = 0
    t_loop_start = perf_counter()
    for r in results:
        ibge = r.get('unidade_orgao_codigo_ibge')
        latlon = None
        if ibge is not None:
            latlon = coords_map.get(str(ibge)) or coords_map.get(str(ibge).strip())
        if not latlon:
            r['geo_distance_km'] = None
            r['geo_similarity'] = 0.0
            ignored += 1
            sim_sem = r.get('similarity', 0.0)
            r['final_score'] = (1 - geo_weight) * sim_sem + geo_weight * 0.0
            continue
        lat, lon = latlon
        try:
            dist = haversine_km(c_lat, c_lon, lat, lon)
        except Exception:
            dist = None
        if dist is None:
            r['geo_distance_km'] = None
            r['geo_similarity'] = 0.0
            ignored += 1
            sim_sem = r.get('similarity', 0.0)
            r['final_score'] = (1 - geo_weight) * sim_sem
            continue
        r['geo_distance_km'] = dist
        geo_sim = math.exp(-dist / geo_tau) if geo_tau > 0 else 0.0
        r['geo_similarity'] = geo_sim
        sim_sem = r.get('similarity', 0.0)
        final_score = (1 - geo_weight) * sim_sem + geo_weight * geo_sim
        r['final_score'] = final_score
        dist_values.append(dist)
    # Reordena pelos final_score (desc)
    t_sort_start = perf_counter()
    results.sort(key=lambda x: x.get('final_score', 0.0), reverse=True)
    loop_ms = (t_sort_start - t_loop_start) * 1000
    sort_ms = (perf_counter() - t_sort_start) * 1000
    stats = {
        "centroid": centroid,
        "geo_weight": geo_weight,
        "geo_tau": geo_tau,
        "ignored": ignored,
        "count": len(results),
        "dist_min": min(dist_values) if dist_values else None,
        "dist_max": max(dist_values) if dist_values else None,
        "dist_mean": (sum(dist_values)/len(dist_values)) if dist_values else None,
    }
    logging.info("Geo stats: centroid=%s weight=%.3f tau=%.1f count=%s ignored=%s dist_mean=%s loop_ms=%.1f sort_ms=%.1f",
                 centroid, geo_weight, geo_tau, len(results), ignored, stats.get('dist_mean'), loop_ms, sort_ms)
    return {"results": results, "geo_stats": stats}

# -------------------- UI estilo GST (adaptado) --------------------

MAX_RESULTS = 30
current_sort_mode = 1  # 1=Similaridade, 2=Data, 3=Valor
DISPLAY_ROWS = 15
last_results: List[dict] = []
last_company: Optional[dict] = None
last_stats: Optional[dict] = None
last_cnpj: Optional[str] = None
last_geo_stats: Optional[dict] = None

SORT_MODES = {
    1: {"name": "Similaridade", "emoji": "🎯"},
    2: {"name": "Data", "emoji": "📅"},
    3: {"name": "Valor", "emoji": "💰"},
}

def display_header():
    header_text = (
        "[bold cyan]🚀 CNPJ Search v1.2[/bold cyan] —\n"
        "Digite CNPJ ou use: 1=Ordenação, 2=Buscar, 3=Detalhes, 4=Exportar, q=Sair"
    )
    console.print(Panel(header_text, border_style="blue", padding=(0, 1)))


def display_menu():
    sort_info = SORT_MODES[current_sort_mode]
    console.print("\n" + "=" * 80)
    console.print("[bold cyan]MENU[/bold cyan]")
    console.print(f"1. Ordenação: [bold]{sort_info['name']}[/bold] ({sort_info.get('emoji','')})")
    console.print("2. Buscar por CNPJ")
    if last_results:
        console.print("3. Ver detalhes de um resultado")
        console.print("4. Exportar resultados (JSON)")
    else:
        console.print("[dim]3. Ver detalhes (indisponível)\n4. Exportar (indisponível)[/dim]")
    console.print("-" * 80)
    console.print("Digite um número ou um CNPJ. [dim](quit para sair)[/dim]")


def format_currency(v) -> str:
    try:
        if v is None:
            return "-"
        return f"{float(v):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "-"


def parse_date(txt: Optional[str]) -> Optional[datetime]:
    if not txt:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(txt[:19], fmt)
        except Exception:
            pass
    return None


def format_date_br(txt: Optional[str]) -> str:
    d = parse_date(txt)
    return d.strftime("%d/%m/%Y") if d else "-"


def apply_sort_mode(results: List[dict]) -> List[dict]:
    if not results:
        return results
    if current_sort_mode == 1:
        # Se geografia ativa e final_score presente, usar final_score; senão similarity
        if any('final_score' in r for r in results):
            return sorted(results, key=lambda r: (r.get('final_score') or 0.0), reverse=True)
        return sorted(results, key=lambda r: (r.get('similarity') or 0.0), reverse=True)
    if current_sort_mode == 2:
        return sorted(results, key=lambda r: (parse_date(r.get('data_encerramento_proposta')) or datetime.min), reverse=True)
    if current_sort_mode == 3:
        return sorted(results, key=lambda r: (r.get('valor_total_homologado') or 0.0), reverse=True)
    return results


def display_results(results: List[dict]):
    if not results:
        console.print("[yellow]Nenhum resultado para exibir.[/yellow]")
        return
    results = apply_sort_mode(results)
    title_extra = " (geo blend)" if any('final_score' in r for r in results) else ""
    table = Table(title=f"Resultados - Ordenação: {SORT_MODES[current_sort_mode]['name']}{title_extra}", show_header=True, header_style="bold magenta")
    table.add_column("Rank", style="dim", width=5, justify="center")
    table.add_column("Órgão", style="cyan", width=30)
    table.add_column("Local", style="cyan", width=22)
    table.add_column("Simil.", justify="right", width=10)
    if any('final_score' in r for r in results):
        table.add_column("ScoreF", justify="right", width=10)
    table.add_column("Valor (R$)", justify="right", width=14)
    table.add_column("Enc.", width=10)

    limit = min(DISPLAY_ROWS, MAX_RESULTS)
    for i, r in enumerate(results[:limit], 1):
        orgao = r.get('orgao_entidade_razao_social') or '-'
        local = f"{r.get('unidade_orgao_municipio_nome') or ''} - {r.get('unidade_orgao_uf_sigla') or ''}".strip(" -")
        sim = f"{(r.get('similarity') or 0.0):.3f}"
        val = format_currency(r.get('valor_total_homologado'))
        data = format_date_br(r.get('data_encerramento_proposta'))
        row = [str(i), orgao, local, sim]
        if 'final_score' in r:
            row.append(f"{(r.get('final_score') or 0.0):.3f}")
        row.append(val)
        row.append(data)
        table.add_row(*row)

    console.print(table)
    if last_geo_stats and last_geo_stats.get('centroid'):
        c_lat, c_lon = last_geo_stats['centroid']
        console.print(f"[blue]Geo: centroid=({c_lat:.4f},{c_lon:.4f}) weight={last_geo_stats.get('geo_weight')} tau={last_geo_stats.get('geo_tau')} dist_mean={last_geo_stats.get('dist_mean')} ignorados={last_geo_stats.get('ignored')}/{last_geo_stats.get('count')}")

    # Painel de DEBUG quando --debug ou DEBUG=1
    if os.environ.get("DEBUG", "").lower() in ("1", "true", "yes"):
        debug_lines = []
        if last_stats:
            debug_lines.append(f"result_count={last_stats.get('result_count')}")
            debug_lines.append(f"emb_dim={last_stats.get('embedding_dim')} emb_type={last_stats.get('emb_type')}")
            if last_stats.get('sem_ms') is not None:
                debug_lines.append(f"sem_ms={last_stats.get('sem_ms')}")
            if last_stats.get('coords_contr_ms') is not None:
                debug_lines.append(f"coords_contr_ms={last_stats.get('coords_contr_ms')} coords_cand_ms={last_stats.get('coords_cand_ms')} enrich_ms={last_stats.get('enrich_ms')} median_all_ms={last_stats.get('median_all_ms')}")
            if last_stats.get('median_lat') is not None and last_stats.get('median_lon') is not None:
                debug_lines.append(f"median_pos=({last_stats.get('median_lat'):.6f},{last_stats.get('median_lon'):.6f})")
        if last_geo_stats:
            debug_lines.append(f"geo_weight={last_geo_stats.get('geo_weight')} geo_tau={last_geo_stats.get('geo_tau')}")
            debug_lines.append(f"dist_min={last_geo_stats.get('dist_min')} dist_mean={last_geo_stats.get('dist_mean')} dist_max={last_geo_stats.get('dist_max')}")
            debug_lines.append(f"ignored={last_geo_stats.get('ignored')} count={last_geo_stats.get('count')}")
            if last_geo_stats.get('centroid'):
                clat, clon = last_geo_stats['centroid']
                debug_lines.append(f"centroid=({clat:.6f},{clon:.6f})")
        if debug_lines:
            console.print(Panel("\n".join(debug_lines), title="DEBUG", border_style="yellow", padding=(0,1)))
    console.print("\n[bold magenta]Detalhes dos resultados:[/bold magenta]\n")
    limit = min(DISPLAY_ROWS, len(results))
    for i in range(1, limit + 1):
        display_result_details(results[i-1], i)


def display_result_details(result: dict, pos: int):
    obj = result.get('objeto_compra') or ''
    val = format_currency(result.get('valor_total_homologado'))
    data = format_date_br(result.get('data_encerramento_proposta'))
    org = result.get('orgao_entidade_razao_social') or 'N/I'
    loc = f"{result.get('unidade_orgao_municipio_nome') or 'N/I'} - {result.get('unidade_orgao_uf_sigla') or 'N/I'}"
    pncp = result.get('numero_controle_pncp') or 'N/I'
    link = result.get('link_sistema_origem') or ''
    sim = f"{(result.get('similarity') or 0.0):.3f}"
    fs = result.get('final_score')
    geo_d = result.get('geo_distance_km')
    geo_s = result.get('geo_similarity')
    extra_geo = ''
    if fs is not None:
        extra_geo = f"\n[bold]📌 Final Score:[/bold] {fs:.3f}  [bold]🌐 Dist(km):[/bold] {geo_d if geo_d is not None else '-'}  [bold]GeoSim:[/bold] {geo_s:.3f}" if geo_s is not None else ''

    detail_text = f"""
[bold cyan]#{pos}[/bold cyan] [yellow]Similarity: {sim}[/yellow]{extra_geo}

[bold]📄 Objeto:[/bold] {obj}

[bold]💰 Valor Homologado:[/bold] {val}
[bold]📅 Encerramento:[/bold] {data}
[bold]🏢 Órgão:[/bold] {org}
[bold]🌍 Localização:[/bold] {loc}

[bold]🔗 PNCP:[/bold] {pncp}
{('https://pncp.gov.br' in link) and f"[bold]🔗 Link Origem:[/bold] {link}" or (f"[bold]🔗 Link Origem:[/bold] {link}" if link else '')}
"""
    console.print(Panel(detail_text, border_style="green", title=f"Resultado {pos}", padding=(0,1)))

# -------------------- Fluxo principal --------------------

def run_search(cnpj14: str, top_candidates: int, timeout_ms: int, sample_pct: float, sample_n: int, use_geo: bool, geo_weight: float, geo_tau: float) -> Tuple[Optional[dict], dict, List[dict], Optional[dict]]:
    session = build_session()
    logging.info("Consultando OpenCNPJ...")
    company = fetch_company(session, cnpj14, timeout=float(os.environ.get("REQUEST_TIMEOUT", "30")))
    logging.info("Conectando ao banco...")
    conn = get_db_conn()
    try:
        with conn:
            emb_list, ibges_contratos = get_contrato_embeddings_sampled(conn, cnpj14, max(1, int(sample_n)))
            logging.info("Embeddings amostrados: %s (limite=%s)", len(emb_list), sample_n)
            emb_mean = mean_vector(emb_list)
            if not emb_mean:
                stats = {
                    "cnpj": cnpj14,
                    "contratos_com_embedding": len(emb_list),
                    "mensagem": "Sem embeddings para gerar perfil",
                    "embedding_dim": 0,
                    "emb_type": "halfvec",
                }
                return company, stats, [], None
            vec_lit = to_vector_literal(emb_mean)
            t_sem_start = perf_counter()
            results = search_similar_contratacoes(conn, vec_lit, top_candidates, timeout_ms, sample_pct)
            sem_ms = (perf_counter() - t_sem_start) * 1000
            stats = {
                "cnpj": cnpj14,
                "contratos_com_embedding": len(emb_list),
                "embedding_dim": len(emb_mean),
                "emb_type": "halfvec",
                "result_count": len(results),
                "sem_ms": round(sem_ms, 1),
            }
            geo_stats = None
            if use_geo and results:
                # Carrega coords dos contratos do fornecedor (para centróide)
                t_coords_contr_start = perf_counter()
                # Converte ibges_contratos para strings para compatibilidade uniforme
                ibges_contratos_str = [str(c) for c in ibges_contratos if c is not None]
                coords_map_contratos = load_municipios_coords(conn, ibges_contratos_str)
                coords_contratos = [coords_map_contratos.get(str(c)) for c in ibges_contratos_str if coords_map_contratos.get(str(c))]
                centroid = compute_centroid(coords_contratos)
                coords_contr_ms = (perf_counter() - t_coords_contr_start) * 1000
                logging.info("Centroid calculado: %s (amostras=%s)", centroid, len(coords_contratos))
                # Mediana geográfica usando TODOS os contratos do CNPJ
                t_med_all_start = perf_counter()
                ibge_all = get_all_ibge_for_cnpj(conn, cnpj14)
                ibge_all_str = [str(x) for x in ibge_all]
                coords_map_all = load_municipios_coords(conn, ibge_all_str)
                coords_all = [coords_map_all.get(str(c)) for c in ibge_all_str if coords_map_all.get(str(c))]
                median_pos = compute_median_coord(coords_all)
                med_all_ms = (perf_counter() - t_med_all_start) * 1000
                logging.info("Mediana geográfica (todos contratos): %s (coords=%s) tempo=%.1fms", median_pos, len(coords_all), med_all_ms)
                # Carrega coords dos candidatos
                ibges_candidatos = [str(r.get('unidade_orgao_codigo_ibge')) for r in results if r.get('unidade_orgao_codigo_ibge') is not None]
                t_coords_cand_start = perf_counter()
                coords_map_candidatos = load_municipios_coords(conn, ibges_candidatos)
                coords_cand_ms = (perf_counter() - t_coords_cand_start) * 1000
                t_enrich_start = perf_counter()
                enriched = enrich_with_geo_and_rescore(results, centroid, geo_weight, geo_tau, coords_map_candidatos)
                enrich_ms = (perf_counter() - t_enrich_start) * 1000
                results = enriched['results']
                geo_stats = enriched.get('geo_stats')
                stats['geo_active'] = True
                if centroid:
                    stats['centroid_lat'] = centroid[0]
                    stats['centroid_lon'] = centroid[1]
                if median_pos:
                    stats['median_lat'] = median_pos[0]
                    stats['median_lon'] = median_pos[1]
                # Anexa tempos
                stats['coords_contr_ms'] = round(coords_contr_ms, 1)
                stats['coords_cand_ms'] = round(coords_cand_ms, 1)
                stats['enrich_ms'] = round(enrich_ms, 1)
                stats['median_all_ms'] = round(med_all_ms, 1)
            else:
                stats['geo_active'] = False
            return company, stats, results, geo_stats
    finally:
        try:
            conn.close()
        except Exception:
            pass


def interactive_loop(default_cnpj: Optional[str], top_candidates: int, timeout_ms: int, sample_pct: float, sample_n: int, use_geo: bool, geo_weight: float, geo_tau: float):
    global last_results, last_company, last_stats, last_cnpj, current_sort_mode, last_geo_stats
    console.clear()
    display_header()
    while True:
        display_menu()
        choice = Prompt.ask("Entrada").strip()
        if choice.lower() in ["q", "quit", "exit", "sair"]:
            break
        if choice == "1":
            current_sort_mode = 1 if current_sort_mode == 3 else (current_sort_mode + 1)
            console.print(f"[green]✓ Ordenação alterada para: {SORT_MODES[current_sort_mode]['name']}[/green]")
            if last_results:
                display_results(last_results)
            continue
        if choice == "2":
            cnpj_input = Prompt.ask("Informe o CNPJ (14 dígitos)", default=(default_cnpj or "")).strip()
            cnpj14 = normalize_cnpj(cnpj_input)
            if not cnpj14:
                console.print("[red]CNPJ inválido[/red]")
                continue
            console.print(f"[cyan]CNPJ:[/cyan] {cnpj14} ({format_cnpj(cnpj14)})")
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
                progress.add_task(description="Buscando...", total=None)
                last_company, last_stats, last_results, last_geo_stats = run_search(cnpj14, top_candidates, timeout_ms, sample_pct, sample_n, use_geo, geo_weight, geo_tau)
                last_cnpj = cnpj14
            console.print(f"[bold green]Resultados encontrados: {len(last_results)}[/bold green]")
            display_results(last_results)
            continue
        if choice == "3" and last_results:
            idx = Prompt.ask(f"Nº do resultado (1-{min(len(last_results), DISPLAY_ROWS)})", default="1").strip()
            try:
                i = int(idx)
                if i < 1 or i > len(last_results[:DISPLAY_ROWS]):
                    raise ValueError()
                display_result_details(last_results[i-1], i)
            except Exception:
                console.print("[red]Índice inválido[/red]")
            continue
        if choice == "4" and last_results:
            out = {
                "company": last_company,
                "stats": last_stats,
                "results": last_results,
                "geo_stats": last_geo_stats,
            }
            os.makedirs(os.path.join("scripts", "logs"), exist_ok=True)
            out_path = os.path.join("scripts", "logs", "cnpj_search_v1_2_LAST.json")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(out, f, ensure_ascii=False, default=str, indent=2)
            console.print(f"[green]JSON exportado em: {out_path}[green]")
            continue
        cnpj14 = normalize_cnpj(choice)
        if cnpj14:
            console.print(f"[cyan]CNPJ:[/cyan] {cnpj14} ({format_cnpj(cnpj14)})")
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
                progress.add_task(description="Buscando...", total=None)
                last_company, last_stats, last_results, last_geo_stats = run_search(cnpj14, top_candidates, timeout_ms, sample_pct, sample_n, use_geo, geo_weight, geo_tau)
                last_cnpj = cnpj14
            console.print(f"[bold green]Resultados encontrados: {len(last_results)}[/bold green]")
            display_results(last_results)
            continue
        console.print("[yellow]Entrada não reconhecida[/yellow]")

# -------------------- Main --------------------

def main():
    global last_company, last_stats, last_results, last_cnpj, last_geo_stats
    load_env()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="CNPJ Search v1.2 (UI estilo GST + geografia opcional)")
    parser.add_argument("--cnpj", help="CNPJ do fornecedor (14 dígitos ou formatado)")
    parser.add_argument("--top-k", type=int, default=30, help="Quantidade de resultados (exibição final). Default=30")
    parser.add_argument("--top-candidates", type=int, default=800, help="Quantidade de candidatos semânticos antes do blend (default=800)")
    parser.add_argument("--timeout-ms", type=int, default=120000, help="Timeout da consulta semântica (ms). Default=120000")
    parser.add_argument("--fallback-sample-pct", type=float, default=2.0, help="TABLESAMPLE pct no fallback. Default=2.0")
    parser.add_argument("--rows", type=int, default=15, help="Linhas exibidas na tabela (default=15)")
    parser.add_argument("--sample-contratos", type=int, default=50, help="Amostra de contratos para vetor médio (default=50)")
    parser.add_argument("--load-json", help="Caminho para JSON de saída (apenas apresentação)")
    parser.add_argument("--width", type=int, default=96, help="Largura do console (default=96)")
    parser.add_argument("--debug", action="store_true", help="Ativa logs detalhados")
    # Geografia
    parser.add_argument("--pos", action="store_true", help="Ativa blending geográfico")
    parser.add_argument("--geo-weight", type=float, default=0.25, help="Peso da similaridade geográfica no score final (default=0.25)")
    parser.add_argument("--geo-tau", type=float, default=300.0, help="Tau (km) para decaimento exponencial da distância (default=300)")
    args = parser.parse_args()

    # Ajuste de largura
    global console
    try:
        w = max(60, min(140, int(args.width)))
        console = Console(width=w)
    except Exception:
        console = Console(width=96)

    global DISPLAY_ROWS
    try:
        DISPLAY_ROWS = max(5, min(50, int(args.rows)))
    except Exception:
        DISPLAY_ROWS = 15

    if args.debug:
        os.environ["DEBUG"] = "1"
        logging.getLogger().setLevel(logging.INFO)
    if os.environ.get("DEBUG", "").lower() in ("1", "true", "yes"):
        logging.getLogger().setLevel(logging.INFO)

    # Modo apresentação
    if args.load_json:
        try:
            with open(args.load_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            last_company = data.get("company")
            last_stats = data.get("stats")
            last_results = data.get("results", [])
            last_geo_stats = data.get("geo_stats")
            console.clear()
            display_header()
            if last_stats:
                console.print(f"[blue]CNPJ:[/blue] {last_stats.get('cnpj', '')}")
            display_results(last_results)
            interactive_loop(last_stats.get('cnpj') if last_stats else None, args.top_candidates, args.timeout_ms, args.fallback_sample_pct, args.sample_contratos, args.pos, args.geo_weight, args.geo_tau)
            return
        except Exception as e:
            console.print(f"[red]Falha ao carregar JSON: {e}[/red]")

    # Execução direta se CNPJ fornecido
    if args.cnpj:
        cnpj14 = normalize_cnpj(args.cnpj)
        if not cnpj14:
            console.print("[red]CNPJ inválido[/red]")
            return
        console.print(f"[cyan]CNPJ:[/cyan] {cnpj14} ({format_cnpj(cnpj14)})")
        last_company, last_stats, last_results, last_geo_stats = run_search(cnpj14, args.top_candidates, args.timeout_ms, args.fallback_sample_pct, args.sample_contratos, args.pos, args.geo_weight, args.geo_tau)
        last_cnpj = cnpj14
        # Cortar exibição final a top-k (após re-ranking)
        last_results = last_results[:args.top_k]
        console.clear()
        display_header()
        if last_stats:
            console.print(f"[blue]CNPJ:[/blue] {last_stats.get('cnpj', '')}")
        display_results(last_results)
        interactive_loop(cnpj14, args.top_candidates, args.timeout_ms, args.fallback_sample_pct, args.sample_contratos, args.pos, args.geo_weight, args.geo_tau)
        return

    # Interativo puro
    interactive_loop(None, args.top_candidates, args.timeout_ms, args.fallback_sample_pct, args.sample_contratos, args.pos, args.geo_weight, args.geo_tau)

if __name__ == "__main__":
    main()
