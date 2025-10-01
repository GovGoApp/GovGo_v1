"""
CLI para executar boletins agendados (user_schedule) e gravar resultados (user_boletim).

Uso local (PowerShell):
  python -m search.gvg_browser.scripts.run_scheduled_boletins

Notas:
- Não agenda nada por si só; é para ser chamado por um scheduler externo.
- Hoje só lista e executa DIARIO/SEMANAL conforme dia da semana.
"""

from __future__ import annotations

import uuid
import os
import sys
from pathlib import Path

# Garante que o pacote 'search' (raiz do repo) esteja no sys.path quando rodado via cron
try:
    repo_root = str(Path(__file__).resolve().parents[3])
    if repo_root not in sys.path:
        sys.path.insert(0, repo_root)
except Exception:
    pass
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import json

try:
    # Execução como pacote
    from search.gvg_browser.gvg_boletim import (
        list_active_schedules_all,
        record_boletim_results,
        touch_last_run,
    )
    from search.search_v1.GvG_Search_Function import gvg_search  # retorna dict com 'results'
    from search.gvg_browser.gvg_debug import debug_log as dbg
except Exception:
    # Execução direta dentro da pasta scripts
    import sys, os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from gvg_boletim import (
        list_active_schedules_all,
        record_boletim_results,
        touch_last_run,
    )
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
    from search_v1.GvG_Search_Function import gvg_search  # retorna dict com 'results'
    from gvg_debug import debug_log as dbg


SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOGS_DIR = os.path.join(SCRIPT_DIR, "logs")
os.makedirs(LOGS_DIR, exist_ok=True)

# Log compartilhado estilo pipeline (stdout + arquivo único por sessão)
PIPELINE_TIMESTAMP = os.getenv("PIPELINE_TIMESTAMP") or datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
LOG_FILE = os.path.join(LOGS_DIR, f"log_{PIPELINE_TIMESTAMP}.log")

def log_line(msg: str) -> None:
    try:
        print(msg, flush=True)
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass


def _build_rows_from_search(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    def _first(det: Dict[str, Any], keys: List[str]) -> Any:
        for k in keys:
            if k in det and det.get(k) not in (None, ""):
                return det.get(k)
        return None
    def _compact_payload(det: Dict[str, Any]) -> Dict[str, Any]:
        return {
            # identificação básica
            'objeto': _first(det, ['objeto_compra', 'objetoCompra', 'objeto_contrato', 'objetoContrato']),
            # órgão/unidade/localização
            'orgao': _first(det, ['orgao_entidade_razao_social', 'orgaoEntidadeRazaoSocial', 'orgao_entidade_razaosocial']),
            'unidade': _first(det, ['unidade_orgao_nome_unidade', 'unidadeorgao_nomeunidade']),
            'municipio': _first(det, ['unidade_orgao_municipio_nome', 'unidadeorgao_municipionome']),
            'uf': _first(det, ['unidade_orgao_uf_sigla', 'unidadeorgao_ufsigla']),
            # valores/modalidade
            'valor': _first(det, ['valor_total_estimado', 'valorTotalEstimado', 'valor_total_homologado', 'valorGlobal', 'valor_final', 'valorFinal']),
            'modalidade': _first(det, ['modalidade_nome', 'modalidadeNome']),
            'modo_disputa': _first(det, ['modo_disputa_nome', 'modoDisputaNome']),
            # datas principais
            'data_publicacao_pncp': _first(det, ['dataPublicacao', 'data_publicacao_pncp']),
            'data_encerramento_proposta': _first(det, ['dataEncerramentoProposta', 'data_encerramento_proposta']),
            # links úteis
            'links': {
                'origem': _first(det, ['link_sistema_origem', 'linkSistemaOrigem']),
                'processo': _first(det, ['link_processo_eletronico', 'linkProcessoEletronico'])
            }
        }
    for r in results or []:
        det = r.get('details') or {}
        pid = (
            det.get('numerocontrolepncp')
            or det.get('numeroControlePNCP')
            or det.get('numero_controle_pncp')
            or r.get('id')
            or r.get('numero_controle')
        )
        if not pid:
            continue
        compact = _compact_payload(det)
        rows.append({
            'numero_controle_pncp': str(pid),
            'similarity': r.get('similarity'),
            'data_publicacao_pncp': compact.get('data_publicacao_pncp'),
            'data_encerramento_proposta': compact.get('data_encerramento_proposta'),
            'payload': compact,
        })
    return rows


def run_once(now: Optional[datetime] = None) -> None:
    now = now or datetime.now(timezone.utc)
    # Cabeçalho
    log_line("================================================================================")
    log_line(f"[1/2] EXECUÇÃO DE BOLETINS — Sessão: {PIPELINE_TIMESTAMP}")
    log_line(f"Data: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    log_line("================================================================================")

    schedules = list_active_schedules_all(now)
    log_line(f"Boletins ativos hoje (após filtro de dias): {len(schedules)}")
    # Preview: quais boletins serão executados hoje e o motivo
    try:
        dow_map = {0: 'seg', 1: 'ter', 2: 'qua', 3: 'qui', 4: 'sex', 5: 'sab', 6: 'dom'}
        dow = dow_map.get(now.weekday())
        log_line(f"Prévia: {len(schedules)} boletim(ns) hoje {now.strftime('%Y-%m-%d')} (dow={dow})")
    except Exception:
        pass

    # Barra de progresso por boletim
    total = len(schedules)
    done = 0
    last_pct = -1

    executed = 0
    skipped = 0

    for s in schedules:
        sid = s['id']
        uid = s['user_id']
        query = s['query_text']
        # Checagem de frequência por tipo de agenda antes de executar
        stype = (s.get('schedule_type') or '').upper()
        sdetail = s.get('schedule_detail') or {}
        if isinstance(sdetail, str):
            try:
                sdetail = json.loads(sdetail)
            except Exception:
                sdetail = {}
        last_run = s.get('last_run_at')

        def _to_dt(x: Any) -> Optional[datetime]:
            if not x:
                return None
            if isinstance(x, datetime):
                return x if x.tzinfo else x.replace(tzinfo=timezone.utc)
            if isinstance(x, str):
                try:
                    return datetime.fromisoformat(x.replace('Z', '+00:00'))
                except Exception:
                    try:
                        return datetime.strptime(x[:10], '%Y-%m-%d').replace(tzinfo=timezone.utc)
                    except Exception:
                        return None
            return None

        lr_dt = _to_dt(last_run)
        now_date = now.astimezone(timezone.utc).date()
        ran_today = (lr_dt.astimezone(timezone.utc).date() == now_date) if lr_dt else False

        # MULTIDIARIO: respeita min_interval_minutes se definido em schedule_detail
        min_int = None
        try:
            v = (sdetail or {}).get('min_interval_minutes')
            if isinstance(v, (int, float)):
                min_int = int(v)
        except Exception:
            min_int = None

        if stype in ('DIARIO', 'SEMANAL') and ran_today:
            done += 1
            skipped += 1
            # Progresso também em skips
            pct = int((done * 100) / max(1, total))
            if pct == 100 or pct - last_pct >= 5:
                fill = int(round(pct * 20 / 100))
                bar = "█" * fill + "░" * (20 - fill)
                log_line(f"Execução: {pct}% [{bar}] ({done}/{total})")
                last_pct = pct
            continue
        if stype == 'MULTIDIARIO' and min_int and lr_dt and (now - lr_dt < timedelta(minutes=min_int)):
            done += 1
            skipped += 1
            pct = int((done * 100) / max(1, total))
            if pct == 100 or pct - last_pct >= 5:
                fill = int(round(pct * 20 / 100))
                bar = "█" * fill + "░" * (20 - fill)
                log_line(f"Execução: {pct}% [{bar}] ({done}/{total})")
                last_pct = pct
            continue

        log_line(f"Executando boletim {sid} :: '{query}'")

        # Extrai configurações do snapshot do boletim
        cfg = s.get('config_snapshot') or {}
        if isinstance(cfg, str):
            try:
                cfg = json.loads(cfg)
            except Exception:
                cfg = {}

        # Detalhes de agenda e canais (apenas logging por enquanto)
        sched_detail = s.get('schedule_detail') or {}
        if isinstance(sched_detail, str):
            try:
                sched_detail = json.loads(sched_detail)
            except Exception:
                sched_detail = {}
        channels = s.get('channels') or []
        if isinstance(channels, str):
            try:
                channels = json.loads(channels)
            except Exception:
                channels = [channels]

        # Defaults seguros
        search_type = int(cfg.get('search_type', 3))
        search_approach = int(cfg.get('search_approach', 3))
        relevance_level = int(cfg.get('relevance_level', 2))
        sort_mode = int(cfg.get('sort_mode', 1))
        max_results = int(cfg.get('max_results', 50))
        top_categories_count = int(cfg.get('top_categories_count', 10))
        filter_expired = bool(cfg.get('filter_expired', True))
        negation_emb = bool(cfg.get('negation_emb', True))

        # Log dos parâmetros que serão enviados para a busca
    # (Parâmetros omitidos do log para reduzir ruído)

        # Executa busca respeitando o snapshot (com proteção)
        try:
            resp = gvg_search(
                prompt=query,
                search=search_type,
                approach=search_approach,
                relevance=relevance_level,
                order=sort_mode,
                max_results=max_results,
                top_cat=top_categories_count,
                negation_emb=negation_emb,
                filter_expired=filter_expired,
                intelligent_toggle=False,
                export=None,
                return_export_paths=False,
                return_raw=True,
            )
        except Exception as e:
            log_line(f"ERRO busca sid={sid}: {e}")
            done += 1
            skipped += 1
            pct = int((done * 100) / max(1, total))
            if pct == 100 or pct - last_pct >= 5:
                fill = int(round(pct * 20 / 100))
                bar = "█" * fill + "░" * (20 - fill)
                log_line(f"Execução: {pct}% [{bar}] ({done}/{total})")
                last_pct = pct
            continue

        # Log dos parâmetros efetivos reconhecidos pela função
    # (Parâmetros efetivos omitidos do log)
        rows_all = _build_rows_from_search(resp.get('results') or [])

        # Delta: manter apenas itens com data_publicacao_pncp >= baseline (last_run_at)
        last_run = s.get('last_run_at')
        baseline_iso = None
        if last_run:
            try:
                if isinstance(last_run, str):
                    baseline_iso = last_run[:10]
                else:
                    baseline_iso = last_run.strftime('%Y-%m-%d')
            except Exception:
                baseline_iso = None

        def _parse_date_any(d: Any) -> Optional[str]:
            if not d:
                return None
            if isinstance(d, str):
                s = d.strip()
                try:
                    if len(s) >= 10 and s[4] == '-' and s[7] == '-':
                        return s[:10]
                except Exception:
                    pass
                try:
                    if '/' in s and len(s) >= 10:
                        dd, mm, yy = s[:10].split('/')
                        return f"{yy}-{mm}-{dd}"
                except Exception:
                    return None
                return None
            return None

        if baseline_iso:
            before = len(rows_all)
            rows = [r for r in rows_all if (_parse_date_any(r.get('data_publicacao_pncp')) or '') >= baseline_iso]
            kept = len(rows)
            # só loga delta se houve filtragem
            if kept != before:
                log_line(f"Delta baseline={baseline_iso}: {before}->{kept}")
        else:
            rows = rows_all

        run_token = uuid.uuid4().hex
        record_boletim_results(sid, uid, run_token, now, rows)
        log_line(f"Boletim {sid}: resultados gravados = {len(rows)}")

        # marcar last_run
        touch_last_run(sid, now)
        executed += 1

        # Atualiza progresso
        done += 1
        pct = int((done * 100) / max(1, total))
        if pct == 100 or pct - last_pct >= 5:
            fill = int(round(pct * 20 / 100))
            bar = "█" * fill + "░" * (20 - fill)
            log_line(f"Execução: {pct}% [{bar}] ({done}/{total})")
            last_pct = pct

    # envio por email será tratado em script separado (last_sent_at)
    log_line(f"Resumo: executados={executed}, pulados={skipped}, total={total}")
    log_line("Concluído: execução de boletins finalizada")


if __name__ == '__main__':
    run_once()
