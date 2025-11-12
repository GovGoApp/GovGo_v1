#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""
Carrega o CSV de municípios do IBGE para Postgres (Supabase).

Uso (PowerShell):
    python .\scripts\ibge\load_ibge_municipios.py \
        --csv-path "C:\Users\Haroldo Duraes\Desktop\GOvGO\v0\#DATA\IBGE\municipios.csv" \
        --truncate

Requer variáveis no .env (em v1/scripts/.env):
    SUPABASE_HOST, SUPABASE_PORT, SUPABASE_DBNAME, SUPABASE_USER, SUPABASE_PASSWORD

Tabela alvo: public.municipios
"""
import os
import argparse
from pathlib import Path
from dotenv import load_dotenv
import psycopg2


DDL = """
CREATE TABLE IF NOT EXISTS public.municipios (
    municipio bigint PRIMARY KEY,
    uf smallint,
    uf_code text,
    name text,
    mesoregion integer,
    microregion integer,
    rgint integer,
    rgi integer,
    osm_relation_id bigint,
    wikidata_id text,
    is_capital text,
    wikipedia_pt text,
    lon double precision,
    lat double precision,
    no_accents text,
    slug_name text,
    alternative_names text,
    pop_21 integer
);
CREATE INDEX IF NOT EXISTS idx_municipios_uf ON public.municipios(uf);
CREATE INDEX IF NOT EXISTS idx_municipios_uf_code ON public.municipios(uf_code);
"""


COPY_SQL = """
COPY public.municipios (
    municipio, uf, uf_code, name, mesoregion, microregion, rgint, rgi,
    osm_relation_id, wikidata_id, is_capital, wikipedia_pt, lon, lat,
    no_accents, slug_name, alternative_names, pop_21
) FROM STDIN WITH (FORMAT CSV, HEADER TRUE, NULL '', ENCODING 'UTF8');
"""


def load_env():
    env_path = Path(__file__).resolve().parents[2] / 'scripts' / '.env'
    load_dotenv(str(env_path))


def get_conn():
    return psycopg2.connect(
        host=os.environ.get("SUPABASE_HOST"),
        port=int(os.environ.get("SUPABASE_PORT", "6543")),
        dbname=os.environ.get("SUPABASE_DBNAME"),
        user=os.environ.get("SUPABASE_USER"),
        password=os.environ.get("SUPABASE_PASSWORD"),
    )


def main():
    parser = argparse.ArgumentParser(description="Importa CSV de municípios para Postgres")
    parser.add_argument("--csv-path", required=True, help="Caminho absoluto para o CSV do IBGE")
    parser.add_argument("--truncate", action="store_true", help="Limpa a tabela antes de importar")
    args = parser.parse_args()

    load_env()
    csv_path = args.csv_path
    if not os.path.isfile(csv_path):
        raise FileNotFoundError(f"CSV não encontrado: {csv_path}")

    conn = get_conn()
    try:
        with conn:
            with conn.cursor() as cur:
                # Cria tabela e índices se não existirem
                cur.execute(DDL)
                if args.truncate:
                    cur.execute("TRUNCATE TABLE public.municipios")
            # COPY em bloco
            with conn.cursor() as cur, open(csv_path, "r", encoding="utf-8") as f:
                cur.copy_expert(COPY_SQL, f)
    finally:
        try:
            conn.close()
        except Exception:
            pass

    print("✅ Importação concluída em public.municipios")


if __name__ == "__main__":
    main()
