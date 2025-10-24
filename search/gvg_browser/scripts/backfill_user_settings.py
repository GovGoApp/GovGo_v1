r"""
Backfill de user_settings: insere linha para usuários que ainda não possuem,
atribuindo plano FREE (id obtido por lookup) e plan_status='active'.

Uso (Windows PowerShell):
    python .\backfill_user_settings.py

Requer que o módulo gvg_database esteja configurado (variáveis .env, etc.)
"""
from __future__ import annotations

import os
import sys
from typing import List, Tuple

# Garantir que o diretório pai (search/gvg_browser) esteja no sys.path
CUR_DIR = os.path.dirname(__file__)
APP_DIR = os.path.abspath(os.path.join(CUR_DIR, '..'))
if APP_DIR not in sys.path:
        sys.path.insert(0, APP_DIR)

from gvg_database import db_fetch_all, db_fetch_one, db_execute  # type: ignore


def _get_free_plan_id_default() -> int:
    row = db_fetch_one("SELECT id FROM public.system_plans WHERE UPPER(code)='FREE' LIMIT 1", ctx="BFREE.free_plan")
    if not row:
        return 1
    return row[0] if not isinstance(row, dict) else int(row.get('id', 1))


def _get_missing_users() -> List[str]:
    sql = (
        "SELECT u.id::text AS uid "
        "FROM auth.users u "
        "LEFT JOIN public.user_settings s ON s.user_id = u.id "
        "WHERE s.user_id IS NULL"
    )
    rows = db_fetch_all(sql, ctx="BACKFILL.missing_users")
    out: List[str] = []
    for r in rows:
        if isinstance(r, dict):
            uid = r.get('uid')
        else:
            uid = r[0]
        if uid:
            out.append(str(uid))
    return out


def backfill_user_settings() -> Tuple[int, int]:
    free_id = _get_free_plan_id_default()
    users = _get_missing_users()
    inserted = 0
    skipped = 0
    for uid in users:
        try:
            affected = db_execute(
                "INSERT INTO public.user_settings (user_id, plan_id, plan_status, plan_started_at) "
                "VALUES (%s, %s, 'active', now()) ON CONFLICT (user_id) DO NOTHING",
                (uid, free_id),
                ctx="BACKFILL.insert"
            )
            if affected and affected > 0:
                inserted += 1
            else:
                skipped += 1
        except Exception:
            # Não interromper todo o processo por uma falha isolada
            skipped += 1
    return inserted, skipped


if __name__ == "__main__":
    ins, skp = backfill_user_settings()
    msg = f"Backfill concluído. Inseridos={ins} Ignorados={skp}"
    print(msg)
    # Código de saída 0 mesmo se nada for inserido
    sys.exit(0)
