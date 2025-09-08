"""Backfill de rótulos em user_bookmarks.

Gera rótulos (3-4 palavras) para favoritos sem rotulo usando generate_contratacao_label.
Segurança:
- Sai silenciosamente se coluna rotulo não existir.
- Atualiza em lotes (commit a cada N) para reduzir risco.
- Suporta modo dry-run.

Uso:
  python 06_backfill_bookmark_rotulos.py --limit 300 --commit-batch 25 --sleep-ms 150
  python 06_backfill_bookmark_rotulos.py --dry-run
"""
from __future__ import annotations
import argparse
import time
from typing import Optional

from gvg_database import create_connection
from gvg_ai_utils import generate_contratacao_label


def has_rotulo_column(cur) -> bool:
    try:
        cur.execute(
            """
            SELECT 1 FROM information_schema.columns
            WHERE table_schema='public' AND table_name='user_bookmarks' AND column_name='rotulo'
            """
        )
        return cur.fetchone() is not None
    except Exception:
        return False

def fetch_candidates(cur, limit: int) -> list:
    # Tenta diferentes colunas de descrição em contratacao
    # coalesce na ordem de prioridade
    cur.execute(
        f"""
        SELECT ub.id, ub.user_id, ub.numero_controle_pncp,
               COALESCE(c.descricaocompleta, c."descricaoCompleta", c.objeto_compra, c.objeto) AS descricao
        FROM public.user_bookmarks ub
        LEFT JOIN public.contratacao c ON c.numero_controle_pncp = ub.numero_controle_pncp
        WHERE (ub.rotulo IS NULL OR trim(ub.rotulo) = '')
        ORDER BY ub.id
        LIMIT %s
        """,
        (limit,)
    )
    rows = cur.fetchall() or []
    out = []
    for r in rows:
        try:
            out.append({
                'id': r[0],
                'user_id': r[1],
                'numero_controle_pncp': r[2],
                'descricao': r[3] or ''
            })
        except Exception:
            continue
    return out


def update_rotulo(cur, bid: int, rotulo: str):
    cur.execute(
        "UPDATE public.user_bookmarks SET rotulo = %s WHERE id = %s",
        (rotulo, bid)
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=500, help='Máx registros a processar na seleção inicial.')
    ap.add_argument('--commit-batch', type=int, default=20, help='Commits a cada N updates.')
    ap.add_argument('--sleep-ms', type=int, default=200, help='Pausa entre chamadas de geração (mitigar rate).')
    ap.add_argument('--dry-run', action='store_true', help='Não grava no banco, apenas simula.')
    args = ap.parse_args()

    conn = create_connection()
    if not conn:
        print('Conexão BD indisponível.')
        return
    cur = conn.cursor()
    try:
        if not has_rotulo_column(cur):
            print('Coluna rotulo inexistente. Encerrando.')
            return
        candidatos = fetch_candidates(cur, args.limit)
        if not candidatos:
            print('Nenhum favorito sem rótulo.')
            return
        print(f'Candidatos: {len(candidatos)}')
        processed = 0
        success = 0
        failed = 0
        batch = 0
        t0 = time.time()
        for item in candidatos:
            bid = item['id']
            desc = (item.get('descricao') or '').strip()
            try:
                rotulo = generate_contratacao_label(desc) if desc else 'Indefinido'
            except Exception:
                rotulo = 'Indefinido'
            if args.dry_run:
                print(f"[DRY] id={bid} pncp={item['numero_controle_pncp']} -> {rotulo}")
            else:
                try:
                    update_rotulo(cur, bid, rotulo)
                    success += 1
                    batch += 1
                except Exception:
                    failed += 1
            processed += 1
            if not args.dry_run and batch >= args.commit_batch:
                try:
                    conn.commit()
                except Exception:
                    pass
                batch = 0
            # Pausa simples para evitar estouro de rate
            if args.sleep_ms > 0:
                time.sleep(args.sleep_ms / 1000.0)
        # Commit final
        if not args.dry_run:
            try:
                conn.commit()
            except Exception:
                pass
        dt = time.time() - t0
        print(f'Processados={processed} Sucesso={success} Falha={failed} Tempo={dt:.1f}s DryRun={args.dry_run}')
    finally:
        try:
            cur.close()
        except Exception:
            pass
        try:
            conn.close()
        except Exception:
            pass

if __name__ == '__main__':
    main()
