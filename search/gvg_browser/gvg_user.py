"""
gvg_user.py
Funções auxiliares de usuário e histórico de prompts por usuário.

Agora usa usuário dinâmico quando há token/sessão; fallback anônimo apenas para compatibilidade.
"""
from __future__ import annotations

import os
import json
from typing import List, Optional, Dict, Any, Union
import datetime as _dt
import time
from gvg_database import (
    create_connection,  # compat quando precisar
    db_fetch_all, db_fetch_one, db_execute, db_execute_many,
    db_execute_returning_one,
)  # type: ignore
from gvg_debug import debug_log as dbg  # type: ignore
from gvg_schema import get_contratacao_core_columns, PRIMARY_KEY  # type: ignore
from gvg_search_core import _augment_aliases  # type: ignore

# Tenta importar auth para obter usuário da sessão (token em cookies)
try:
    from gvg_auth import get_user_from_token  # type: ignore
except ImportError:
    get_user_from_token = None  # type: ignore

# Usuário atual em memória (anônimo por padrão; será preenchido ao logar)
_CURRENT_USER = {
    'uid': '',
    'email': '',
    'name': 'Usuário',
}

# Permite injetar token (por camada Flask) em tempo de execução
_ACCESS_TOKEN: Optional[str] = None

# --- Caches leves ---
_SCHEMA_TYPES_CACHE: Dict[str, Dict[str, Any]] = {}
_DATA_CACHE: Dict[str, Any] = {}

_TTL_SCHEMA_SECONDS = 3600  # 60 minutos
_TTL_USER_DATA_SECONDS = 300  # 5 minutos


def _schema_types_cached(table: str) -> Dict[str, str]:
    now = time.time()
    ent = _SCHEMA_TYPES_CACHE.get(table)
    if ent and ent.get('expires', 0) > now:
        return ent.get('types', {})
    rows = db_fetch_all(
        (
            """
            SELECT column_name, udt_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = %s
            """
        ),
        (table,),
        ctx=f"USER.schema:describe:{table}"
    ) or []
    types = {r[0]: r[1] for r in rows}
    _SCHEMA_TYPES_CACHE[table] = {'types': types, 'expires': now + _TTL_SCHEMA_SECONDS}
    return types


def _schema_columns_cached(table: str) -> List[str]:
    return list(_schema_types_cached(table).keys())


def _cache_get(key: str):
    ent = _DATA_CACHE.get(key)
    if not ent:
        return None
    if ent.get('expires', 0) > time.time():
        return ent.get('value')
    _DATA_CACHE.pop(key, None)
    return None


def _cache_set(key: str, value: Any, ttl: int = _TTL_USER_DATA_SECONDS):
    _DATA_CACHE[key] = {'value': value, 'expires': time.time() + ttl}


def _cache_invalidate_prefix(prefix: str):
    for k in list(_DATA_CACHE.keys()):
        if str(k).startswith(prefix):
            _DATA_CACHE.pop(k, None)


def set_access_token(token: Optional[str]):
    global _ACCESS_TOKEN
    _ACCESS_TOKEN = token
    try:
        dbg('AUTH', f"gvg_user.set_access_token token_len={(len(token) if token else 0)}")
    except Exception:
        pass


def get_current_user() -> Dict[str, str]:
    """Retorna usuário atual.
    - Se houver token válido via Supabase, usa-o;
    - Senão, retorna usuário anônimo (compatibilidade temporária).
    """
    global _CURRENT_USER
    token = _ACCESS_TOKEN or os.getenv('GVG_ACCESS_TOKEN')
    if token and get_user_from_token:
        info = None
        try:
            info = get_user_from_token(token)
        except Exception:
            info = None
        if info and info.get('uid'):
            # Atualiza o usuário corrente em memória
            _CURRENT_USER = {
                'uid': info['uid'],
                'email': info.get('email') or '',
                'name': info.get('name') or (info.get('email') or 'Usuário'),
            }
            return dict(_CURRENT_USER)
    try:
        dbg('AUTH', f"gvg_user.get_current_user uid={_CURRENT_USER.get('uid')} email={_CURRENT_USER.get('email')}")
    except Exception:
        pass
    return dict(_CURRENT_USER)

def set_current_user(user_or_uid: Union[Dict[str, str], str], email: Optional[str] = None, name: Optional[str] = None):
    """Define o usuário atual.
    Aceita um dicionário {'uid','email','name'} ou os três campos separados.
    """
    global _CURRENT_USER
    if isinstance(user_or_uid, dict):
        u = user_or_uid
        _CURRENT_USER = {
            'uid': str(u.get('uid') or u.get('id') or ''),
            'email': str(u.get('email') or ''),
            'name': str(u.get('name') or u.get('full_name') or u.get('email') or 'Usuário'),
        }
    else:
        _CURRENT_USER = {
            'uid': str(user_or_uid or ''),
            'email': str(email or ''),
            'name': str(name or 'Usuário'),
        }
    try:
        dbg('AUTH', f"gvg_user.set_current_user uid={_CURRENT_USER.get('uid')} email={_CURRENT_USER.get('email')}")
    except Exception:
        pass


def get_user_initials(name: Optional[str]) -> str:
    if not name:
        return 'NA'
    parts = [p.strip() for p in str(name).split() if p.strip()]
    if not parts:
        return 'NA'
    if len(parts) == 1:
        return parts[0][:2].upper()
    return (parts[0][0] + parts[-1][0]).upper()


# ==========================
# Histórico de prompts
# ==========================
def fetch_prompt_texts(limit: int = 50) -> List[str]:
    """Retorna textos dos prompts (mais recentes) já filtrando active = true (coluna garantida)."""
    user = get_current_user()
    uid = user['uid']
    try:
        # cache por usuário
        ck = f"USER.fetch_prompt_texts:{uid}:{limit}"
        cached = _cache_get(ck)
        if cached is not None:
            return list(cached)
        rows = db_fetch_all(
            (
                """SELECT text
                       FROM public.user_prompts
                      WHERE user_id = %s
                        AND text IS NOT NULL
                        AND active = true
                   ORDER BY created_at DESC
                      LIMIT %s"""
            ),
            (uid, limit),
            ctx="USER.fetch_prompt_texts",
        ) or []
        out = [r[0] for r in rows if r and r[0] is not None]
        _cache_set(ck, out)
        return out
    except Exception:
        return []


def add_prompt(
    text: str,
    title: Optional[str] = None,
    *,
    search_type: Optional[int] = None,
    search_approach: Optional[int] = None,
    relevance_level: Optional[int] = None,
    sort_mode: Optional[int] = None,
    max_results: Optional[int] = None,
    top_categories_count: Optional[int] = None,
    filter_expired: Optional[bool] = None,
    embedding: Optional[List[float]] = None,
    filters: Optional[Dict[str, Any]] = None,
) -> Optional[int]:
    """Adiciona um prompt ao histórico do usuário, com configuração (e embedding, se disponível).

    - Dedup por (user_id, text)
    - Retorna o id do prompt inserido (prompt_id) em caso de sucesso; None em erro.
    """
    if not text:
        return None
    user = get_current_user(); uid = user['uid']
    try:
        # Dedup por texto do mesmo usuário: obter ids
        ids_rows = db_fetch_all(
            "SELECT id FROM public.user_prompts WHERE user_id = %s AND text = %s",
            (uid, text), ctx="USER.add_prompt:find_duplicates"
        ) or []
        old_ids = [r[0] for r in ids_rows if r and r[0] is not None]
        if old_ids:
            placeholders = ','.join(['%s'] * len(old_ids))
            db_execute(
                f"DELETE FROM public.user_results WHERE user_id = %s AND prompt_id IN ({placeholders})",
                (uid, *old_ids), ctx="USER.add_prompt:delete_old_results"
            )
        db_execute(
            "DELETE FROM public.user_prompts WHERE user_id = %s AND text = %s",
            (uid, text), ctx="USER.add_prompt:delete_old_prompts"
        )

        # Descobrir colunas existentes e tipos
        col_types = _schema_types_cached('user_prompts')
        cols_existing = set(col_types.keys())

        # Colunas e valores base
        insert_cols = ['user_id', 'title', 'text']
        insert_vals: List[Any] = [uid, title or (text[:60] if text else None), text]
        placeholders: List[str] = ['%s', '%s', '%s']

        # Campos opcionais
        optional_map = [
            ('search_type', search_type),
            ('search_approach', search_approach),
            ('relevance_level', relevance_level),
            ('sort_mode', sort_mode),
            ('max_results', max_results),
            ('top_categories_count', top_categories_count),
            ('filter_expired', filter_expired),
            ('embedding', embedding),
            ('filters', filters),
        ]
        for col, val in optional_map:
            if col in cols_existing:
                insert_cols.append(col)
                if col == 'embedding' and col_types.get('embedding') == 'vector':
                    placeholders.append('%s::vector')
                    insert_vals.append(val)
                elif col == 'filters' and col_types.get('filters') in ('jsonb', 'json'):
                    placeholders.append('%s::jsonb')
                    insert_vals.append(json.dumps(val) if val is not None else None)
                else:
                    placeholders.append('%s')
                    insert_vals.append(val)

        try:
            dbg('SQL', '[gvg_user.add_prompt] cols_existing = ' + str(sorted(list(cols_existing))))
            dbg('SQL', '[gvg_user.add_prompt] insert_cols = ' + str(insert_cols))
            dbg('SQL', '[gvg_user.add_prompt] insert_vals types = ' + str([type(v).__name__ for v in insert_vals]))
        except Exception:
            pass

        sql = f"INSERT INTO public.user_prompts ({', '.join(insert_cols)}) VALUES ({', '.join(placeholders)}) RETURNING id"
        row = db_execute_returning_one(sql, tuple(insert_vals), as_dict=False, ctx="USER.add_prompt:insert")
        prompt_id = row[0] if isinstance(row, (list, tuple)) else (row.get('id') if isinstance(row, dict) else None)
        pid = int(prompt_id) if prompt_id is not None else None
        # invalida caches de prompts do usuário
        _cache_invalidate_prefix(f"USER.fetch_prompt_texts:{uid}:")
        _cache_invalidate_prefix(f"USER.fetch_prompts_with_config:{uid}:")
        return pid
    except Exception:
        return None


def fetch_prompts_with_config(limit: int = 50) -> List[Dict[str, Any]]:
    """Retorna prompts (texto, título, criado_em) com as configurações salvas."""
    user = get_current_user()
    uid = user['uid']
    try:
        # cache de schema
        cols_existing = set(_schema_columns_cached('user_prompts'))

        base_cols = ['text', 'title', 'created_at']
        opt_cols = [
            'search_type', 'search_approach', 'relevance_level', 'sort_mode',
            'max_results', 'top_categories_count', 'filter_expired', 'filters'
        ]
        select_cols = base_cols + [c for c in opt_cols if c in cols_existing]
        # Checa se coluna active existe para filtrar somente ativos
        has_active = 'active' in cols_existing
        where_clause = "WHERE user_id = %s AND text IS NOT NULL"
        if has_active:
            where_clause += " AND active = true"
        select_sql = f"SELECT {', '.join(select_cols)} FROM public.user_prompts {where_clause} ORDER BY created_at DESC LIMIT %s"
        # cache por usuário
        ck = f"USER.fetch_prompts_with_config:{uid}:{limit}:{','.join(select_cols)}"
        cached = _cache_get(ck)
        if cached is not None:
            return list(cached)
        rows = db_fetch_all(select_sql, (uid, limit), ctx="USER.fetch_prompts_with_config:select") or []
        out: List[Dict[str, Any]] = []
        for row in rows:
            item: Dict[str, Any] = {}
            # rows vem como tuplas; mapear por índice
            for idx, c in enumerate(select_cols):
                try:
                    item[c] = row[idx]
                except Exception:
                    item[c] = None
            out.append(item)
        _cache_set(ck, out)
        return out
    except Exception:
        return []


def delete_prompt(text: str) -> bool:
    """Remove um prompt específico (pelo texto) do histórico do usuário atual."""
    if not text:
        return False
    user = get_current_user(); uid = user['uid']
    try:
        # Detecta coluna active
        has_active = 'active' in _schema_columns_cached('user_prompts')
        if has_active:
            aff = db_execute(
                "UPDATE public.user_prompts SET active=false WHERE user_id=%s AND text=%s",
                (uid, text), ctx="USER.delete_prompt:soft_delete"
            )
            return bool(aff and aff >= 0)
        # Hard delete + limpar filhos
        ids_rows = db_fetch_all(
            "SELECT id FROM public.user_prompts WHERE user_id = %s AND text = %s",
            (uid, text), ctx="USER.delete_prompt:find_ids"
        ) or []
        prompt_ids = [r[0] for r in ids_rows if r and r[0] is not None]
        if prompt_ids:
            placeholders = ','.join(['%s'] * len(prompt_ids))
            db_execute(
                f"DELETE FROM public.user_results WHERE user_id = %s AND prompt_id IN ({placeholders})",
                (uid, *prompt_ids), ctx="USER.delete_prompt:delete_children"
            )
        db_execute(
            "DELETE FROM public.user_prompts WHERE user_id = %s AND text = %s",
            (uid, text), ctx="USER.delete_prompt:delete_prompt"
        )
        # invalidar caches relacionados
        _cache_invalidate_prefix(f"USER.fetch_prompt_texts:{uid}:")
        _cache_invalidate_prefix(f"USER.fetch_prompts_with_config:{uid}:")
        return True
    except Exception:
        return False


def save_user_results(prompt_id: int, results: List[Dict[str, Any]]) -> bool:
    """Grava os resultados retornados para um prompt na tabela public.user_results.

    Campos: user_id, prompt_id, numero_controle_pncp, rank, similarity, valor, data_encerramento_proposta
    """
    if not prompt_id or not results:
        return False
    user = get_current_user(); uid = user['uid']
    try:
        rows_to_insert = []
        for r in results:
            numero = r.get('numero_controle') or r.get('id')
            rank = r.get('rank')
            similarity = r.get('similarity')
            details = r.get('details') or {}
            raw_val = details.get('valorfinal') or details.get('valorFinal') or details.get('valortotalestimado') or details.get('valorTotalEstimado')
            valor = None
            if raw_val is not None:
                try:
                    if isinstance(raw_val, str):
                        rv = raw_val.strip().replace('.', '').replace(',', '.') if raw_val.count(',')==1 and raw_val.count('.')>1 else raw_val
                        valor = float(rv)
                    else:
                        valor = float(raw_val)
                except Exception:
                    valor = None
            data_enc = details.get('dataencerramentoproposta') or details.get('dataEncerramentoProposta') or details.get('dataEncerramento')
            if not numero or rank is None:
                continue
            rows_to_insert.append((uid, prompt_id, str(numero), int(rank), float(similarity) if similarity is not None else None, valor, data_enc))
        if not rows_to_insert:
            return False
        insert_sql = (
            "INSERT INTO public.user_results "
            "(user_id, prompt_id, numero_controle_pncp, rank, similarity, valor, data_encerramento_proposta) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s)"
        )
        aff = db_execute_many(insert_sql, rows_to_insert, ctx="USER.save_user_results")
        return bool(aff and aff >= 0)
    except Exception:
        return False


def fetch_user_results_for_prompt_text(text: str, limit: int = 500) -> List[Dict[str, Any]]:
    """Carrega resultados salvos (public.user_results) para o prompt com o texto fornecido.

    Junta com user_prompts (para obter o prompt_id mais recente/ativo) e contratacao (para detalhes).
    Retorna no formato esperado pela UI: [{'id','numero_controle','rank','similarity','details':{...}}]
    """
    if not text:
        return []
    user = get_current_user(); uid = user.get('uid')
    if not uid:
        return []
    try:
        # Detecta coluna active em user_prompts (cache de schema)
        has_active = 'active' in _schema_columns_cached('user_prompts')
        core_cols = get_contratacao_core_columns('c')
        core_expr = ",\n  ".join(core_cols)
        where_up = ["up.user_id = %s", "up.text = %s"]
        params: List[Any] = [uid, text]
        if has_active:
            where_up.append("up.active = true")
        sql = (
            "SELECT "
            "  ur.numero_controle_pncp, ur.rank, ur.similarity, ur.valor, ur.data_encerramento_proposta,\n  "
            + core_expr +
            f"\nFROM public.user_prompts up\n"
            f"JOIN public.user_results ur ON ur.prompt_id = up.id AND ur.user_id = up.user_id\n"
            f"JOIN public.contratacao c ON c.{PRIMARY_KEY} = ur.numero_controle_pncp\n"
            "WHERE " + " AND ".join(where_up) + "\n"
            "ORDER BY ur.rank ASC\n"
            "LIMIT %s"
        )
        params.append(limit)
        rows = db_fetch_all(sql, tuple(params), as_dict=True, ctx="USER.fetch_user_results_for_prompt_text:select") or []
        allowed = { (f.split('.')[-1] if '.' in f else f) for f in core_cols }
        out: List[Dict[str, Any]] = []
        for rec in rows:
            pid = rec.get('numero_controle_pncp')
            rank = rec.get('rank')
            sim = rec.get('similarity')
            details = {k: rec.get(k) for k in rec.keys() if k in allowed}
            _augment_aliases(details)
            out.append({
                'id': pid,
                'numero_controle': pid,
                'rank': int(rank) if rank is not None else None,
                'similarity': float(sim) if sim is not None else None,
                'details': details
            })
        return out
    except Exception:
        return []


# ==========================
# Favoritos (Bookmarks)
# ==========================
def fetch_bookmarks(limit: int = 100) -> List[Dict[str, Any]]:
    """Lista favoritos do usuário atual, incluindo rótulo se a coluna existir.

    Retorna itens contendo:
      numero_controle_pncp, objeto_compra, orgao_entidade_razao_social,
      unidade_orgao_municipio_nome, unidade_orgao_uf_sigla,
      data_encerramento_proposta, rotulo (opcional)
    """
    user = get_current_user(); uid = user['uid']
    try:
        # schema (uma chamada)
        bm_cols = set(_schema_columns_cached('user_bookmarks'))
        if not bm_cols:
            return []
        has_rotulo = 'rotulo' in bm_cols
        has_active = 'active' in bm_cols
        select_fields = [
            'ub.id',
            'ub.numero_controle_pncp',
            'c.objeto_compra',
            'c.orgao_entidade_razao_social',
            'c.unidade_orgao_municipio_nome',
            'c.unidade_orgao_uf_sigla',
            'c.data_encerramento_proposta'
        ]
        if has_rotulo:
            select_fields.append('ub.rotulo')
        where_parts = ["ub.user_id = %s", "c.numero_controle_pncp = ub.numero_controle_pncp"]
        if has_active:
            where_parts.append("ub.active = true")
        sql = (
            "SELECT " + ', '.join(select_fields) +
            " FROM public.user_bookmarks ub, public.contratacao c WHERE " + ' AND '.join(where_parts) +
            " ORDER BY ub.created_at DESC NULLS LAST, ub.id DESC LIMIT %s"
        )
        ck = f"USER.fetch_bookmarks:{uid}:{limit}:{','.join(select_fields)}"
        cached = _cache_get(ck)
        if cached is not None:
            return list(cached)
        rows_db = db_fetch_all(sql, (uid, limit), ctx="USER.fetch_bookmarks:select") or []
        out: List[Dict[str, Any]] = []
        for row in rows_db:
            pncp = row[1]
            item = {
                'numero_controle_pncp': pncp,
                'objeto_compra': row[2],
                'orgao_entidade_razao_social': row[3],
                'unidade_orgao_municipio_nome': row[4],
                'unidade_orgao_uf_sigla': row[5],
                'data_encerramento_proposta': row[6],
            }
            if has_rotulo:
                item['rotulo'] = row[7]
            out.append(item)
        _cache_set(ck, out)
        return out
    except Exception:
        return []


def add_bookmark(numero_controle_pncp: str, rotulo: Optional[str] = None) -> bool:
    """Adiciona um favorito (ignora duplicatas), com rótulo opcional.

    Se a coluna rotulo não existir, ignora o parâmetro rotulo.
    """
    if not numero_controle_pncp:
        return False
    user = get_current_user(); uid = user['uid']
    try:
        bm_cols = set(_schema_columns_cached('user_bookmarks'))
        if not bm_cols:
            return False
        has_rotulo = 'rotulo' in bm_cols
        has_active = 'active' in bm_cols
        if has_active:
            if has_rotulo:
                aff = db_execute(
                    "UPDATE public.user_bookmarks SET active=true, rotulo=COALESCE(%s, rotulo) WHERE user_id=%s AND numero_controle_pncp=%s",
                    (rotulo, uid, numero_controle_pncp), ctx="USER.add_bookmark:reactivate_with_rotulo"
                )
            else:
                aff = db_execute(
                    "UPDATE public.user_bookmarks SET active=true WHERE user_id=%s AND numero_controle_pncp=%s",
                    (uid, numero_controle_pncp), ctx="USER.add_bookmark:reactivate"
                )
            if not aff:
                if has_rotulo:
                    db_execute(
                        "INSERT INTO public.user_bookmarks (user_id, numero_controle_pncp, rotulo) VALUES (%s, %s, %s)",
                        (uid, numero_controle_pncp, rotulo), ctx="USER.add_bookmark:insert_with_rotulo"
                    )
                else:
                    db_execute(
                        "INSERT INTO public.user_bookmarks (user_id, numero_controle_pncp) VALUES (%s, %s)",
                        (uid, numero_controle_pncp), ctx="USER.add_bookmark:insert"
                    )
        else:
            db_execute(
                "DELETE FROM public.user_bookmarks WHERE user_id = %s AND numero_controle_pncp = %s",
                (uid, numero_controle_pncp), ctx="USER.add_bookmark:legacy_delete"
            )
            if has_rotulo:
                db_execute(
                    "INSERT INTO public.user_bookmarks (user_id, numero_controle_pncp, rotulo) VALUES (%s, %s, %s)",
                    (uid, numero_controle_pncp, rotulo), ctx="USER.add_bookmark:legacy_insert_with_rotulo"
                )
            else:
                db_execute(
                    "INSERT INTO public.user_bookmarks (user_id, numero_controle_pncp) VALUES (%s, %s)",
                    (uid, numero_controle_pncp), ctx="USER.add_bookmark:legacy_insert"
                )
        # invalida cache de favoritos
        _cache_invalidate_prefix(f"USER.fetch_bookmarks:{uid}:")
        return True
    except Exception:
        return False


def remove_bookmark(numero_controle_pncp: str) -> bool:
    """Remove um favorito."""
    if not numero_controle_pncp:
        return False
    user = get_current_user(); uid = user['uid']
    try:
        has_active = 'active' in _schema_columns_cached('user_bookmarks')
        if has_active:
            db_execute(
                "UPDATE public.user_bookmarks SET active=false WHERE user_id=%s AND numero_controle_pncp=%s",
                (uid, numero_controle_pncp), ctx="USER.remove_bookmark:soft_delete"
            )
        else:
            db_execute(
                "DELETE FROM public.user_bookmarks WHERE user_id = %s AND numero_controle_pncp = %s",
                (uid, numero_controle_pncp), ctx="USER.remove_bookmark:hard_delete"
            )
        _cache_invalidate_prefix(f"USER.fetch_bookmarks:{uid}:")
        return True
    except Exception:
        return False
