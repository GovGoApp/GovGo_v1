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
        update_schedule_preproc_output,
    )
    from search.gvg_browser.gvg_debug import debug_log as dbg
    from search.gvg_browser.gvg_preprocessing import SearchQueryProcessor, ENABLE_SEARCH_V2
    from search.gvg_browser.gvg_search_core import (
        semantic_search, keyword_search, hybrid_search,
        correspondence_search, category_filtered_search,
        get_top_categories_for_query, set_relevance_filter_level
    )
except Exception:
    # Execução direta dentro da pasta scripts
    import sys, os
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from gvg_boletim import (
        list_active_schedules_all,
        record_boletim_results,
        touch_last_run,
        update_schedule_preproc_output,
    )
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
    from gvg_debug import debug_log as dbg
    from gvg_preprocessing import SearchQueryProcessor, ENABLE_SEARCH_V2
    from gvg_search_core import (
        semantic_search, keyword_search, hybrid_search,
        correspondence_search, category_filtered_search,
        get_top_categories_for_query, set_relevance_filter_level
    )


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


# Conversão de filtros (dict) para lista de condições SQL (igual ao Browser)
def _filters_to_sql_conditions(f: Dict[str, Any] | None) -> List[str]:
    if not f or not isinstance(f, dict):
        return []
    out: List[str] = []
    def _esc(x: str) -> str:
        return x.replace("'", "''").replace('%','%%')
    pncp = (f.get('pncp') or '').strip() if f.get('pncp') else ''
    orgao = (f.get('orgao') or '').strip() if f.get('orgao') else ''
    cnpj = (f.get('cnpj') or '').strip() if f.get('cnpj') else ''
    uasg = (f.get('uasg') or '').strip() if f.get('uasg') else ''
    uf_val = f.get('uf')
    municipio = (f.get('municipio') or '').strip() if f.get('municipio') else ''
    modalidade_id = f.get('modalidade_id') if f.get('modalidade_id') is not None else None
    modo_id = f.get('modo_id') if f.get('modo_id') is not None else None
    date_field = (f.get('date_field') or 'encerramento').strip()
    ds = (f.get('date_start') or '').strip() if f.get('date_start') else ''
    de = (f.get('date_end') or '').strip() if f.get('date_end') else ''
    if pncp:
        out.append(f"c.numero_controle_pncp = '{_esc(pncp)}'")
    if orgao:
        o = _esc(orgao)
        out.append(f"( c.orgao_entidade_razao_social ILIKE '%{o}%' OR c.unidade_orgao_nome_unidade ILIKE '%{o}%' )")
    if cnpj:
        out.append(f"c.orgao_entidade_cnpj = '{_esc(cnpj)}'")
    if uasg:
        out.append(f"c.unidade_orgao_codigo_unidade = '{_esc(uasg)}'")
    if isinstance(uf_val, list):
        ufs = [str(u).strip() for u in uf_val if str(u).strip()]
        if ufs:
            in_list = ", ".join([f"'{_esc(u)}'" for u in ufs])
            out.append(f"c.unidade_orgao_uf_sigla IN ({in_list})")
    else:
        uf = (str(uf_val).strip() if uf_val is not None else '')
        if uf:
            out.append(f"c.unidade_orgao_uf_sigla = '{_esc(uf)}'")
    if municipio:
        parts = [p.strip() for p in municipio.split(',') if p and p.strip()]
        if parts:
            ors = [f"c.unidade_orgao_municipio_nome ILIKE '%{_esc(p)}%'" for p in parts]
            out.append("( " + " OR ".join(ors) + " )")
    if isinstance(modalidade_id, list):
        mods = [str(x).strip() for x in modalidade_id if str(x).strip()]
        if mods:
            in_list = ", ".join([f"'{_esc(m)}'" for m in mods])
            out.append(f"c.modalidade_id IN ({in_list})")
    else:
        mod = (str(modalidade_id).strip() if modalidade_id is not None else '')
        if mod:
            out.append(f"c.modalidade_id = '{_esc(mod)}'")
    if isinstance(modo_id, list):
        modos = [str(x).strip() for x in modo_id if str(x).strip()]
        if modos:
            in_list2 = ", ".join([f"'{_esc(m)}'" for m in modos])
            out.append(f"c.modo_disputa_id IN ({in_list2})")
    else:
        md = (str(modo_id).strip() if modo_id is not None else '')
        if md:
            out.append(f"c.modo_disputa_id = '{_esc(md)}'")
    col = 'data_encerramento_proposta'
    if date_field == 'abertura':
        col = 'data_abertura_proposta'
    elif date_field == 'publicacao':
        col = 'data_inclusao'
    if ds and de:
        out.append(f"to_date(NULLIF(c.{col},''),'YYYY-MM-DD') BETWEEN to_date('{ds}','YYYY-MM-DD') AND to_date('{de}','YYYY-MM-DD')")
    elif ds:
        out.append(f"to_date(NULLIF(c.{col},''),'YYYY-MM-DD') >= to_date('{ds}','YYYY-MM-DD')")
    elif de:
        out.append(f"to_date(NULLIF(c.{col},''),'YYYY-MM-DD') <= to_date('{de}','YYYY-MM-DD')")
    return out


def _to_float(value):
    try:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        import re as _re
        s = str(value).strip()
        if not s:
            return None
        s = _re.sub(r"[^0-9,\.-]", "", s)
        if s.count(',') == 1 and s.count('.') >= 1:
            s = s.replace('.', '').replace(',', '.')
        elif s.count(',') == 1 and s.count('.') == 0:
            s = s.replace(',', '.')
        elif s.count(',') > 1 and s.count('.') == 0:
            s = s.replace(',', '')
        return float(s)
    except Exception:
        return None


def _as_bool(x, default: bool = False) -> bool:
    """Converte valores diversos (bool/int/str) para bool de forma previsível.

    Aceita: True/False, 1/0, "true"/"false", "yes"/"no", "on"/"off", "1"/"0".
    Valores None ou desconhecidos retornam o default.
    """
    try:
        if x is None:
            return default
        if isinstance(x, bool):
            return x
        if isinstance(x, (int, float)):
            return x != 0
        if isinstance(x, str):
            s = x.strip().lower()
            if s in ("true", "1", "yes", "on", "y", "t"):
                return True
            if s in ("false", "0", "no", "off", "n", "f", ""):
                return False
    except Exception:
        pass
    return default


def _sort_results(results: List[Dict[str, Any]], order_mode: int) -> List[Dict[str, Any]]:
    if not results:
        return results
    if order_mode == 1:
        return sorted(results, key=lambda x: x.get('similarity', 0), reverse=True)
    if order_mode == 2:
        from datetime import datetime as _dt
        def _to_date(s):
            if not s:
                return None
            ss = str(s)
            for fmt in ('%Y-%m-%d','%d/%m/%Y'):
                try:
                    return _dt.strptime(ss[:10], fmt).date()
                except Exception:
                    continue
            return None
        def _date_key(item: Dict[str, Any]):
            d = (item.get('details') or {})
            v = d.get('data_encerramento_proposta') or d.get('dataEncerramentoProposta') or d.get('dataencerramentoproposta')
            return _to_date(v) or _dt.max.date()
        return sorted(results, key=_date_key)
    if order_mode == 3:
        def _value_key(item: Dict[str, Any]) -> float:
            d = (item.get('details') or {})
            v_est = d.get('valor_total_estimado') or d.get('valorTotalEstimado') or d.get('valortotalestimado')
            v = _to_float(v_est)
            return -(v if v is not None else -1.0)
        return sorted(results, key=_value_key)
    return results


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
        filter_expired = _as_bool(cfg.get('filter_expired'), default=True)
        negation_emb = bool(cfg.get('negation_emb', True))

        # Log dos parâmetros que serão enviados para a busca
        # (Parâmetros omitidos do log para reduzir ruído)

        # Executa busca respeitando snapshot, sem IA por padrão (usa cache de pré-processamento, se houver)
        try:
            filters_dict = s.get('filters') if isinstance(s.get('filters'), dict) else {}
            filters_sql = _filters_to_sql_conditions(filters_dict)

            # Ler EXACTO preproc_output do BD, se existir
            preproc = s.get('preproc_output') if isinstance(s.get('preproc_output'), dict) else None
            info = None
            if preproc and isinstance(preproc, dict):
                info = preproc
                where_sql = info.get('sql_conditions') or []
                base_terms = (info.get('search_terms') or query or '').strip()
                try:
                    dbg('PRE', f"[BOLETIM] cache HIT user_schedule.preproc_output sid={sid} terms='{base_terms[:60]}' sql_conds={len(where_sql)}")
                except Exception:
                    pass
            else:
                # Sempre processar se não houver cache (alinha ao GSB)
                try:
                    dbg('PRE', f"[BOLETIM] cache MISS sid={sid} (gerando preproc_output)")
                except Exception:
                    pass
                processor = SearchQueryProcessor()
                try:
                    info = processor.process_query_v2(query or '', filters_sql) if ENABLE_SEARCH_V2 else processor.process_query(query or '')
                except Exception:
                    info = {'search_terms': query or '', 'negative_terms': '', 'sql_conditions': filters_sql, 'embeddings': bool((query or '').strip())}
                if not isinstance(info, dict):
                    info = {'search_terms': query or '', 'negative_terms': '', 'sql_conditions': filters_sql, 'embeddings': bool((query or '').strip())}
                # Salvar EXACTAMENTE output
                try:
                    update_schedule_preproc_output(sid, info)
                    try:
                        dbg('PRE', f"[BOLETIM] assistant OUTPUT+SAVE sid={sid} terms='{(info.get('search_terms') or '')[:60]}' sql_conds={len(info.get('sql_conditions') or [])}")
                    except Exception:
                        pass
                except Exception:
                    pass
                where_sql = info.get('sql_conditions') or filters_sql
                base_terms = (info.get('search_terms') or query or '').strip()

            # Aplicar filtro de encerrados de forma explícita no where_sql e nas sql_conditions do preproc
            if filter_expired:
                _enc_filter = "to_date(NULLIF(c.data_encerramento_proposta,''),'YYYY-MM-DD') >= CURRENT_DATE"
                try:
                    # Injetar no where_sql (usado por approaches com where_sql)
                    where_sql = list(where_sql or [])
                    if _enc_filter not in where_sql:
                        where_sql.append(_enc_filter)
                    # Injetar também nas sql_conditions do preproc (usado por query_obj nas buscas diretas)
                    if isinstance(info, dict):
                        sc = list((info.get('sql_conditions') or []))
                        if _enc_filter not in sc:
                            sc.append(_enc_filter)
                            info['sql_conditions'] = sc
                    log_line("Filtro de encerrados aplicado (filter_expired=True)")
                except Exception:
                    pass

            # Negative terms (usados para eventual embedding / futura extensão) - manter referência
            negative_terms = ''
            try:
                negative_terms = (info.get('negative_terms') or '') if isinstance(info, dict) else ''
            except Exception:
                negative_terms = ''

            # Alinhar relevância
            try:
                set_relevance_filter_level(relevance_level)
            except Exception:
                pass

            results: List[Dict[str, Any]] = []
            # Monta objeto unificado de query para o core (evita reprocessamento interno)
            query_obj = {
                'original_query': query,
                'search_terms': (info.get('search_terms') if isinstance(info, dict) else query) or query,
                'negative_terms': (info.get('negative_terms') if isinstance(info, dict) else '') or '',
                'sql_conditions': (info.get('sql_conditions') if isinstance(info, dict) else where_sql) or [],
                'embeddings': (info.get('embeddings') if isinstance(info, dict) and info.get('embeddings') is not None else True),
                'explanation': (info.get('explanation') if isinstance(info, dict) else 'Pré-processado boletim') or 'Pré-processado boletim'
            }

            if search_approach == 1:
                if search_type == 1:
                    results, _ = semantic_search(query_obj, limit=max_results, filter_expired=filter_expired, use_negation=negation_emb)
                elif search_type == 2:
                    results, _ = keyword_search(query_obj, limit=max_results, filter_expired=filter_expired)
                else:
                    results, _ = hybrid_search(query_obj, limit=max_results, filter_expired=filter_expired, use_negation=negation_emb)
            elif search_approach == 2:
                cats = get_top_categories_for_query(query_text=base_terms or query, top_n=top_categories_count, use_negation=False, search_type=search_type, console=None)
                if cats:
                    # correspondence_search ainda recebe string; where_sql já aplicado via preproc -> passamos condições também
                    results, _, _ = correspondence_search(query_text=query, top_categories=cats, limit=max_results, filter_expired=filter_expired, console=None, where_sql=where_sql)
            else:
                cats = get_top_categories_for_query(query_text=base_terms or query, top_n=top_categories_count, use_negation=False, search_type=search_type, console=None)
                if cats:
                    # category_filtered_search aceita string; passa where_sql com filtros
                    results, _, _ = category_filtered_search(query_text=query, search_type=search_type, top_categories=cats, limit=max_results, filter_expired=filter_expired, use_negation=negation_emb, console=None, where_sql=where_sql)

            # Ordenação e rank
            results = _sort_results(results or [], sort_mode or 1)
            for idx, r in enumerate(results, 1):
                r['rank'] = idx
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
        rows_all = _build_rows_from_search(results or [])

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
        # Evento de uso boletim_run
        try:
            from gvg_usage import usage_event_start, usage_event_finish  # type: ignore
            usage_event_start(str(uid), 'boletim_run', ref_type='boletim', ref_id=str(sid))
            usage_event_finish({'results': len(rows)})
        except Exception:
            pass

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
