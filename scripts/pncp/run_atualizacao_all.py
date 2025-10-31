#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Runner diário PNCP (atualização) para Contratos, Atas e PCA

- Itera dia a dia em um intervalo --from/--to (AAAAMMDD)
- Se não houver --to, usa o dia corrente
- Se não houver --from, usa o LED (last_processed_date) de cada domínio separadamente
- Se nenhum for informado, usa LED→hoje
- Se LED == hoje para um domínio, não faz nada para esse domínio

Obs: Não altera a lógica interna dos 01; apenas orquestra e garante persistência do LED ao final de cada dia.
"""
import os
import argparse
from datetime import datetime, timedelta, timezone
from typing import Optional
import importlib.util

import psycopg2
from dotenv import load_dotenv
from rich.progress import Progress, BarColumn, TimeElapsedColumn, TimeRemainingColumn, SpinnerColumn, TextColumn

# Chaves de estado
LED_KEYS = {
    "contrato": "last_processed_date_contrato",
    "ata": "last_processed_date_ata",
    "pca": "last_processed_date_pca",
}


def _load_env():
    env_path = os.path.normpath(os.path.join(os.path.dirname(__file__), ".env"))
    load_dotenv(env_path)


def _db_conn():
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
        (key, value, "Atualizado pelo runner PNCP"),
    )


def _date_iter(d_from: str, d_to: str):
    dt_from = datetime.strptime(d_from, "%Y%m%d").date()
    dt_to = datetime.strptime(d_to, "%Y%m%d").date()
    cur = dt_from
    while cur <= dt_to:
        yield cur.strftime("%Y%m%d")
        cur += timedelta(days=1)


def _load_process_fn(module_path: str, func_name: str = "process_window"):
    spec = importlib.util.spec_from_file_location("_runner_loaded_module", module_path)
    mod = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(mod)  # type: ignore
    fn = getattr(mod, func_name)
    return fn


def main():
    _load_env()

    parser = argparse.ArgumentParser(description="Runner PNCP diário (atualização)")
    parser.add_argument("--from", dest="date_from", required=False, help="AAAAMMDD")
    parser.add_argument("--to", dest="date_to", required=False, help="AAAAMMDD")
    args = parser.parse_args()

    today = datetime.now(timezone.utc).strftime("%Y%m%d")

    base_dir = os.path.dirname(__file__)
    path_contrato = os.path.join(base_dir, "contrato", "01_processing.py")
    path_ata = os.path.join(base_dir, "ata", "01_processing.py")
    path_pca = os.path.join(base_dir, "pca", "01_processing.py")

    contrato_process = _load_process_fn(path_contrato)
    ata_process = _load_process_fn(path_ata)
    pca_process = _load_process_fn(path_pca)

    with _db_conn() as conn:
        conn.autocommit = False
        with conn.cursor() as cur:
            # Determina LEDs (um por domínio)
            leds = {
                "contrato": get_system_config(cur, LED_KEYS["contrato"]) or today,
                "ata": get_system_config(cur, LED_KEYS["ata"]) or today,
                "pca": get_system_config(cur, LED_KEYS["pca"]) or today,
            }
            conn.commit()

    # Calcula intervalos por domínio
    def _compute_range(led: str) -> Optional[tuple[str, str]]:
        d_from = args.date_from or led
        d_to = args.date_to or today
        # Se LED já é hoje e sem --from explícito, não roda
        if not args.date_from and d_from >= d_to:
            return None
        if d_from > d_to:
            return None
        return d_from, d_to

    ranges = {k: _compute_range(leds[k]) for k in leds.keys()}

    # Progresso por domínio (dias)
    with Progress(
        SpinnerColumn(style="green"),
        TextColumn("[bold]{task.fields[dom]}[/] {task.description}"),
        BarColumn(bar_width=None),
        TextColumn("{task.completed}/{task.total}"),
        TimeElapsedColumn(),
        transient=False,
    ) as progress:
        tasks = {}
        for dom in ["contrato", "ata", "pca"]:
            r = ranges.get(dom)
            if r is None:
                tasks[dom] = None
                continue
            total_days = (datetime.strptime(r[1], "%Y%m%d").date() - datetime.strptime(r[0], "%Y%m%d").date()).days + 1
            tasks[dom] = progress.add_task(f"{r[0]}→{r[1]}", total=total_days, dom=dom)

        # Executa domínio a domínio (ordem: contrato, ata, pca)
        for dom in ["contrato", "ata", "pca"]:
            r = ranges.get(dom)
            if r is None:
                continue
            for day in _date_iter(r[0], r[1]):
                # Dispara o 01 específico
                if dom == "contrato":
                    contrato_process(day, day, mode="atualizacao")
                elif dom == "ata":
                    ata_process(day, day, mode="atualizacao")
                elif dom == "pca":
                    pca_process(day, day)
                # Atualiza LED explicitamente
                with _db_conn() as conn2:
                    conn2.autocommit = False
                    with conn2.cursor() as cur2:
                        set_system_config(cur2, LED_KEYS[dom], day)
                        conn2.commit()
                # Avança barra
                if tasks.get(dom) is not None:
                    progress.update(tasks[dom], advance=1, description=day)


if __name__ == "__main__":
    main()
