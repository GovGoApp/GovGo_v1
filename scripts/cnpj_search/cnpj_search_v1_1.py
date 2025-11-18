#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cnpj_search_v1_1

Terminal interativo no estilo GST para buscar processos similares a partir de um CNPJ.

Recursos
- Entrada de CNPJ via CLI ou menu interativo (igual GST: cabeçalho, menu, tabela, detalhes)
- Ordenação por: Similaridade | Data de Encerramento | Valor
- Busca usa exclusivamente embeddings_hv (halfvec(3072)) conforme BDS1_v6
- Timeout configurável e fallback com TABLESAMPLE em caso de lentidão
- Opção de carregar um JSON já pronto (exemplo_saida.json) para apenas apresentar

Uso rápido
- Interativo: python scripts/cnpj_search/cnpj_search_v1_1.py
- Direto:     python scripts/cnpj_search/cnpj_search_v1_1.py --cnpj 11164874000109
"""
import os
import re
import json
import argparse
import logging
from typing import List, Optional, Tuple
from datetime import datetime

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
# Largura padrão reduzida; pode ser sobrescrita via --width em main()
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


# -------------------- Ambiente e conexão --------------------

API_BASE = "https://api.opencnpj.org"


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


def normalize_cnpj(cnpj: str) -> Optional[str]:
    if not cnpj:
        return None
    digits = re.sub(r"\D", "", str(cnpj))
    return digits if len(digits) == 14 else None


def format_cnpj(cnpj14: str) -> str:
    """Formata 14 dígitos para 11.111.111/1111-11."""
    if not cnpj14 or len(cnpj14) != 14 or not cnpj14.isdigit():
        return cnpj14 or ""
    return f"{cnpj14[0:2]}.{cnpj14[2:5]}.{cnpj14[5:8]}/{cnpj14[8:12]}-{cnpj14[12:14]}"


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


# -------------------- Busca (halfvec 3072) --------------------

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


def get_contrato_embeddings(conn, pncp_ids: List[str]) -> List[List[float]]:
    if not pncp_ids:
        return []
    sql = """
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
        return out


def get_contrato_embeddings_sampled(conn, cnpj14: str, sample_n: int) -> List[List[float]]:
    """Carrega uma amostra aleatória de embeddings de contratos do CNPJ informado.
    Seleciona diretamente via JOIN e ORDER BY random() LIMIT sample_n.
    """
    if not cnpj14 or sample_n <= 0:
        return []
    sql = """
        SELECT ce.embeddings_hv::text AS emb
        FROM public.contrato c
        JOIN public.contrato_emb ce USING (numero_controle_pncp)
        WHERE c.ni_fornecedor = %s
        ORDER BY random()
        LIMIT %s
    """
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        if isdbg('SQL'):
            dbg_sql('load contrato_emb sample (halfvec)', sql, [cnpj14, sample_n], names=['cnpj','limit'])
        cur.execute(sql, (cnpj14, sample_n))
        rows = cur.fetchall()
        out: List[List[float]] = []
        for r in rows:
            vec = parse_vector_text(r.get("emb"))
            if vec is not None and len(vec) > 0:
                out.append(vec)
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
    return "[" + ",".join(f"{x:.6f}" for x in vec) + "]"


def search_similar_contratacoes(conn, vec_lit: str, top_k: int, timeout_ms: int, sample_pct: float) -> List[dict]:
    emb_dim = int(os.environ.get("EMB_DIM", "3072"))
    col = "embeddings_hv"
    cast = f"::halfvec({emb_dim})"

    # Calcula a distância uma única vez (evita recomputo no SELECT e ORDER BY)
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
            # Probes opcional (se definido no ambiente)
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


# -------------------- UI estilo GST --------------------

MAX_RESULTS = 30
current_sort_mode = 1  # 1=Similaridade, 2=Data, 3=Valor
# Quantidade de linhas exibidas na tabela (ajustável via --rows)
DISPLAY_ROWS = 15
last_results: List[dict] = []
last_company: Optional[dict] = None
last_stats: Optional[dict] = None
last_cnpj: Optional[str] = None

SORT_MODES = {
    1: {"name": "Similaridade", "emoji": "🎯"},
    2: {"name": "Data", "emoji": "📅"},
    3: {"name": "Valor", "emoji": "💰"},
}


def display_header():
    # Cabeçalho ultra-compacto (mínimo de linhas)
    header_text = (
        "[bold cyan]🚀 CNPJ Search v1.1[/bold cyan] —\n"
        "Digite CNPJ ou use: 1=Ordenação, 2=Buscar, 3=Detalhes, 4=Exportar, q=Sair"
    )
    console.print(Panel(header_text, border_style="blue", padding=(0, 1)))


def display_menu():
    sort_info = SORT_MODES[current_sort_mode]
    console.print("\n" + "=" * 80)
    console.print("[bold cyan]MENU[/bold cyan]")
    console.print(f"1. Ordenação: [bold]{sort_info['name']}[/bold] ({sort_info['description'] if 'description' in sort_info else sort_info['emoji']})")
    console.print("2. Buscar por CNPJ")
    if last_results:
        console.print("3. Ver detalhes de um resultado")
        console.print("4. Exportar resultados (JSON)")
    else:
        console.print("[dim]3. Ver detalhes (indisponível)\n4. Exportar (indisponível)[/dim]")
    console.print("-" * 80)
    console.print("Digite um número para mudar configuração ou digite um CNPJ para buscar. [dim](quit para sair)[/dim]")


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
    # formatos comuns: ISO-like, YYYY-MM-DDTHH:MM:SS, YYYY-MM-DD
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
    table = Table(title=f"Resultados - Ordenação: {SORT_MODES[current_sort_mode]['name']}", show_header=True, header_style="bold magenta")
    table.add_column("Rank", style="dim", width=5, justify="center")
    table.add_column("Órgão", style="cyan", width=32)
    table.add_column("Local", style="cyan", width=22)
    table.add_column("Simil.", justify="right", width=10)
    table.add_column("Valor (R$)", justify="right", width=14)
    table.add_column("Enc.", width=10)

    # Limitar número de linhas exibidas
    limit = min(DISPLAY_ROWS, MAX_RESULTS)
    for i, r in enumerate(results[:limit], 1):
        orgao = r.get('orgao_entidade_razao_social') or '-'
        local = f"{r.get('unidade_orgao_municipio_nome') or ''} - {r.get('unidade_orgao_uf_sigla') or ''}".strip(" -")
        sim = f"{(r.get('similarity') or 0.0):.3f}"
        val = format_currency(r.get('valor_total_homologado'))
        data = format_date_br(r.get('data_encerramento_proposta'))
        table.add_row(str(i), orgao, local, sim, val, data)

    console.print(table)
    console.print("\n[bold magenta]Detalhes dos resultados:[/bold magenta]\n")
    # Exibir painéis de detalhes no estilo GST para cada linha exibida
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

    detail_text = f"""
[bold cyan]#{pos}[/bold cyan] [yellow]Similarity: {sim}[/yellow]

[bold]📄 Objeto:[/bold] {obj}

[bold]💰 Valor Homologado:[/bold] {val}
[bold]📅 Encerramento:[/bold] {data}
[bold]🏢 Órgão:[/bold] {org}
[bold]🌍 Localização:[/bold] {loc}

[bold]🔗 PNCP:[/bold] {pncp}
{('https://pncp.gov.br' in link) and f"[bold]🔗 Link Origem:[/bold] {link}" or (f"[bold]🔗 Link Origem:[/bold] {link}" if link else '')}
"""
    console.print(Panel(detail_text, border_style="green", title=f"Resultado {pos}", padding=(0,1)))


# -------------------- Fluxo de busca --------------------

def run_search(cnpj14: str, top_k: int, timeout_ms: int, sample_pct: float, sample_n: int) -> Tuple[Optional[dict], dict, List[dict]]:
    session = build_session()
    logging.info("Consultando OpenCNPJ...")
    company = fetch_company(session, cnpj14, timeout=float(os.environ.get("REQUEST_TIMEOUT", "30")))
    logging.info("Conectando ao banco...")
    conn = get_db_conn()
    try:
        with conn:
            pncp_ids = get_contrato_ids_for_cnpj(conn, cnpj14)
            logging.info("Contratos localizados: %s", len(pncp_ids))
            emb_list = get_contrato_embeddings_sampled(conn, cnpj14, max(1, int(sample_n)))
            logging.info("Embeddings amostrados: %s (limite solicitado=%s)", len(emb_list), sample_n)
            emb_mean = mean_vector(emb_list)
            if not emb_mean:
                stats = {
                    "cnpj": cnpj14,
                    "contratos_encontrados": len(pncp_ids),
                    "contratos_com_embedding": len(emb_list),
                    "mensagem": "Sem embeddings para gerar perfil",
                    "embedding_dim": 0,
                    "emb_type": "halfvec",
                }
                return company, stats, []
            logging.info("Dimensão do perfil (média): %s", len(emb_mean))
            vec_lit = to_vector_literal(emb_mean)
            results = search_similar_contratacoes(conn, vec_lit, top_k, timeout_ms, sample_pct)
            logging.info("Resultados retornados: %s", len(results))
            stats = {
                "cnpj": cnpj14,
                "contratos_encontrados": len(pncp_ids),
                "contratos_com_embedding": len(emb_list),
                "embedding_dim": len(emb_mean),
                "emb_type": "halfvec",
            }
            return company, stats, results
    finally:
        try:
            conn.close()
        except Exception:
            pass


def interactive_loop(default_cnpj: Optional[str], top_k: int, timeout_ms: int, sample_pct: float, sample_n: int):
    global last_results, last_company, last_stats, last_cnpj, current_sort_mode
    console.clear()
    display_header()
    while True:
        display_menu()
        choice = Prompt.ask("Entrada").strip()
        if choice.lower() in ["q", "quit", "exit", "sair"]:
            break
        if choice == "1":
            # Alterna ordenação 1->2->3->1
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
                last_company, last_stats, last_results = run_search(cnpj14, top_k, timeout_ms, sample_pct, sample_n)
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
            }
            os.makedirs(os.path.join("scripts", "logs"), exist_ok=True)
            out_path = os.path.join("scripts", "logs", "cnpj_search_v1_1_LAST.json")
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(out, f, ensure_ascii=False, default=str, indent=2)
            console.print(f"[green]JSON exportado em: {out_path}[/green]")
            continue

        # Se não é opção, tente como CNPJ direto (como no GST digita-se a consulta)
        cnpj14 = normalize_cnpj(choice)
        if cnpj14:
            console.print(f"[cyan]CNPJ:[/cyan] {cnpj14} ({format_cnpj(cnpj14)})")
            with Progress(SpinnerColumn(), TextColumn("[progress.description]{task.description}"), transient=True) as progress:
                progress.add_task(description="Buscando...", total=None)
                last_company, last_stats, last_results = run_search(cnpj14, top_k, timeout_ms, sample_pct, sample_n)
                last_cnpj = cnpj14
            console.print(f"[bold green]Resultados encontrados: {len(last_results)}[/bold green]")
            display_results(last_results)
            continue
        console.print("[yellow]Entrada não reconhecida[/yellow]")


# -------------------- Main --------------------

def main():
    global last_company, last_stats, last_results, last_cnpj
    load_env()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    parser = argparse.ArgumentParser(description="CNPJ Search v1.1 (UI estilo GST)")
    parser.add_argument("--cnpj", help="CNPJ do fornecedor (14 dígitos ou formatado)")
    parser.add_argument("--top-k", type=int, default=30, help="Quantidade de resultados (default=30)")
    parser.add_argument("--timeout-ms", type=int, default=120000, help="Timeout da consulta (ms). Default=120000")
    parser.add_argument("--fallback-sample-pct", type=float, default=2.0, help="TABLESAMPLE pct no fallback. Default=2.0")
    parser.add_argument("--rows", type=int, default=15, help="Linhas exibidas na tabela (default=15)")
    parser.add_argument("--sample-contratos", type=int, default=50, help="Tamanho da amostra de contratos para gerar o perfil (default=50)")
    parser.add_argument("--load-json", help="Caminho para JSON de saída (apenas apresentação)")
    parser.add_argument("--width", type=int, default=96, help="Largura do console (default=96)")
    parser.add_argument("--debug", action="store_true", help="Ativa logs detalhados (gvg_debug + info)")
    args = parser.parse_args()

    # Ajuste de largura do console
    global console
    try:
        w = max(60, min(140, int(args.width)))
        console = Console(width=w)
    except Exception:
        console = Console(width=96)

    # Ajuste do número de linhas exibidas
    global DISPLAY_ROWS
    try:
        DISPLAY_ROWS = max(5, min(50, int(args.rows)))
    except Exception:
        DISPLAY_ROWS = 15

    if args.debug:
        os.environ["DEBUG"] = "1"
        logging.getLogger().setLevel(logging.INFO)
    # Alternativa: honrar DEBUG=1 no ambiente mesmo sem --debug
    if os.environ.get("DEBUG", "").lower() in ("1", "true", "yes"): 
        logging.getLogger().setLevel(logging.INFO)

    # Modo apresentação a partir de um JSON pronto (como exemplo_saida.json)
    if args.load_json:
        try:
            with open(args.load_json, "r", encoding="utf-8") as f:
                data = json.load(f)
            last_company = data.get("company")
            last_stats = data.get("stats")
            last_results = data.get("results", [])
            console.clear()
            display_header()
            if last_stats:
                console.print(f"[blue]CNPJ:[/blue] {last_stats.get('cnpj', '')}")
            display_results(last_results)
            # Entra no menu apenas para navegação de detalhes/export
            interactive_loop(last_stats.get('cnpj') if last_stats else None, args.top_k, args.timeout_ms, args.fallback_sample_pct, args.sample_contratos)
            return
        except Exception as e:
            console.print(f"[red]Falha ao carregar JSON: {e}[/red]")

    # Modo direto (se veio CNPJ em CLI) ou interativo
    if args.cnpj:
        cnpj14 = normalize_cnpj(args.cnpj)
        if not cnpj14:
            console.print("[red]CNPJ inválido[/red]")
            return
        console.print(f"[cyan]CNPJ:[/cyan] {cnpj14} ({format_cnpj(cnpj14)})")
        last_company, last_stats, last_results = run_search(cnpj14, args.top_k, args.timeout_ms, args.fallback_sample_pct, args.sample_contratos)
        last_cnpj = cnpj14
        console.clear()
        display_header()
        if last_stats:
            console.print(f"[blue]CNPJ:[/blue] {last_stats.get('cnpj', '')}")
        display_results(last_results)
        interactive_loop(cnpj14, args.top_k, args.timeout_ms, args.fallback_sample_pct, args.sample_contratos)
        return

    # Interativo puro
    interactive_loop(None, args.top_k, args.timeout_ms, args.fallback_sample_pct, args.sample_contratos)


if __name__ == "__main__":
    main()