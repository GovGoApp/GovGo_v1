#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
01_processing (PCA)

Objetivo
- Baixar PCA e seus itens (preferir /v1/pca; fallback /v1/pca/usuario por ano/idUsuario)
- Inserir/atualizar em public.pca (cabeçalho) e public.item_pca (itens)
- Persistir estado (LPD) em system_config (pca_last_processed_date) e cursores auxiliares
- Registrar métricas em pipeline_run_stats (stage="pca.01")

Observações
- Datas como TEXT no BD
- Paginação até 500
- Retries/backoff, timeouts, logs simples

Esqueleto: preencha mapeamentos e SQLs conforme o schema atual.
"""
import os
import sys
import json
import time
import logging
import argparse
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from rich.progress import Progress, BarColumn, TimeElapsedColumn, TimeRemainingColumn, SpinnerColumn, TextColumn
from pathlib import Path

# Trace opcional de progresso (ativado por --trace)
TRACE = False

STAGE_NAME = "pca.01"
DEFAULT_PAGE_SIZE = 100  # reduzido para evitar timeouts; pode ser ajustado com --page
JSON_RETRY_MAX = 3
BASE_URL = os.environ.get("PNCP_CONSULTA_BASE_URL", "https://pncp.gov.br/api/consulta")

CFG_LAST_PROCESSED = "last_processed_date_pca"
CFG_PCA_USER_IDS = "pca_user_ids"  # JSON array opcional p/ fallback /pca/usuario

# Arquivo de log para páginas puladas (para retry posterior)
def _get_skipped_log_path() -> str:
    # scripts/pncp/pca/01_processing.py → subir 2 níveis até scripts/, depois logs/
    base_dir = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".."))
    log_dir = os.path.join(base_dir, "logs")
    os.makedirs(log_dir, exist_ok=True)
    return os.path.join(log_dir, "pca_skipped_pages.csv")


def log_skipped_page(url: str, date_from: str, date_to: str, page: int, page_size: int, status: Optional[int], attempts: int):
    """Registra em CSV a página que não foi lida após retries.

    Colunas: timestamp_utc, url, date_from, date_to, page, page_size, status_code, attempts
    """
    path = _get_skipped_log_path()
    is_new = not os.path.exists(path)
    try:
        with open(path, "a", encoding="utf-8") as f:
            if is_new:
                f.write("timestamp_utc,url,date_from,date_to,page,page_size,status_code,attempts\n")
            ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            line = f'{ts},{url},{date_from},{date_to},{page},{page_size},{status if status is not None else ""},{attempts}\n'
            f.write(line)
        if TRACE:
            logging.info("PCA TRACE: página pulada registrada (p=%s, janela=%s→%s)", page, date_from, date_to)
    except Exception:
        logging.exception("PCA: falha ao registrar página pulada no CSV")


def build_session() -> requests.Session:
    s = requests.Session()
    retry = Retry(
        total=5,
        backoff_factor=1.5,
        status_forcelist=[408, 429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry)
    s.mount("http://", adapter)
    s.mount("https://", adapter)
    s.headers.update({"accept": "*/*", "user-agent": "GovGo-Pipeline/1.0"})
    return s


def get_db_conn():
    """Conecta usando apenas SUPABASE_* do scripts/pncp/.env"""
    return psycopg2.connect(
        host=os.environ.get("SUPABASE_HOST"),
        port=int(os.environ.get("SUPABASE_PORT", "6543")),
        dbname=os.environ.get("SUPABASE_DBNAME"),
        user=os.environ.get("SUPABASE_USER"),
        password=os.environ.get("SUPABASE_PASSWORD"),
    )


def get_system_config(cur, key: str) -> Optional[str]:
    cur.execute("SELECT value FROM system_config WHERE key=%s", (key,))
    row = cur.fetchone()
    return row[0] if row else None


def set_system_config(cur, key: str, value: str):
    cur.execute(
        """
        INSERT INTO system_config (key, value, description)
        VALUES (%s, %s, %s)
        ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, updated_at=NOW()
        """,
        (key, value, f"Atualizado por {STAGE_NAME}"),
    )


def insert_pipeline_run_stats(cur, stage: str, date_ref: str, inserted_contratacoes: int, inserted_itens: int = 0):
    cur.execute(
        """
        INSERT INTO pipeline_run_stats(stage, date_ref, inserted_contratacoes, inserted_itens)
        VALUES (%s, %s, %s, %s)
        """,
        (stage, date_ref, inserted_contratacoes, inserted_itens),
    )


def normalize_pca_header(api_obj: Dict[str, Any]) -> Dict[str, Any]:
    """Mapeia o cabeçalho PCA conforme payload real do /v1/pca e /v1/pca/atualizacao.
    Campos observados: idPcaPncp, anoPca, orgaoEntidadeCnpj, orgaoEntidadeRazaoSocial,
    codigoUnidade, nomeUnidade, dataPublicacaoPNCP, dataAtualizacaoGlobalPCA.
    """
    return {
        "numero_controle_pca_pncp": api_obj.get("idPcaPncp"),
        "orgao_entidade_cnpj": api_obj.get("orgaoEntidadeCnpj"),
        "orgao_entidade_razao_social": api_obj.get("orgaoEntidadeRazaoSocial"),
        "codigo_unidade": api_obj.get("codigoUnidade"),
        "nome_unidade": api_obj.get("nomeUnidade"),
        "ano_pca": api_obj.get("anoPca"),
        # pode não existir em todos os endpoints
        "id_usuario": api_obj.get("idUsuario"),
        # Datas observadas no JSON: dataPublicacaoPNCP, dataAtualizacaoGlobalPCA
        "data_publicacao_pncp": api_obj.get("dataPublicacaoPNCP") or api_obj.get("dataPublicacaoPncp"),
        "data_inclusao": api_obj.get("dataInclusao"),
        "data_atualizacao": api_obj.get("dataAtualizacaoGlobalPCA") or api_obj.get("dataAtualizacao"),
    }


def normalize_pca_item(numero_controle_pca_pncp: str, item: Dict[str, Any]) -> Dict[str, Any]:
    """Mapeia o item do PCA. A descrição do "objeto" do PCA está em descricaoItem."""
    return {
        "numero_controle_pca_pncp": numero_controle_pca_pncp,
        "numero_item": item.get("numeroItem"),
        "categoria_item_pca_nome": item.get("categoriaItemPcaNome"),
        "classificacao_catalogo_id": item.get("classificacaoCatalogoId"),
        "nome_classificacao_catalogo": item.get("nomeClassificacaoCatalogo"),
        "classificacao_superior_codigo": item.get("classificacaoSuperiorCodigo"),
        "classificacao_superior_nome": item.get("classificacaoSuperiorNome"),
        "pdm_codigo": item.get("pdmCodigo"),
        "pdm_descricao": item.get("pdmDescricao"),
        "codigo_item": item.get("codigoItem"),
        "descricao_item": item.get("descricaoItem"),
        "unidade_fornecimento": item.get("unidadeFornecimento"),
        "quantidade_estimada": item.get("quantidadeEstimada"),
        "valor_unitario": item.get("valorUnitario"),
        "valor_total": item.get("valorTotal"),
        "valor_orcamento_exercicio": item.get("valorOrcamentoExercicio"),
        "data_desejada": item.get("dataDesejada"),
        "unidade_requisitante": item.get("unidadeRequisitante"),
        "grupo_contratacao_codigo": item.get("grupoContratacaoCodigo"),
        "grupo_contratacao_nome": item.get("grupoContratacaoNome"),
        "data_inclusao": item.get("dataInclusao"),
        "data_atualizacao": item.get("dataAtualizacao"),
    }


def upsert_pca(cur, rows: List[Dict[str, Any]]) -> Tuple[int, int]:
    if not rows:
        return 0, 0
    psycopg2.extras.execute_values(
        cur,
        """
        INSERT INTO public.pca (
            numero_controle_pca_pncp,
            orgao_entidade_cnpj,
            orgao_entidade_razao_social,
            codigo_unidade,
            nome_unidade,
            ano_pca,
            id_usuario,
            data_publicacao_pncp,
            data_inclusao,
            data_atualizacao
        ) VALUES %s
        ON CONFLICT (numero_controle_pca_pncp) DO UPDATE SET
            orgao_entidade_cnpj = EXCLUDED.orgao_entidade_cnpj,
            orgao_entidade_razao_social = EXCLUDED.orgao_entidade_razao_social,
            codigo_unidade = EXCLUDED.codigo_unidade,
            nome_unidade = EXCLUDED.nome_unidade,
            ano_pca = EXCLUDED.ano_pca,
            id_usuario = EXCLUDED.id_usuario,
            data_publicacao_pncp = EXCLUDED.data_publicacao_pncp,
            data_inclusao = EXCLUDED.data_inclusao,
            data_atualizacao = EXCLUDED.data_atualizacao
        """,
        [
            (
                r.get("numero_controle_pca_pncp"),
                r.get("orgao_entidade_cnpj"),
                r.get("orgao_entidade_razao_social"),
                r.get("codigo_unidade"),
                r.get("nome_unidade"),
                r.get("ano_pca"),
                r.get("id_usuario"),
                r.get("data_publicacao_pncp"),
                r.get("data_inclusao"),
                r.get("data_atualizacao"),
            )
            for r in rows
        ],
        page_size=1000,
    )
    return len(rows), 0


def upsert_item_pca(cur, rows: List[Dict[str, Any]]) -> Tuple[int, int]:
    if not rows:
        return 0, 0
    # Preparar valores na mesma ordem para UPDATE e INSERT
    cols = [
        "numero_controle_pca_pncp",
        "numero_item",
        "categoria_item_pca_nome",
        "classificacao_catalogo_id",
        "nome_classificacao_catalogo",
        "classificacao_superior_codigo",
        "classificacao_superior_nome",
        "pdm_codigo",
        "pdm_descricao",
        "codigo_item",
        "descricao_item",
        "unidade_fornecimento",
        "quantidade_estimada",
        "valor_unitario",
        "valor_total",
        "valor_orcamento_exercicio",
        "data_desejada",
        "unidade_requisitante",
        "grupo_contratacao_codigo",
        "grupo_contratacao_nome",
        "data_inclusao",
        "data_atualizacao",
    ]
    values = [
        tuple(r.get(c) for c in cols)
        for r in rows
    ]

    # 1) UPDATE existente (match por numero_controle_pca_pncp, numero_item)
    update_sql = f"""
    WITH vals ({', '.join(cols)}) AS (VALUES %s)
    UPDATE public.item_pca ip
    SET
        categoria_item_pca_nome = v.categoria_item_pca_nome,
        classificacao_catalogo_id = v.classificacao_catalogo_id,
        nome_classificacao_catalogo = v.nome_classificacao_catalogo,
        classificacao_superior_codigo = v.classificacao_superior_codigo,
        classificacao_superior_nome = v.classificacao_superior_nome,
        pdm_codigo = v.pdm_codigo,
        pdm_descricao = v.pdm_descricao,
        codigo_item = v.codigo_item,
        descricao_item = v.descricao_item,
        unidade_fornecimento = v.unidade_fornecimento,
        quantidade_estimada = v.quantidade_estimada,
        valor_unitario = v.valor_unitario,
        valor_total = v.valor_total,
        valor_orcamento_exercicio = v.valor_orcamento_exercicio,
        data_desejada = v.data_desejada,
        unidade_requisitante = v.unidade_requisitante,
        grupo_contratacao_codigo = v.grupo_contratacao_codigo,
        grupo_contratacao_nome = v.grupo_contratacao_nome,
        data_inclusao = v.data_inclusao,
        data_atualizacao = v.data_atualizacao
        FROM vals v
        WHERE ip.numero_controle_pca_pncp = v.numero_controle_pca_pncp::text
            AND ip.numero_item = v.numero_item::text
    """
    psycopg2.extras.execute_values(cur, update_sql, values, page_size=1000)
    updated = cur.rowcount or 0

    # 2) INSERT dos que não existem
    insert_sql = f"""
    WITH vals ({', '.join(cols)}) AS (VALUES %s)
    INSERT INTO public.item_pca (
        numero_controle_pca_pncp,
        numero_item,
        categoria_item_pca_nome,
        classificacao_catalogo_id,
        nome_classificacao_catalogo,
        classificacao_superior_codigo,
        classificacao_superior_nome,
        pdm_codigo,
        pdm_descricao,
        codigo_item,
        descricao_item,
        unidade_fornecimento,
        quantidade_estimada,
        valor_unitario,
        valor_total,
        valor_orcamento_exercicio,
        data_desejada,
        unidade_requisitante,
        grupo_contratacao_codigo,
        grupo_contratacao_nome,
        data_inclusao,
        data_atualizacao
    )
    SELECT
        v.numero_controle_pca_pncp::text,
        v.numero_item::text,
        v.categoria_item_pca_nome,
        v.classificacao_catalogo_id,
        v.nome_classificacao_catalogo,
        v.classificacao_superior_codigo,
        v.classificacao_superior_nome,
        v.pdm_codigo,
        v.pdm_descricao,
        v.codigo_item,
        v.descricao_item,
        v.unidade_fornecimento,
        v.quantidade_estimada,
        v.valor_unitario,
        v.valor_total,
        v.valor_orcamento_exercicio,
        v.data_desejada,
        v.unidade_requisitante,
        v.grupo_contratacao_codigo,
        v.grupo_contratacao_nome,
        v.data_inclusao,
        v.data_atualizacao
    FROM vals v
        WHERE NOT EXISTS (
        SELECT 1
        FROM public.item_pca ip
                WHERE ip.numero_controle_pca_pncp = v.numero_controle_pca_pncp::text
                    AND ip.numero_item = v.numero_item::text
    )
    """
    psycopg2.extras.execute_values(cur, insert_sql, values, page_size=1000)
    inserted = cur.rowcount or 0
    return inserted, updated


def fetch_pca_page(session: requests.Session, url: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    resp = session.get(url, params=params, timeout=60)
    if resp.status_code == 204:
        return []
    resp.raise_for_status()
    try:
        data = resp.json()
    except Exception:
        logging.warning("PCA: resposta sem JSON valido (status=%s)", resp.status_code)
        return []
    if isinstance(data, list):
        return data
    return data.get("data") or []


def fetch_pca_window(session: requests.Session, url: str, params: Dict[str, Any], page_size: int = DEFAULT_PAGE_SIZE) -> List[Dict[str, Any]]:
    """Agrega todas as páginas de PCA usando os metadados totalPaginas.

    Lida com dois formatos:
    - lista simples
    - objeto { data: [...], totalPaginas, totalRegistros, numeroPagina, paginasRestantes, empty }
    """
    params0 = params.copy()
    params0["pagina"] = 1
    params0["tamanhoPagina"] = page_size
    r0 = session.get(url, params=params0, timeout=60)
    if r0.status_code == 204:
        return []
    r0.raise_for_status()
    # Página 1: se status=200 e JSON for inválido, tratar como vazio sem retries (não é erro)
    try:
        j0 = r0.json() or {}
    except Exception:
        if r0.status_code == 200:
            if TRACE:
                logging.info("PCA TRACE: pagina 1 com status 200 e JSON invalido; tratando como vazio")
            return []
        # Para outros status (não 200), aplicar retries básicos
        j0 = None
        attempt = 0
        while attempt < JSON_RETRY_MAX:
            attempt += 1
            logging.warning("PCA: resposta sem JSON valido na pagina 1 (status=%s), tentativa %s/%s", r0.status_code, attempt, JSON_RETRY_MAX)
            time.sleep(1 * attempt)
            r0 = session.get(url, params=params0, timeout=60)
            if r0.status_code == 204:
                return []
            r0.raise_for_status()
            try:
                j0 = r0.json() or {}
                break
            except Exception:
                continue
        if j0 is None:
            logging.error("PCA: pagina 1 sem JSON apos %s tentativas; tratando como vazio", JSON_RETRY_MAX)
            return []

    if isinstance(j0, list):
        return list(j0)

    data = list(j0.get("data") or [])
    total_pag = int(j0.get("totalPaginas", 1) or 1)
    total_reg = j0.get("totalRegistros")
    num_pag = j0.get("numeroPagina")
    rest = j0.get("paginasRestantes")
    empty = j0.get("empty")
    # sem log por página para não poluir a barra de progresso

    # Prefixo com dia/intervalo na barra
    def _fmt(d: Optional[str]) -> Optional[str]:
        if not d or len(d) != 8:
            return None
        return f"{d[6:8]}/{d[4:6]}/{d[0:4]}"
    raw1 = params.get("dataInicio")
    raw2 = params.get("dataFim")
    d1 = _fmt(raw1)
    d2 = _fmt(raw2)
    def _is_consecutive(r1: Optional[str], r2: Optional[str]) -> bool:
        try:
            if not r1 or not r2 or len(r1) != 8 or len(r2) != 8:
                return False
            d_1 = datetime.strptime(r1, "%Y%m%d").date()
            d_2 = datetime.strptime(r2, "%Y%m%d").date()
            return d_1 + timedelta(days=1) == d_2
        except Exception:
            return False
    if d1 and d2:
        if (raw1 == raw2) or _is_consecutive(raw1, raw2):
            label_prefix = f"Dia {d1}: PCA"
        else:
            label_prefix = f"Intervalo {d1} → {d2}: PCA"
    else:
        label_prefix = "PCA"

    with Progress(
        SpinnerColumn(style="yellow"),
        TextColumn(f"[bold]{label_prefix}[/]"),
        BarColumn(bar_width=None),
        TextColumn("{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        transient=False,
    ) as progress:
        task = progress.add_task("", total=total_pag)
        # posiciona no numeroPagina reportado (ou 1)
        try:
            np1 = int(j0.get("numeroPagina", 1))
        except Exception:
            np1 = 1
        progress.update(task, completed=max(1, min(np1, total_pag)))
        if TRACE:
            logging.info(
                "PCA TRACE: totalPaginas=%s, numeroPaginaInicial=%s -> barra=%s/%s (%.0f%%)",
                total_pag, np1, max(1, min(np1, total_pag)), total_pag,
                100.0 * max(1, min(np1, total_pag)) / max(total_pag, 1)
            )

        for p in range(2, total_pag + 1):
            params_p = params.copy()
            params_p["pagina"] = p
            params_p["tamanhoPagina"] = page_size
            rp = session.get(url, params=params_p, timeout=60)
            if rp.status_code == 204:
                break
            rp.raise_for_status()

            # Tentar parsear JSON com retries; se falhar todas as tentativas, ignorar a página e continuar
            jp = None
            attempt = 0
            while attempt < JSON_RETRY_MAX:
                try:
                    jp = rp.json() or {}
                    break
                except Exception:
                    attempt += 1
                    logging.warning("PCA: resposta sem JSON valido na pagina %s (status=%s), tentativa %s/%s", p, rp.status_code, attempt, JSON_RETRY_MAX)
                    if attempt < JSON_RETRY_MAX:
                        time.sleep(1 * attempt)
                        rp = session.get(url, params=params_p, timeout=60)
                        if rp.status_code == 204:
                            jp = {}
                            break
                        rp.raise_for_status()
            if jp is None:
                logging.error("PCA: falha ao obter JSON da pagina %s apos %s tentativas; pulando pagina", p, JSON_RETRY_MAX)
                # Logar página pulada para retry posterior
                try:
                    log_skipped_page(url, params.get("dataInicio", ""), params.get("dataFim", ""), p, page_size, rp.status_code, JSON_RETRY_MAX)
                except Exception:
                    pass
                # Avança a barra para refletir tentativa de leitura
                progress.update(task, completed=max(p, 1))
                continue

            page_list = jp if isinstance(jp, list) else (jp.get("data") or [])
            # sem log por página; apenas progresso visual
            data.extend(list(page_list))
            # Atualiza o percentual com base em numeroPagina/totalPaginas
            try:
                cur_np = int(jp.get("numeroPagina", p)) if isinstance(jp, dict) else p
            except Exception:
                cur_np = p
            progress.update(task, completed=max(cur_np, 1))
            if TRACE:
                logging.info(
                    "PCA TRACE: pagina=%s, numeroPagina=%s/%s (%.0f%%)",
                    p, max(cur_np, 1), total_pag,
                    100.0 * max(cur_np, 1) / max(total_pag, 1)
                )

    return data


def process_window(date_from: str, date_to: str, prefer_pca_endpoint: bool = True, ano_pca: Optional[int] = None, page_size: int = DEFAULT_PAGE_SIZE) -> bool:
    """
    Diário: /v1/pca/atualizacao por dataAtualizacao
    Backfill 2025: preferir /v1/pca; se não retornar itens completos, fallback /v1/pca/usuario por (anoPca,idUsuario)
    """
    # Carrega exclusivamente o .env de scripts/pncp/.env
    env_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".env"))
    load_dotenv(env_path)
    # Logging sem timestamp (mesmo padrão do contrato)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    started_at = datetime.now(timezone.utc)
    # Sem logs de abertura de janela (reduz ruído); habilite TRACE para detalhar
    if TRACE:
        logging.info("PCA TRACE: janela=%s→%s", date_from, date_to)

    session = build_session()

    url_upd = f"{BASE_URL}/v1/pca/atualizacao"
    # Importante: este endpoint aceita datas AAAAMMDD (sem hífen)
    params = {
        "dataInicio": date_from,
        "dataFim": date_to,
        "pagina": 1,
        "tamanhoPagina": page_size,
    }

    total_pages = 0
    total_downloaded = 0
    inserted_headers = 0
    inserted_items = 0
    items_updated = 0  # updates somente de itens
    updated = 0
    errors = 0

    ok = False
    with get_db_conn() as conn:
        conn.autocommit = False
        with conn.cursor() as cur:
            try:
                # Agregar todas as páginas primeiro
                headers_all = fetch_pca_window(session, url_upd, params, page_size=page_size)
                total_downloaded = len(headers_all)

                # Upsert cabeçalhos em lote
                head_rows = [normalize_pca_header(h) for h in headers_all]
                # Deduplicar por numero_controle_pca_pncp para evitar conflitos
                dedup_map: Dict[str, Dict[str, Any]] = {}
                for r in head_rows:
                    k = r.get("numero_controle_pca_pncp")
                    if not k:
                        continue
                    if k not in dedup_map:
                        dedup_map[k] = r
                head_rows_dedup = list(dedup_map.values())
                if TRACE:
                    dup_download = len(head_rows) - len(head_rows_dedup)
                    logging.info(
                        "PCA TRACE: headers baixados=%s, únicos=%s, duplicados_download=%s",
                        len(head_rows), len(head_rows_dedup), dup_download
                    )

                # Checar existência prévia no BD para estatística de duplicidade no banco
                existing_in_db: set[str] = set()
                db_dt_map: Dict[str, Optional[str]] = {}
                new_dt_map: Dict[str, Optional[str]] = {r.get("numero_controle_pca_pncp"): r.get("data_atualizacao") for r in head_rows_dedup if r.get("numero_controle_pca_pncp")}
                if head_rows_dedup:
                    keys = [r.get("numero_controle_pca_pncp") for r in head_rows_dedup if r.get("numero_controle_pca_pncp")]
                    if keys:
                        cur.execute(
                            """
                            SELECT numero_controle_pca_pncp, data_atualizacao
                              FROM public.pca
                             WHERE numero_controle_pca_pncp = ANY(%s)
                            """,
                            (keys,),
                        )
                        rows_db = cur.fetchall() or []
                        existing_in_db = {row[0] for row in rows_db}
                        db_dt_map = {row[0]: row[1] for row in rows_db}
                if TRACE:
                    novos = len(head_rows_dedup) - len(existing_in_db)
                    # Quantos existentes têm data_atualizacao diferente (candidatos reais a update)
                    candidatos_update = 0
                    for k in existing_in_db:
                        if new_dt_map.get(k) != db_dt_map.get(k):
                            candidatos_update += 1
                    logging.info(
                        "PCA TRACE: headers existentes_no_bd=%s, novos=%s, candidatos_update=%s",
                        len(existing_in_db), novos, candidatos_update
                    )
                if head_rows_dedup:
                    # silêncio: sem logs de deduplicação
                    ins_h, upd_h = upsert_pca(cur, head_rows_dedup)
                    inserted_headers += ins_h
                    updated += upd_h
                    if TRACE:
                        logging.info("PCA TRACE: upsert headers enviados=%s", len(head_rows_dedup))
                    # silêncio: sem logs detalhados de upsert

                # Para cada header, obter itens (se o endpoint não trouxer embutido) SEM barra adicional
                processed = 0
                total_items_normalized = 0
                for h in headers_all:
                    id_pca = h.get("idPcaPncp")
                    items = h.get("itens") or []
                    if not items:
                        # fallback por usuario/ano se necessário
                        try:
                            id_usuario = h.get("idUsuario")
                            if not id_usuario:
                                logging.warning("PCA: sem idUsuario no header; sem fallback /pca/usuario para %s", id_pca)
                                items = []
                            else:
                                ano = h.get("anoPca") or ano_pca or datetime.now(timezone.utc).year
                                items = fetch_pca_items_by_usuario(session, ano, id_usuario, id_pca, page_size=page_size)
                        except Exception:
                            logging.warning("PCA: falha no fallback /pca/usuario para %s", id_pca)
                            items = []
                    item_rows = [normalize_pca_item(id_pca, it) for it in items]
                    if item_rows:
                        # Deduplicar itens por (numero_controle_pca_pncp, numero_item)
                        dmap: Dict[Tuple[str, Any], Dict[str, Any]] = {}
                        for r in item_rows:
                            k = (r.get("numero_controle_pca_pncp"), r.get("numero_item"))
                            if not k[0] or k[1] is None:
                                continue
                            if k not in dmap:
                                dmap[k] = r
                        item_rows = list(dmap.values())
                        total_items_normalized += len(item_rows)
                        ins_i, upd_i = upsert_item_pca(cur, item_rows)
                        inserted_items += ins_i
                        items_updated += upd_i
                        updated += upd_i
                        # silêncio: sem logs detalhados de upsert itens
                    processed += 1

                if TRACE:
                    logging.info(
                        "PCA TRACE: itens normalizados=%s, inserted=%s, updated=%s",
                        total_items_normalized, inserted_items, items_updated
                    )

                # Atualiza LED: registrar o último dia COMPLETO processado.
                # Se a janela for [D, D+1], persistir D; caso contrário, persistir date_to.
                led_value = date_to
                try:
                    if (
                        isinstance(date_from, str)
                        and isinstance(date_to, str)
                        and len(date_from) == 8
                        and len(date_to) == 8
                    ):
                        d0 = datetime.strptime(date_from, "%Y%m%d").date()
                        d1 = datetime.strptime(date_to, "%Y%m%d").date()
                        if d0 + timedelta(days=1) == d1:
                            led_value = date_from
                except Exception:
                    pass
                set_system_config(cur, CFG_LAST_PROCESSED, led_value)
                if TRACE:
                    logging.info("PCA TRACE: LED gravado=%s", led_value)
                conn.commit()

                # Confirma LED gravado no BD e interrompe caso não confirme
                try:
                    cur.execute("SELECT value FROM system_config WHERE key=%s", (CFG_LAST_PROCESSED,))
                    row = cur.fetchone()
                    db_led = row[0] if row else None
                except Exception:
                    db_led = None
                if db_led != led_value:
                    logging.error("PCA: LED não confirmado no BD (esperado=%s, lido=%s)", led_value, db_led)
                    ok = False
                else:
                    if TRACE:
                        logging.info("PCA TRACE: LED confirmado no BD=%s", db_led)
                    ok = True
            except Exception:
                conn.rollback()
                logging.exception("Erro no processamento PCA")
                errors += 1
                ok = False
            finally:
                try:
                    insert_pipeline_run_stats(cur, STAGE_NAME, date_to, inserted_headers, inserted_items)
                    conn.commit()
                except Exception:
                    conn.rollback()
                    logging.exception("Falha ao gravar pipeline_run_stats (pca)")
    return ok


def fetch_pca_items_by_usuario(session: requests.Session, ano_pca: int, id_usuario: int, id_pca_pncp: Optional[str] = None, page_size: int = DEFAULT_PAGE_SIZE) -> List[Dict[str, Any]]:
    """Busca itens via /v1/pca/usuario filtrando por ano/idUsuario; opcionalmente filtra pelo id_pca_pncp."""
    url = f"{BASE_URL}/v1/pca/usuario"
    pagina = 1
    itens: List[Dict[str, Any]] = []
    while True:
        params = {"anoPca": ano_pca, "idUsuario": id_usuario, "pagina": pagina, "tamanhoPagina": page_size}
        resp = session.get(url, params=params, timeout=60)
        resp.raise_for_status()
        data = resp.json()
        lst = data if isinstance(data, list) else (data.get("data") or [])
        if not lst:
            break
        for header in lst:
            if id_pca_pncp and header.get("idPcaPncp") != id_pca_pncp:
                continue
            itens.extend(header.get("itens") or [])
        pagina += 1
    return itens


def main():
    parser = argparse.ArgumentParser(description="Pipeline 01 - PCA (processing)")
    parser.add_argument("--tipo", choices=["periodo", "diario"], default="periodo", help="Modo de execução: periodo (uma chamada) ou diario (dia-a-dia)")
    parser.add_argument("--from", dest="date_from", required=False, help="AAAAMMDD", default=None)
    parser.add_argument("--to", dest="date_to", required=False, help="AAAAMMDD", default=None)
    parser.add_argument("--ano", dest="ano_pca", required=False, type=int, help="Ano PCA (fallback /pca/usuario)")
    parser.add_argument("--trace", action="store_true", help="Exibe logs detalhados (progresso por página, intervalo e LED)")
    parser.add_argument("--page", dest="page_size", required=False, type=int, default=DEFAULT_PAGE_SIZE, help="Tamanho de página para API (default 100)")
    args = parser.parse_args()

    # Ativa TRACE global e configura logging cedo caso solicitado
    global TRACE
    TRACE = bool(args.trace)
    if TRACE:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    # Defaults baseados em LED: sem --from usa last_processed_date_pca; sem --to usa hoje.
    env_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".env"))
    load_dotenv(env_path)

    d_to = datetime.now(timezone.utc)
    today = d_to.strftime("%Y%m%d")
    led = None
    try:
        with get_db_conn() as conn:
            with conn.cursor() as cur:
                led = get_system_config(cur, CFG_LAST_PROCESSED)
                if TRACE:
                    logging.info("PCA TRACE: LED lido=%s (chave=%s)", led, CFG_LAST_PROCESSED)
    except Exception:
        led = None

    # Normaliza datas (aceita AAAAMMDD ou AAAA-MM-DD; remove não dígitos)
    def _norm(d: Optional[str]) -> Optional[str]:
        if d is None:
            return None
        d = str(d).strip()
        # remover separadores
        d_digits = "".join(ch for ch in d if ch.isdigit())
        if len(d_digits) == 8:
            return d_digits
        return None

    # Regras de intervalo:
    # --from A --to B => A..B
    # --from A (sem --to) => A..today
    # --to B (sem --from) => LED..B
    # nenhum => LED..today
    from_sup = args.date_from is not None
    to_sup = args.date_to is not None

    raw_from = None
    raw_to = None
    if from_sup and to_sup:
        raw_from = args.date_from
        raw_to = args.date_to
    elif from_sup and not to_sup:
        raw_from = args.date_from
        raw_to = today
    elif to_sup and not from_sup:
        raw_from = led or today
        raw_to = args.date_to
    else:
        raw_from = led or today
        raw_to = today

    date_from = _norm(raw_from) or today
    date_to = _norm(raw_to) or today

    # Validação básica de intervalo
    try:
        dt_from = datetime.strptime(date_from, "%Y%m%d")
        dt_to = datetime.strptime(date_to, "%Y%m%d")
    except Exception:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
        logging.error("PCA: formato de data inválido. Use AAAAMMDD.")
        return
    if dt_from > dt_to:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
        logging.error("PCA: data inicial é maior que a data final.")
        return

    if not from_sup and not to_sup and (led == today):
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
        logging.info("PCA: LED (%s) já está no dia atual (%s). Nada a fazer.", led, today)
        return

    # Log do intervalo resolvido
    if TRACE:
        src_from = (
            "arg"
            if from_sup
            else ("LED" if (not from_sup and to_sup) or (not from_sup and not to_sup and led) else "today")
        )
        src_to = (
            "arg" if to_sup else "today"
        )
        logging.info("PCA TRACE: intervalo resolvido %s→%s (origem: from=%s, to=%s)", date_from, date_to, src_from, src_to)

    # valida page_size mínima/máxima razoável
    page_size = max(20, min(int(args.page_size or DEFAULT_PAGE_SIZE), 500))
    if TRACE:
        logging.info("PCA TRACE: page_size=%s", page_size)

    if args.tipo == "periodo":
        _ok = process_window(date_from, date_to, prefer_pca_endpoint=True, ano_pca=args.ano_pca, page_size=page_size)
        if not _ok:
            logging.error("PCA: término antecipado (LED não confirmado)")
    else:
        # Modo diário para PCA: a API /v1/pca/atualizacao retorna vazio quando dataInicio == dataFim.
        # Portanto, processar por janelas [D, D+1].
        cur_dt = dt_from
        while cur_dt <= dt_to:
            day_str = cur_dt.strftime("%Y%m%d")
            next_day_str = (cur_dt + timedelta(days=1)).strftime("%Y%m%d")
            if TRACE:
                ds_h = f"{day_str[:4]}-{day_str[4:6]}-{day_str[6:]}"
                nds_h = f"{next_day_str[:4]}-{next_day_str[4:6]}-{next_day_str[6:]}"
                logging.info("PCA TRACE: diário %s → %s", ds_h, nds_h)
            _ok = process_window(day_str, next_day_str, prefer_pca_endpoint=True, ano_pca=args.ano_pca, page_size=page_size)
            if not _ok:
                logging.error("PCA: encerrando execução diária devido a falha ao confirmar LED (dia %s)", day_str)
                break
            cur_dt += timedelta(days=1)


if __name__ == "__main__":
    main()
