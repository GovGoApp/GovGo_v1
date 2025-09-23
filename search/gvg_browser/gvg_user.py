"""
gvg_user.py
Funções auxiliares de usuário e histórico de prompts por usuário.

Agora usa usuário dinâmico quando há token/sessão; fallback anônimo apenas para compatibilidade.
"""
from __future__ import annotations

import os
from typing import List, Optional, Dict, Any, Union
import datetime as _dt
try:
    from search.gvg_browser.gvg_database import create_connection  # type: ignore
    from search.gvg_browser.gvg_debug import debug_log as dbg  # type: ignore
    from search.gvg_browser.gvg_schema import get_contratacao_core_columns, PRIMARY_KEY  # type: ignore
    from search.gvg_browser.gvg_search_core import _augment_aliases  # type: ignore
except Exception:
    try:
        from .gvg_database import create_connection  # type: ignore
        from .gvg_debug import debug_log as dbg  # type: ignore
        from .gvg_schema import get_contratacao_core_columns, PRIMARY_KEY  # type: ignore
        from .gvg_search_core import _augment_aliases  # type: ignore
    except Exception:
        from gvg_database import create_connection  # type: ignore
        from gvg_debug import debug_log as dbg  # type: ignore
        from gvg_schema import get_contratacao_core_columns, PRIMARY_KEY  # type: ignore
        from gvg_search_core import _augment_aliases  # type: ignore

# Tenta importar auth para obter usuário da sessão (token em cookies)
try:
    from gvg_auth import get_user_from_token  # type: ignore
except Exception:
    get_user_from_token = None  # type: ignore

# Usuário atual em memória (anônimo por padrão; será preenchido ao logar)
_CURRENT_USER = {
    'uid': '',
    'email': '',
    'name': 'Usuário',
}

# Permite injetar token (por camada Flask) em tempo de execução
_ACCESS_TOKEN: Optional[str] = None


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
    conn = None
    cur = None
    try:
        conn = create_connection()
        if not conn:
            return []
        cur = conn.cursor()
        cur.execute(
            """SELECT text
                   FROM public.user_prompts
                  WHERE user_id = %s
                    AND text IS NOT NULL
                    AND active = true
               ORDER BY created_at DESC
                  LIMIT %s""",
            (uid, limit)
        )
        rows = cur.fetchall() or []
        return [r[0] for r in rows if r and r[0]]
    except Exception:
        return []
    finally:
        try:
            if cur:
                cur.close()
        finally:
            if conn:
                conn.close()


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
) -> Optional[int]:
    """Adiciona um prompt ao histórico do usuário, com configuração (e embedding, se disponível).

    - Dedup por (user_id, text)
    - Retorna o id do prompt inserido (prompt_id) em caso de sucesso; None em erro.
    """
    if not text:
        return None
    user = get_current_user(); uid = user['uid']
    conn = None; cur = None
    try:
        conn = create_connection()
        if not conn:
            return None
        cur = conn.cursor()
        # Dedup por texto do mesmo usuário
        # Para garantir remoção consistente dos resultados associados, apagamos primeiro os filhos (user_results)
        try:
            cur.execute(
                "SELECT id FROM public.user_prompts WHERE user_id = %s AND text = %s",
                (uid, text)
            )
            ids_rows = cur.fetchall() or []
            old_ids = [r[0] for r in ids_rows if r and r[0] is not None]
            if old_ids:
                # Apaga resultados vinculados a estes prompts
                placeholders = ','.join(['%s'] * len(old_ids))
                cur.execute(
                    f"DELETE FROM public.user_results WHERE user_id = %s AND prompt_id IN ({placeholders})",
                    (uid, *old_ids)
                )
        except Exception:
            # Em caso de falha nesta limpeza preventiva, prossegue; ON DELETE CASCADE pode resolver
            pass
        # Agora apaga os prompts duplicados por texto
        cur.execute("DELETE FROM public.user_prompts WHERE user_id = %s AND text = %s", (uid, text))

        # Descobrir colunas existentes e tipos
        cur.execute(
            """
            SELECT column_name, udt_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'user_prompts'
            """
        )
        rows_cols = cur.fetchall() or []
        cols_existing = {r[0] for r in rows_cols}
        col_types = {r[0]: r[1] for r in rows_cols}

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
        ]
        for col, val in optional_map:
            if col in cols_existing:
                insert_cols.append(col)
                insert_vals.append(val)
                # Vetor precisa de cast explícito
                if col == 'embedding' and col_types.get('embedding') == 'vector':
                    placeholders.append('%s::vector')
                else:
                    placeholders.append('%s')

        # Debug opcional (auto-gated pelo dbg)
        try:
            dbg('SQL', '[gvg_user.add_prompt] cols_existing = ' + str(sorted(list(cols_existing))))
            dbg('SQL', '[gvg_user.add_prompt] insert_cols = ' + str(insert_cols))
            dbg('SQL', '[gvg_user.add_prompt] insert_vals types = ' + str([type(v).__name__ for v in insert_vals]))
        except Exception:
            pass

        sql = f"INSERT INTO public.user_prompts ({', '.join(insert_cols)}) VALUES ({', '.join(placeholders)}) RETURNING id"
        cur.execute(sql, insert_vals)
        row = cur.fetchone()
        prompt_id = row[0] if row else None
        conn.commit()
        return int(prompt_id) if prompt_id is not None else None
    except Exception:
        try:
            if conn: conn.rollback()
        except Exception:
            pass
        return None
    finally:
        try:
            if cur: cur.close()
        finally:
            if conn: conn.close()


def fetch_prompts_with_config(limit: int = 50) -> List[Dict[str, Any]]:
    """Retorna prompts (texto, título, criado_em) com as configurações salvas."""
    user = get_current_user()
    uid = user['uid']
    conn = None; cur = None
    try:
        conn = create_connection()
        if not conn:
            return []
        cur = conn.cursor()
        # Ver quais colunas existem para montar SELECT dinamicamente
        cur.execute(
            """
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = 'public' AND table_name = 'user_prompts'
            """
        )
        cols_existing = {r[0] for r in (cur.fetchall() or [])}

        base_cols = ['text', 'title', 'created_at']
        opt_cols = [
            'search_type', 'search_approach', 'relevance_level', 'sort_mode',
            'max_results', 'top_categories_count', 'filter_expired'
        ]
        select_cols = base_cols + [c for c in opt_cols if c in cols_existing]
        # Checa se coluna active existe para filtrar somente ativos
        has_active = 'active' in cols_existing
        where_clause = "WHERE user_id = %s AND text IS NOT NULL"
        if has_active:
            where_clause += " AND active = true"
        select_sql = f"SELECT {', '.join(select_cols)} FROM public.user_prompts {where_clause} ORDER BY created_at DESC LIMIT %s"
        cur.execute(select_sql, (uid, limit))

        out: List[Dict[str, Any]] = []
        for row in cur.fetchall() or []:
            item: Dict[str, Any] = {}
            for idx, c in enumerate(select_cols):
                item[c] = row[idx]
            out.append(item)
        return out
    except Exception:
        return []
    finally:
        try:
            if cur: cur.close()
        finally:
            if conn: conn.close()


def delete_prompt(text: str) -> bool:
    """Remove um prompt específico (pelo texto) do histórico do usuário atual."""
    if not text:
        return False
    user = get_current_user(); uid = user['uid']
    conn = None; cur = None
    try:
        conn = create_connection()
        if not conn:
            return False
        cur = conn.cursor()
        # Detecta se existe coluna active para aplicar soft delete
        try:
            cur.execute(
                """
                SELECT 1 FROM information_schema.columns
                WHERE table_schema='public' AND table_name='user_prompts' AND column_name='active'
                """
            )
            has_active = bool(cur.fetchone())
        except Exception:
            has_active = False
        if has_active:
            cur.execute(
                "UPDATE public.user_prompts SET active=false WHERE user_id=%s AND text=%s",
                (uid, text)
            )
        else:
            # Comportamento antigo (hard delete + limpeza de resultados)
            cur.execute(
                "SELECT id FROM public.user_prompts WHERE user_id = %s AND text = %s",
                (uid, text)
            )
            ids_rows = cur.fetchall() or []
            prompt_ids = [r[0] for r in ids_rows if r and r[0] is not None]
            if prompt_ids:
                placeholders = ','.join(['%s'] * len(prompt_ids))
                cur.execute(
                    f"DELETE FROM public.user_results WHERE user_id = %s AND prompt_id IN ({placeholders})",
                    (uid, *prompt_ids)
                )
            cur.execute("DELETE FROM public.user_prompts WHERE user_id = %s AND text = %s", (uid, text))
        conn.commit()
        return True
    except Exception:
        try:
            if conn: conn.rollback()
        except Exception:
            pass
        return False
    finally:
        try:
            if cur: cur.close()
        finally:
            if conn: conn.close()


def save_user_results(prompt_id: int, results: List[Dict[str, Any]]) -> bool:
    """Grava os resultados retornados para um prompt na tabela public.user_results.

    Campos: user_id, prompt_id, numero_controle_pncp, rank, similarity, valor, data_encerramento_proposta
    """
    if not prompt_id or not results:
        return False
    user = get_current_user(); uid = user['uid']
    conn = None; cur = None
    try:
        conn = create_connection()
        if not conn:
            return False
        cur = conn.cursor()
        # Monta linhas a inserir
        rows = []
        for r in results:
            numero = r.get('numero_controle') or r.get('id')
            rank = r.get('rank')
            similarity = r.get('similarity')
            details = r.get('details') or {}
            # valor: tenta final, senão estimado (converte para float quando possível)
            raw_val = details.get('valorfinal') or details.get('valorFinal') or details.get('valortotalestimado') or details.get('valorTotalEstimado')
            valor = None
            if raw_val is not None:
                try:
                    # aceita strings com vírgula como decimal
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
            rows.append((uid, prompt_id, str(numero), int(rank), float(similarity) if similarity is not None else None, valor, data_enc))
        if not rows:
            return False
        # Inserção em lote
        insert_sql = """
            INSERT INTO public.user_results
                (user_id, prompt_id, numero_controle_pncp, rank, similarity, valor, data_encerramento_proposta)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        for tup in rows:
            cur.execute(insert_sql, tup)
        conn.commit()
        return True
    except Exception:
        try:
            if conn: conn.rollback()
        except Exception:
            pass
        return False
    finally:
        try:
            if cur: cur.close()
        finally:
            if conn: conn.close()


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
    conn = None; cur = None
    try:
        conn = create_connection()
        if not conn:
            return []
        cur = conn.cursor()
        # Detecta coluna active em user_prompts
        try:
            cur.execute(
                """
                SELECT 1 FROM information_schema.columns
                WHERE table_schema='public' AND table_name='user_prompts' AND column_name='active'
                """
            )
            has_active = bool(cur.fetchone())
        except Exception:
            has_active = False
        core_cols = get_contratacao_core_columns('c')
        core_expr = ",\n  ".join(core_cols)
        where_up = ["up.user_id = %s", "up.text = %s"]
        params: List[Any] = [uid, text]
        if has_active:
            where_up.append("up.active = true")
        # Junta prompts (mais recente), results e contratacao
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
        cur.execute(sql, params)
        rows = cur.fetchall() or []
        colnames = [d[0] for d in cur.description]
        out: List[Dict[str, Any]] = []
        for row in rows:
            rec = dict(zip(colnames, row))
            pid = rec.get('numero_controle_pncp')
            rank = rec.get('rank')
            sim = rec.get('similarity')
            # Extrai apenas as colunas core para details
            details = {k: rec.get(k) for k in colnames if k in [f.split('.')[-1] if '.' in f else f for f in core_cols]}
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
        try:
            if conn: conn.rollback()
        except Exception:
            pass
        return []
    finally:
        try:
            if cur: cur.close()
        finally:
            if conn: conn.close()


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
    conn = None; cur = None
    try:
        conn = create_connection()
        if not conn:
            return []
        cur = conn.cursor()
        # Verificar existência da tabela
        try:
            cur.execute(
                """
                SELECT 1 FROM information_schema.tables
                WHERE table_schema='public' AND table_name='user_bookmarks'
                """
            )
            if not cur.fetchone():
                return []
        except Exception:
            return []
        # Detecta se coluna rotulo existe
        has_rotulo = False
        try:
            cur.execute(
                """
                SELECT 1 FROM information_schema.columns
                WHERE table_schema='public' AND table_name='user_bookmarks' AND column_name='rotulo'
                """
            )
            has_rotulo = bool(cur.fetchone())
        except Exception:
            has_rotulo = False
        # Checar colunas existentes em user_bookmarks para saber se active existe
        try:
            cur.execute(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_schema='public' AND table_name='user_bookmarks'
                """
            )
            bm_cols = {r[0] for r in (cur.fetchall() or [])}
        except Exception:
            bm_cols = set()
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
        cur.execute(sql, (uid, limit))
        rows_db = cur.fetchall() or []
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
        return out
    except Exception:
        return []
    finally:
        try:
            if cur:
                cur.close()
        finally:
            if conn:
                conn.close()


def add_bookmark(numero_controle_pncp: str, rotulo: Optional[str] = None) -> bool:
    """Adiciona um favorito (ignora duplicatas), com rótulo opcional.

    Se a coluna rotulo não existir, ignora o parâmetro rotulo.
    """
    if not numero_controle_pncp:
        return False
    user = get_current_user(); uid = user['uid']
    conn = None; cur = None
    try:
        conn = create_connection()
        if not conn:
            return False
        cur = conn.cursor()
        # Garante tabela existente
        try:
            cur.execute("""
                SELECT 1 FROM information_schema.tables
                WHERE table_schema='public' AND table_name='user_bookmarks'
            """)
            if not cur.fetchone():
                return False
        except Exception:
            return False
        # Checa se coluna rotulo existe
        has_rotulo = False
        try:
            cur.execute(
                """
                SELECT 1 FROM information_schema.columns
                WHERE table_schema='public' AND table_name='user_bookmarks' AND column_name='rotulo'
                """
            )
            has_rotulo = bool(cur.fetchone())
        except Exception:
            has_rotulo = False
        # Detecta coluna active
        has_active = False
        try:
            cur.execute(
                """
                SELECT 1 FROM information_schema.columns
                WHERE table_schema='public' AND table_name='user_bookmarks' AND column_name='active'
                """
            )
            has_active = bool(cur.fetchone())
        except Exception:
            has_active = False
        # Se active existe: tentar reativar em vez de remover/inserir
        if has_active:
            if has_rotulo:
                cur.execute(
                    "UPDATE public.user_bookmarks SET active=true, rotulo=COALESCE(%s, rotulo) WHERE user_id=%s AND numero_controle_pncp=%s",
                    (rotulo, uid, numero_controle_pncp)
                )
            else:
                cur.execute(
                    "UPDATE public.user_bookmarks SET active=true WHERE user_id=%s AND numero_controle_pncp=%s",
                    (uid, numero_controle_pncp)
                )
            if cur.rowcount == 0:
                if has_rotulo:
                    cur.execute(
                        "INSERT INTO public.user_bookmarks (user_id, numero_controle_pncp, rotulo) VALUES (%s, %s, %s)",
                        (uid, numero_controle_pncp, rotulo)
                    )
                else:
                    cur.execute(
                        "INSERT INTO public.user_bookmarks (user_id, numero_controle_pncp) VALUES (%s, %s)",
                        (uid, numero_controle_pncp)
                    )
        else:
            # fallback comportamento antigo (sem coluna active)
            cur.execute(
                "DELETE FROM public.user_bookmarks WHERE user_id = %s AND numero_controle_pncp = %s",
                (uid, numero_controle_pncp)
            )
            if has_rotulo:
                cur.execute(
                    "INSERT INTO public.user_bookmarks (user_id, numero_controle_pncp, rotulo) VALUES (%s, %s, %s)",
                    (uid, numero_controle_pncp, rotulo)
                )
            else:
                cur.execute(
                    "INSERT INTO public.user_bookmarks (user_id, numero_controle_pncp) VALUES (%s, %s)",
                    (uid, numero_controle_pncp)
                )
        conn.commit()
        return True
    except Exception:
        try:
            if conn: conn.rollback()
        except Exception:
            pass
        return False
    finally:
        try:
            if cur: cur.close()
        finally:
            if conn: conn.close()


def remove_bookmark(numero_controle_pncp: str) -> bool:
    """Remove um favorito."""
    if not numero_controle_pncp:
        return False
    user = get_current_user(); uid = user['uid']
    conn = None; cur = None
    try:
        conn = create_connection()
        if not conn:
            return False
        cur = conn.cursor()
        # Soft delete se coluna active existir
        has_active = False
        try:
            cur.execute(
                """
                SELECT 1 FROM information_schema.columns
                WHERE table_schema='public' AND table_name='user_bookmarks' AND column_name='active'
                """
            )
            has_active = bool(cur.fetchone())
        except Exception:
            has_active = False
        if has_active:
            cur.execute(
                "UPDATE public.user_bookmarks SET active=false WHERE user_id=%s AND numero_controle_pncp=%s",
                (uid, numero_controle_pncp)
            )
        else:
            cur.execute(
                "DELETE FROM public.user_bookmarks WHERE user_id = %s AND numero_controle_pncp = %s",
                (uid, numero_controle_pncp)
            )
        conn.commit()
        return True
    except Exception:
        try:
            if conn: conn.rollback()
        except Exception:
            pass
        return False
    finally:
        try:
            if cur: cur.close()
        finally:
            if conn: conn.close()
