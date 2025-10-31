#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
01_processing (Ata de Registro de Preços)

Objetivo
- Baixar atas por vigência (/v1/atas) e por atualização (/v1/atas/atualizacao)
- Inserir/atualizar em public.ata (idempotente por numero_controle_pncp_ata)
- Persistir estado (LPD) em system_config (ata_last_processed_date) e vigência no backfill
- Registrar métricas em pipeline_run_stats (stage="ata.01")

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
from datetime import datetime, timedelta
from typing import Any, Dict, Iterable, List, Optional, Tuple

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import psycopg2
import psycopg2.extras
from dotenv import load_dotenv
from rich.progress import Progress, BarColumn, TimeElapsedColumn, TimeRemainingColumn, SpinnerColumn, TextColumn

STAGE_NAME = "ata.01"
DEFAULT_PAGE_SIZE = 200
BASE_URL = os.environ.get("PNCP_CONSULTA_BASE_URL", "https://pncp.gov.br/api/consulta")

CFG_LAST_PROCESSED = "last_processed_date_ata"
CFG_VIG_FROM = "ata_last_vigencia_from"
CFG_VIG_TO = "ata_last_vigencia_to"


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


def normalize_ata(api_obj: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "numero_controle_ata_pncp": api_obj.get("numeroControlePNCPAta"),
        "numero_controle_pncp_compra": api_obj.get("numeroControlePNCPCompra"),
        "numero_ata_registro_preco": api_obj.get("numeroAtaRegistroPreco"),
        "ano_ata": api_obj.get("anoAta"),
        "data_assinatura": api_obj.get("dataAssinatura"),
        "vigencia_inicio": api_obj.get("vigenciaInicio"),
        "vigencia_fim": api_obj.get("vigenciaFim"),
        "data_cancelamento": api_obj.get("dataCancelamento"),
        "cancelado": api_obj.get("cancelado"),
        "objeto_contratacao": api_obj.get("objetoContratacao"),
        "cnpj_orgao": api_obj.get("cnpjOrgao"),
        "nome_orgao": api_obj.get("nomeOrgao"),
        "codigo_unidade_orgao": api_obj.get("codigoUnidadeOrgao"),
        "nome_unidade_orgao": api_obj.get("nomeUnidadeOrgao"),
        "cnpj_orgao_subrogado": api_obj.get("cnpjOrgaoSubrogado"),
        "nome_orgao_subrogado": api_obj.get("nomeOrgaoSubrogado"),
        "codigo_unidade_orgao_subrogado": api_obj.get("codigoUnidadeOrgaoSubrogado"),
        "nome_unidade_orgao_subrogado": api_obj.get("nomeUnidadeOrgaoSubrogado"),
        "usuario": api_obj.get("usuario"),
        "data_publicacao_pncp": api_obj.get("dataPublicacaoPncp"),
        "data_inclusao": api_obj.get("dataInclusao"),
        "data_atualizacao": api_obj.get("dataAtualizacao"),
        "data_atualizacao_global": api_obj.get("dataAtualizacaoGlobal"),
    }


def upsert_atas(cur, atas: List[Dict[str, Any]]) -> Tuple[int, int]:
    if not atas:
        return 0, 0
    psycopg2.extras.execute_values(
        cur,
        """
        INSERT INTO public.ata (
            numero_controle_ata_pncp,
            numero_controle_pncp_compra,
            numero_ata_registro_preco,
            ano_ata,
            data_assinatura,
            vigencia_inicio,
            vigencia_fim,
            data_cancelamento,
            cancelado,
            objeto_contratacao,
            cnpj_orgao,
            nome_orgao,
            codigo_unidade_orgao,
            nome_unidade_orgao,
            cnpj_orgao_subrogado,
            nome_orgao_subrogado,
            codigo_unidade_orgao_subrogado,
            nome_unidade_orgao_subrogado,
            usuario,
            data_publicacao_pncp,
            data_inclusao,
            data_atualizacao,
            data_atualizacao_global
        ) VALUES %s
        ON CONFLICT (numero_controle_ata_pncp) DO UPDATE SET
            numero_controle_pncp_compra = EXCLUDED.numero_controle_pncp_compra,
            numero_ata_registro_preco = EXCLUDED.numero_ata_registro_preco,
            ano_ata = EXCLUDED.ano_ata,
            data_assinatura = EXCLUDED.data_assinatura,
            vigencia_inicio = EXCLUDED.vigencia_inicio,
            vigencia_fim = EXCLUDED.vigencia_fim,
            data_cancelamento = EXCLUDED.data_cancelamento,
            cancelado = EXCLUDED.cancelado,
            objeto_contratacao = EXCLUDED.objeto_contratacao,
            cnpj_orgao = EXCLUDED.cnpj_orgao,
            nome_orgao = EXCLUDED.nome_orgao,
            codigo_unidade_orgao = EXCLUDED.codigo_unidade_orgao,
            nome_unidade_orgao = EXCLUDED.nome_unidade_orgao,
            cnpj_orgao_subrogado = EXCLUDED.cnpj_orgao_subrogado,
            nome_orgao_subrogado = EXCLUDED.nome_orgao_subrogado,
            codigo_unidade_orgao_subrogado = EXCLUDED.codigo_unidade_orgao_subrogado,
            nome_unidade_orgao_subrogado = EXCLUDED.nome_unidade_orgao_subrogado,
            usuario = EXCLUDED.usuario,
            data_publicacao_pncp = EXCLUDED.data_publicacao_pncp,
            data_inclusao = EXCLUDED.data_inclusao,
            data_atualizacao = EXCLUDED.data_atualizacao,
            data_atualizacao_global = EXCLUDED.data_atualizacao_global
        """,
        [
            (
                a.get("numero_controle_ata_pncp"),
                a.get("numero_controle_pncp_compra"),
                a.get("numero_ata_registro_preco"),
                a.get("ano_ata"),
                a.get("data_assinatura"),
                a.get("vigencia_inicio"),
                a.get("vigencia_fim"),
                a.get("data_cancelamento"),
                a.get("cancelado"),
                a.get("objeto_contratacao"),
                a.get("cnpj_orgao"),
                a.get("nome_orgao"),
                a.get("codigo_unidade_orgao"),
                a.get("nome_unidade_orgao"),
                a.get("cnpj_orgao_subrogado"),
                a.get("nome_orgao_subrogado"),
                a.get("codigo_unidade_orgao_subrogado"),
                a.get("nome_unidade_orgao_subrogado"),
                a.get("usuario"),
                a.get("data_publicacao_pncp"),
                a.get("data_inclusao"),
                a.get("data_atualizacao"),
                a.get("data_atualizacao_global"),
            )
            for a in atas
        ],
        page_size=1000,
    )
    return len(atas), 0


def fetch_atas_page(session: requests.Session, url: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    resp = session.get(url, params=params, timeout=60)
    if resp.status_code == 204:
        return []
    resp.raise_for_status()
    try:
        data = resp.json()
    except Exception:
        logging.warning("ATA: resposta sem JSON valido (status=%s)", resp.status_code)
        return []
    if isinstance(data, list):
        return data
    return data.get("data") or []


def fetch_atas_window(session: requests.Session, url: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Agrega todas as páginas de ATAs usando totalPaginas quando disponível."""
    params0 = params.copy()
    params0["pagina"] = 1
    # logs detalhados de request removidos para não poluir a barra
    r0 = session.get(url, params=params0, timeout=60)
    if r0.status_code == 204:
        return []
    r0.raise_for_status()
    try:
        j0 = r0.json() or {}
    except Exception:
        logging.warning("ATA: resposta sem JSON valido na pagina 1 (status=%s)", r0.status_code)
        return []

    if isinstance(j0, list):
        return list(j0)

    data = list(j0.get("data") or [])
    total_pag = int(j0.get("totalPaginas", 1) or 1)
    total_reg = j0.get("totalRegistros")
    rest = j0.get("paginasRestantes")
    empty = j0.get("empty")
    # sem log por página

    # Prefixo com dia/intervalo na barra
    def _fmt(d: Optional[str]) -> Optional[str]:
        if not d or len(d) != 8:
            return None
        return f"{d[6:8]}/{d[4:6]}/{d[0:4]}"
    d1 = _fmt(params.get("dataInicial"))
    d2 = _fmt(params.get("dataFinal"))
    if d1 and d2:
        if d1 == d2:
            label_prefix = f"Dia {d1}: Atas"
        else:
            label_prefix = f"Intervalo {d1} → {d2}: Atas"
    else:
        label_prefix = "Atas"

    with Progress(
        SpinnerColumn(style="yellow"),
        TextColumn(f"[bold]{label_prefix}[/] {{task.description}}"),
        BarColumn(bar_width=None),
        TextColumn("{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        transient=False,
    ) as progress:
        task = progress.add_task(f"1/{total_pag}", total=total_pag)
        progress.advance(task, 1)

        for p in range(2, total_pag + 1):
            params_p = params.copy()
            params_p["pagina"] = p
            params_p["tamanhoPagina"] = params.get("tamanhoPagina", DEFAULT_PAGE_SIZE)
            # sem log de request por página
            rp = session.get(url, params=params_p, timeout=60)
            if rp.status_code == 204:
                break
            rp.raise_for_status()
            try:
                jp = rp.json() or {}
            except Exception:
                logging.warning("ATA: resposta sem JSON valido na pagina %s (status=%s)", p, rp.status_code)
                break
            page_list = jp if isinstance(jp, list) else (jp.get("data") or [])
            # sem log por página; apenas progresso visual
            data.extend(list(page_list))
            progress.update(task, advance=1, description=f"{p}/{total_pag}")

    return data


def process_window(date_from: str, date_to: str, mode: str = "vigencia") -> None:
    """mode: "vigencia" usa /v1/atas; "atualizacao" usa /v1/atas/atualizacao"""
    # Carrega exclusivamente o .env de scripts/pncp/.env
    env_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".env"))
    load_dotenv(env_path)
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    started_at = datetime.now()

    url = f"{BASE_URL}/v1/atas" if mode == "vigencia" else f"{BASE_URL}/v1/atas/atualizacao"
    params = {
        "dataInicial": date_from,
        "dataFinal": date_to,
        "pagina": 1,
        "tamanhoPagina": DEFAULT_PAGE_SIZE,
    }
    # Log do dia/intervalo a ser processado (minimalista)
    if date_from == date_to:
        logging.info("ATA: processando dia %s (mode=%s)", date_from, mode)
    else:
        logging.info("ATA: processando intervalo %s → %s (mode=%s)", date_from, date_to, mode)

    total_downloaded = 0
    inserted = 0
    updated = 0
    errors = 0

    session = build_session()

    with get_db_conn() as conn:
        conn.autocommit = False
        with conn.cursor() as cur:
            try:
                # Agrega todas as páginas para evitar erro 400 em pagina fora do range
                items_all = fetch_atas_window(session, url, params)
                total_downloaded = len(items_all)

                # Dedup por numero_controle_ata_pncp
                rows_all = [normalize_ata(obj) for obj in items_all]
                dmap: Dict[str, Dict[str, Any]] = {}
                for r in rows_all:
                    k = r.get("numero_controle_ata_pncp")
                    if not k:
                        continue
                    if k not in dmap:
                        dmap[k] = r
                rows_dedup = list(dmap.values())
                if rows_dedup:
                    # silêncio: sem logs de deduplicação
                    ins, upd = upsert_atas(cur, rows_dedup)
                    inserted += ins
                    updated += upd

                # Atualiza estado
                if mode == "vigencia":
                    set_system_config(cur, CFG_VIG_FROM, date_from)
                    set_system_config(cur, CFG_VIG_TO, date_to)
                else:
                    set_system_config(cur, CFG_LAST_PROCESSED, date_to)
                conn.commit()
            except Exception:
                conn.rollback()
                logging.exception("Erro no processamento da janela de atas")
                errors += 1
            finally:
                try:
                    insert_pipeline_run_stats(cur, STAGE_NAME, date_to, inserted, 0)
                    conn.commit()
                except Exception:
                    conn.rollback()
                    logging.exception("Falha ao gravar pipeline_run_stats (ata)")


def main():
    parser = argparse.ArgumentParser(description="Pipeline 01 - Atas (processing)")
    parser.add_argument("--mode", choices=["vigencia", "atualizacao"], default="vigencia")
    parser.add_argument("--tipo", choices=["periodo", "diario"], default="periodo", help="Modo de execução: periodo (uma chamada) ou diario (dia-a-dia)")
    parser.add_argument("--from", dest="date_from", required=False, help="AAAAMMDD")
    parser.add_argument("--to", dest="date_to", required=False, help="AAAAMMDD")
    args = parser.parse_args()

    # Defaults baseados em LED: sem --from usa last_processed_date_ata; sem --to usa hoje.
    # Se nenhum for informado e LED==hoje, não faz nada.
    env_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".env"))
    load_dotenv(env_path)

    today = datetime.now().strftime("%Y%m%d")
    led = None
    try:
        with get_db_conn() as conn:
            with conn.cursor() as cur:
                led = get_system_config(cur, CFG_LAST_PROCESSED)
    except Exception:
        led = None

    date_from = args.date_from or (led or today)
    date_to = args.date_to or today

    # Validação e comportamento diario/periodo
    try:
        dt_from = datetime.strptime(date_from, "%Y%m%d")
        dt_to = datetime.strptime(date_to, "%Y%m%d")
    except Exception:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
        logging.error("ATA: formato de data inválido. Use AAAAMMDD.")
        return
    if dt_from > dt_to:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
        logging.error("ATA: data inicial é maior que a data final.")
        return

    if not args.date_from and not args.date_to and (led == today):
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
        logging.info("ATA: LED (%s) já está no dia atual (%s). Nada a fazer.", led, today)
        return

    if args.tipo == "periodo":
        process_window(date_from, date_to, mode=args.mode)
    else:
        cur_dt = dt_from
        while cur_dt <= dt_to:
            day_str = cur_dt.strftime("%Y%m%d")
            process_window(day_str, day_str, mode=args.mode)
            cur_dt += timedelta(days=1)


if __name__ == "__main__":
    main()
