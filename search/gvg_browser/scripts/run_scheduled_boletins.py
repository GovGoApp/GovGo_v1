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
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import json

try:
    # Execução como pacote
    from search.gvg_browser.gvg_boletim import (
        list_active_schedules_all,
        record_boletim_results,
        fetch_unsent_results_for_boletim,
        mark_results_sent,
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
    fetch_unsent_results_for_boletim,
    mark_results_sent,
    touch_last_run,
    )
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
    from search_v1.GvG_Search_Function import gvg_search  # retorna dict com 'results'
    from gvg_debug import debug_log as dbg


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
    schedules = list_active_schedules_all(now)
    # Preview: quais boletins serão executados hoje e o motivo
    try:
        dow_map = {0: 'seg', 1: 'ter', 2: 'qua', 3: 'qui', 4: 'sex', 5: 'sab', 6: 'dom'}
        dow = dow_map.get(now.weekday())
        dbg('BOLETIM', f"Prévia: {len(schedules)} boletim(ns) hoje {now.strftime('%Y-%m-%d')} (dow={dow})")
        for s in schedules:
            stype = (s.get('schedule_type') or '').upper()
            sdetail = s.get('schedule_detail') or {}
            if isinstance(sdetail, str):
                try:
                    sdetail = json.loads(sdetail)
                except Exception:
                    sdetail = {}
            cfg_days = sdetail.get('days') if isinstance(sdetail, dict) else None
            days = []
            if stype in ('DIARIO', 'MULTIDIARIO'):
                days = list(cfg_days) if cfg_days else ['seg', 'ter', 'qua', 'qui', 'sex']
            elif stype == 'SEMANAL':
                days = list(cfg_days) if cfg_days else []
            motivo = f"hoje='{dow}' ∈ days={days}"
            dbg('BOLETIM', f"- id={s.get('id')} tipo={stype} {motivo}")
    except Exception:
        pass
    for s in schedules:
        sid = s['id']
        uid = s['user_id']
        query = s['query_text']
        dbg('BOLETIM', f"Executando boletim {sid} para user {uid}: '{query}'")

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
        search_type = int(cfg.get('search_type', 3))               # 1=semântica, 2=palavras, 3=híbrida
        search_approach = int(cfg.get('search_approach', 3))       # 1=direta, 2=correspondência, 3=filtro
        relevance_level = int(cfg.get('relevance_level', 2))       # 1..3
        sort_mode = int(cfg.get('sort_mode', 1))                   # 1..3
        max_results = int(cfg.get('max_results', 50))
        top_categories_count = int(cfg.get('top_categories_count', 10))
        filter_expired = bool(cfg.get('filter_expired', True))
        negation_emb = bool(cfg.get('negation_emb', True))

        # Log dos parâmetros que serão enviados para a busca
        try:
            params_preview = {
                'prompt': query,
                'search': search_type,
                'approach': search_approach,
                'relevance': relevance_level,
                'order': sort_mode,
                'max_results': max_results,
                'top_cat': top_categories_count,
                'negation_emb': negation_emb,
                'filter_expired': filter_expired,
                'schedule_detail': sched_detail,
                'channels': channels,
            }
            dbg('BOLETIM', 'Parâmetros gvg_search: ' + json.dumps(params_preview, ensure_ascii=False))
        except Exception:
            pass

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
            try:
                dbg('BOLETIM', f"ERRO gvg_search sid={sid} uid={uid}: {e}")
            except Exception:
                pass
            continue

        # Log dos parâmetros efetivos reconhecidos pela função
        try:
            eff_params = resp.get('params') if isinstance(resp, dict) else None
            if eff_params:
                dbg('BOLETIM', 'Parâmetros efetivos: ' + json.dumps(eff_params, ensure_ascii=False))
        except Exception:
            pass
        rows_all = _build_rows_from_search(resp.get('results') or [])

        # Delta: manter apenas itens com data_publicacao_pncp >= baseline (last_run_at)
        last_run = s.get('last_run_at')
        baseline_iso = None
        if last_run:
            try:
                # normaliza para YYYY-MM-DD
                if isinstance(last_run, str):
                    # tenta parse simples de 'YYYY-MM-DD'
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
                # formatos aceitos: YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS, DD/MM/YYYY
                try:
                    if len(s) >= 10 and s[4] == '-' and s[7] == '-':
                        return s[:10]
                except Exception:
                    pass
                try:
                    if '/' in s and len(s) >= 10:
                        # DD/MM/YYYY -> YYYY-MM-DD
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
            try:
                dbg('BOLETIM', f"Delta baseline={baseline_iso} filtrou {before} -> {kept}")
            except Exception:
                pass
        else:
            rows = rows_all
        run_token = uuid.uuid4().hex
        record_boletim_results(sid, uid, run_token, now, rows)

        # marcar last_run
        touch_last_run(sid, now)

        # opcional: marcar como enviados imediatamente (desligável no futuro)
        unsent = fetch_unsent_results_for_boletim(sid, baseline_iso)
        ids = [x['id'] for x in unsent]
        if ids:
            mark_results_sent(ids, now)


if __name__ == '__main__':
    run_once()
