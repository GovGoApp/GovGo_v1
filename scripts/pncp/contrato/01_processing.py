#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
01_processing (Contrato)

Objetivo
- Baixar contratos por janelas de data (publicação e atualização) da API Consulta PNCP
- Inserir/atualizar em public.contrato (idempotente por numero_controle_pncp)
- Persistir estado (LPD) em system_config (contrato_last_processed_date)
- Registrar métricas em pipeline_run_stats (stage="contrato.01")

Observações
- Datas como TEXT no BD (AAAAMMDD ou ISO conforme retorno); para este endpoint usar AAAAMMDD nos params
- Paginação baseada em totalPaginas; tamanhoPagina=50 para estabilidade
- Retries com backoff, timeouts, logs simples (sem prefixo custom)

Importante (IDs PNCP):
- numeroControlePNCP         → id do CONTRATO (máscara ...-2-...); mapear para contrato.numero_controle_pncp
- numeroControlePncpCompra   → id da CONTRATAÇÃO (máscara ...-1-...); mapear para contrato.numero_controle_pncp_compra
- A FK do contrato deve referenciar contratacao(numero_controle_pncp) PELO campo contrato.numero_controle_pncp_compra.
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

STAGE_NAME = "contrato.01"
DEFAULT_PAGE_SIZE = 200  # aumentar para 200 conforme solicitado
BASE_URL = os.environ.get("PNCP_CONSULTA_BASE_URL", "https://pncp.gov.br/api/consulta")

# system_config keys (LPD/LED/LCD por domínio)
CFG_LAST_PROCESSED = "last_processed_date_contrato"


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
    """Conecta usando apenas SUPABASE_* do scripts/pncp/.env (sem fallback de outras pastas)."""
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
    """Compatível com schema BDS1: (stage, date_ref, inserted_contratacoes, inserted_itens)."""
    cur.execute(
        """
        INSERT INTO pipeline_run_stats(stage, date_ref, inserted_contratacoes, inserted_itens)
        VALUES (%s, %s, %s, %s)
        """,
        (stage, date_ref, inserted_contratacoes, inserted_itens),
    )


def normalize_contrato(api_obj: Dict[str, Any]) -> Dict[str, Any]:
    """Converte o JSON da API para colunas existentes em public.contrato (BDS1).
    Alinhamento de IDs PNCP:
    - numeroControlePNCP (json)         → contrato.numero_controle_pncp (ID do contrato)
    - numeroControlePNCPCompra/PncpCompra (json) → contrato.numero_controle_pncp_compra (ID da contratação)
    """
    org = api_obj.get("orgaoEntidade") or {}
    und = api_obj.get("unidadeOrgao") or {}
    tipo = api_obj.get("tipoContrato") or {}
    cat = api_obj.get("categoriaProcesso") or {}

    # IDs PNCP corretamente mapeados
    numero_controle_pncp = api_obj.get("numeroControlePNCP")  # id do CONTRATO
    numero_controle_pncp_compra = (
        api_obj.get("numeroControlePNCPCompra")
        or api_obj.get("numeroControlePncpCompra")
    )  # id da CONTRATAÇÃO

    data_vigencia_inicio = api_obj.get("dataVigenciaInicio")
    vigencia_ano = None
    if isinstance(data_vigencia_inicio, str) and len(data_vigencia_inicio) >= 4:
        vigencia_ano = data_vigencia_inicio[0:4]

    return {
        "numero_controle_pncp": numero_controle_pncp,
        "numero_controle_pncp_compra": numero_controle_pncp_compra,
        "numero_contrato_empenho": api_obj.get("numeroContratoEmpenho"),
        "ano_contrato": api_obj.get("anoContrato"),
        "data_assinatura": api_obj.get("dataAssinatura"),
        "data_vigencia_inicio": data_vigencia_inicio,
        "data_vigencia_fim": api_obj.get("dataVigenciaFim"),
        "ni_fornecedor": api_obj.get("niFornecedor"),
        "tipo_pessoa": api_obj.get("tipoPessoa"),
        "sequencial_contrato": api_obj.get("sequencialContrato"),
        "processo": api_obj.get("processo"),
        "nome_razao_social_fornecedor": api_obj.get("nomeRazaoSocialFornecedor"),
        "numero_parcelas": api_obj.get("numeroParcelas"),
        "numero_retificacao": api_obj.get("numeroRetificacao"),
        "objeto_contrato": api_obj.get("objetoContrato"),
        "valor_inicial": api_obj.get("valorInicial"),
        "valor_parcela": api_obj.get("valorParcela"),
        "valor_global": api_obj.get("valorGlobal"),
        "data_atualizacao_global": api_obj.get("dataAtualizacaoGlobal"),
        "tipo_contrato_id": tipo.get("id"),
        "tipo_contrato_nome": tipo.get("nome"),
        "orgao_entidade_cnpj": org.get("cnpj"),
        "orgao_entidade_razaosocial": org.get("razaoSocial"),
        "orgao_entidade_poder_id": org.get("poderId"),
        "orgao_entidade_esfera_id": org.get("esferaId"),
        "categoria_processo_id": cat.get("id"),
        "categoria_processo_nome": cat.get("nome"),
        "unidade_orgao_uf_nome": und.get("ufNome"),
        "unidade_orgao_codigo_unidade": und.get("codigoUnidade"),
        "unidade_orgao_nome_unidade": und.get("nomeUnidade"),
        "unidade_orgao_uf_sigla": und.get("ufSigla"),
        "unidade_orgao_municipio_nome": und.get("municipioNome"),
        "unidade_orgao_codigo_ibge": und.get("codigoIbge"),
        "vigencia_ano": vigencia_ano,
    }


def upsert_contratos(cur, contratos: List[Dict[str, Any]]) -> Tuple[int, int]:
    """Upsert por numero_controle_pncp sem UNIQUE: faz UPDATE via VALUES + INSERT anti-join.
    Retorna (inserted, updated).
    """
    if not contratos:
        return 0, 0

    cols = [
        "numero_controle_pncp",
        "numero_controle_pncp_compra",
        "numero_contrato_empenho",
        "ano_contrato",
        "data_assinatura",
        "data_vigencia_inicio",
        "data_vigencia_fim",
        "ni_fornecedor",
        "tipo_pessoa",
        "sequencial_contrato",
        "processo",
        "nome_razao_social_fornecedor",
        "numero_parcelas",
        "numero_retificacao",
        "objeto_contrato",
        "valor_inicial",
        "valor_parcela",
        "valor_global",
        "data_atualizacao_global",
        "tipo_contrato_id",
        "tipo_contrato_nome",
        "orgao_entidade_cnpj",
        "orgao_entidade_razaosocial",
        "orgao_entidade_poder_id",
        "orgao_entidade_esfera_id",
        "categoria_processo_id",
        "categoria_processo_nome",
        "unidade_orgao_uf_nome",
        "unidade_orgao_codigo_unidade",
        "unidade_orgao_nome_unidade",
        "unidade_orgao_uf_sigla",
        "unidade_orgao_municipio_nome",
        "unidade_orgao_codigo_ibge",
        "vigencia_ano",
    ]

    values = [
        tuple(c.get(k) for k in cols)
        for c in contratos
    ]

    # 1) UPDATE existentes (chave: numero_controle_pncp; fallback quando NULL: (compra+empenho+ano))
    set_cols = [c for c in cols if c != "numero_controle_pncp"]
    set_clause = ",\n            ".join([f"{c} = v.{c}" for c in set_cols])
    join_cond = (
        "(t.numero_controle_pncp = v.numero_controle_pncp) OR "
        "(t.numero_controle_pncp IS NULL AND v.numero_controle_pncp IS NULL "
        "AND COALESCE(t.numero_controle_pncp_compra::text,'') = COALESCE(v.numero_controle_pncp_compra::text,'') "
        "AND COALESCE(t.numero_contrato_empenho::text,'') = COALESCE(v.numero_contrato_empenho::text,'') "
        "AND COALESCE(t.ano_contrato::text,'') = COALESCE(v.ano_contrato::text,''))"
    )
    update_sql = f"""
        UPDATE public.contrato AS t
           SET {set_clause}
          FROM (VALUES %s) AS v ({', '.join(cols)})
         WHERE {join_cond}
    """
    psycopg2.extras.execute_values(cur, update_sql, values, page_size=1000)
    updated = cur.rowcount or 0

    # 2) INSERT dos que não existem
    insert_sql = f"""
        INSERT INTO public.contrato ({', '.join(cols)})
        SELECT {', '.join(['v.' + c for c in cols])}
          FROM (VALUES %s) AS v ({', '.join(cols)})
          LEFT JOIN public.contrato t
                 ON (t.numero_controle_pncp = v.numero_controle_pncp)
                 OR (t.numero_controle_pncp IS NULL AND v.numero_controle_pncp IS NULL
                     AND COALESCE(t.numero_controle_pncp_compra::text,'') = COALESCE(v.numero_controle_pncp_compra::text,'')
                     AND COALESCE(t.numero_contrato_empenho::text,'') = COALESCE(v.numero_contrato_empenho::text,'')
                     AND COALESCE(t.ano_contrato::text,'') = COALESCE(v.ano_contrato::text,''))
         WHERE t.id_contrato IS NULL
                 ON CONFLICT (numero_controle_pncp) DO NOTHING
         RETURNING 1
    """
    psycopg2.extras.execute_values(cur, insert_sql, values, page_size=1000)
    inserted = len(cur.fetchall() or [])

    return inserted, updated


def fetch_contratos_window(session: requests.Session, url: str, params: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Agrega todas as páginas para a janela (dataInicial/dataFinal).

    Lida com duas formas de resposta:
    - lista simples JSON
    - objeto com 'data' + 'totalPaginas'
    """
    params0 = params.copy()
    params0["pagina"] = 1
    resp = session.get(url, params=params0, timeout=60)
    if resp.status_code == 204:
        return []
    resp.raise_for_status()
    jd = resp.json() or {}

    # lista simples
    if isinstance(jd, list):
        return jd

    data = list(jd.get("data") or [])
    total_pag = int(jd.get("totalPaginas", 1) or 1)
    # logs por página removidos para evitar poluir a barra de progresso

    # Progresso visual Rich para as páginas (inclui a página 1 já carregada)
    # Prefixo com dia/intervalo para a barra
    def _fmt(d: Optional[str]) -> Optional[str]:
        if not d or len(d) != 8:
            return None
        return f"{d[6:8]}/{d[4:6]}/{d[0:4]}"
    d1 = _fmt(params.get("dataInicial"))
    d2 = _fmt(params.get("dataFinal"))
    if d1 and d2:
        if d1 == d2:
            label_prefix = f"Dia {d1}: Contratos"
        else:
            label_prefix = f"Intervalo {d1} → {d2}: Contratos"
    else:
        label_prefix = "Contratos"
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

        # itera páginas restantes
        for p in range(2, total_pag + 1):
            params_p = params.copy()
            params_p["pagina"] = p
            params_p["tamanhoPagina"] = params.get("tamanhoPagina", DEFAULT_PAGE_SIZE)
            r = session.get(url, params=params_p, timeout=60)
            if r.status_code == 204:
                break
            r.raise_for_status()
            jd2 = r.json() or {}
            page_list = jd2 if isinstance(jd2, list) else (jd2.get("data") or [])
            if not page_list:
                break
            # sem logs por página; apenas atualiza a barra
            data.extend(list(page_list))
            progress.update(task, advance=1, description=f"{p}/{total_pag}")

    return data


def process_window(date_from: str, date_to: str, mode: str = "publicacao") -> None:
    """Processa janela de contratos.
    mode: "publicacao" usa /v1/contratos; "atualizacao" usa /v1/contratos/atualizacao
    """
    # Carrega exclusivamente o .env de scripts/pncp/.env
    env_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".env"))
    load_dotenv(env_path)
    # Logging sem horário, conforme solicitado
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    started_at = datetime.now(timezone.utc)
    # Log do dia/intervalo a ser processado
    if date_from == date_to:
        logging.info("Contratos: processando dia %s (mode=%s)", date_from, mode)
    else:
        logging.info("Contratos: processando intervalo %s → %s (mode=%s)", date_from, date_to, mode)

    url = f"{BASE_URL}/v1/contratos" if mode == "publicacao" else f"{BASE_URL}/v1/contratos/atualizacao"
    # Para /v1/contratos, o Manual PNCP indica AAAAMMDD (sem hífen)
    params = {
        "dataInicial": date_from,
        "dataFinal": date_to,
        "pagina": 1,
        "tamanhoPagina": DEFAULT_PAGE_SIZE,
    }

    total_pages = 0
    total_downloaded = 0
    inserted = 0
    updated = 0
    errors = 0

    session = build_session()

    with get_db_conn() as conn:
        conn.autocommit = False
        with conn.cursor() as cur:
            try:
                # Agregar todas as páginas da janela de uma vez
                items = fetch_contratos_window(session, url, params)
                total_downloaded = len(items)
                rows = [normalize_contrato(obj) for obj in items]
                # silêncio: barra de progresso já informa andamento
                # Vinculação ao FK: NÃO filtramos; se NÃO existir a contratação correspondente,
                # anulamos numero_controle_pncp_compra para não violar a FK e preservamos o id do contrato em numero_controle_pncp
                keys = [r.get("numero_controle_pncp_compra") for r in rows if r.get("numero_controle_pncp_compra")]
                existing: set[str] = set()
                if keys:
                    cur.execute(
                        """
                        SELECT numero_controle_pncp
                          FROM public.contratacao
                         WHERE numero_controle_pncp = ANY(%s)
                        """,
                        (keys,),
                    )
                    existing = {r[0] for r in cur.fetchall()}
                detached = 0
                for r in rows:
                    nc_compra = r.get("numero_controle_pncp_compra")
                    if nc_compra and nc_compra not in existing:
                        r["numero_controle_pncp_compra"] = None
                        detached += 1
                # silêncio: manter logs mínimos
                if rows:
                    ins, upd = upsert_contratos(cur, rows)
                    inserted += ins
                    updated += upd
                    # silêncio sobre upsert detalhado

                # Atualiza LPD apenas quando terminar com sucesso
                set_system_config(cur, CFG_LAST_PROCESSED, date_to)
                conn.commit()
            except Exception:
                conn.rollback()
                logging.exception("Erro no processamento da janela")
                errors += 1
            finally:
                try:
                    # BDS1: date_ref é o fim da janela (AAAAMMDD)
                    insert_pipeline_run_stats(cur, STAGE_NAME, date_to, inserted, 0)
                    conn.commit()
                except Exception:
                    conn.rollback()
                    logging.exception("Falha ao gravar pipeline_run_stats")


def main():
    parser = argparse.ArgumentParser(description="Pipeline 01 - Contratos (processing)")
    parser.add_argument("--mode", choices=["publicacao", "atualizacao"], default="atualizacao")
    parser.add_argument("--tipo", choices=["periodo", "diario"], default="diario", help="Modo de execução: periodo (uma chamada) ou diario (dia-a-dia)")
    parser.add_argument("--from", dest="date_from", required=False, help="AAAAMMDD")
    parser.add_argument("--to", dest="date_to", required=False, help="AAAAMMDD")
    args = parser.parse_args()

    # Janela padrão seguindo LEDs (system_config):
    # - Sem --from: usar last_processed_date_contrato
    # - Sem --to: usar current day
    # - Sem ambos: LED → current day; se LED == current day, não faz nada
    env_path = os.path.normpath(os.path.join(os.path.dirname(__file__), "..", ".env"))
    load_dotenv(env_path)
    today = datetime.now(timezone.utc).strftime("%Y%m%d")

    led = None
    try:
        with get_db_conn() as conn:
            with conn.cursor() as cur:
                led = get_system_config(cur, CFG_LAST_PROCESSED)
    except Exception:
        led = None

    date_from = args.date_from or (led or today)
    date_to = args.date_to or today

    # Validação básica de intervalo
    try:
        dt_from = datetime.strptime(date_from, "%Y%m%d")
        dt_to = datetime.strptime(date_to, "%Y%m%d")
    except Exception:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
        logging.error("Contratos: formato de data inválido. Use AAAAMMDD.")
        return
    if dt_from > dt_to:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
        logging.error("Contratos: data inicial é maior que a data final.")
        return

    # Caso nenhum dos dois tenha sido informado e LED seja hoje, não processa
    if not args.date_from and not args.date_to and (led == today):
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
        logging.info("Contratos: LED (%s) já está no dia atual (%s). Nada a fazer.", led, today)
        return

    if args.tipo == "periodo":
        process_window(date_from, date_to, mode=args.mode)
    else:
        # modo diario: processa dia a dia e atualiza LED por dia (process_window já grava o LED quando tiver sucesso)
        cur_dt = dt_from
        while cur_dt <= dt_to:
            day_str = cur_dt.strftime("%Y%m%d")
            process_window(day_str, day_str, mode=args.mode)
            cur_dt += timedelta(days=1)


if __name__ == "__main__":
    main()
