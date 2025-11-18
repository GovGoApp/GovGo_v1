#!/usr/bin/env python3
"""
Importador de CNAE para a base Supabase/Postgres.

Usage:
  - Coloque o arquivo `.xlsx` (ou `.csv` separado por `;`) em algum lugar e execute:
    python import_cnae.py --file path/to/cnae.xlsx

O script lê o `.env` localizado na mesma pasta (`v1\db\.env`) e usa
`SUPABASE_USER`, `SUPABASE_PASSWORD`, `SUPABASE_HOST`, `SUPABASE_PORT`, `SUPABASE_DBNAME`.

Cria a tabela `public.cnae` (todos campos TEXT) se não existir e faz upsert
por `cod_total`.
"""
import argparse
import os
from pathlib import Path
import sys

try:
    import pandas as pd
except Exception as e:
    print("Erro: pandas não está instalado. Rode: pip install pandas openpyxl")
    raise

try:
    import psycopg2
    from psycopg2.extras import execute_values
except Exception as e:
    print("Erro: psycopg2 não está instalado. Rode: pip install psycopg2-binary")
    raise

from dotenv import load_dotenv


EXPECTED_COLS = [
    'cod_total', 'nome_total', 'cod_nv0', 'nom_nv0', 'cod_nv1', 'nom_nv1',
    'cod_nv2', 'nom_nv2', 'cod_nv3', 'nom_nv3', 'cod_nv4', 'nom_nv4'
]


def load_env(env_path: Path):
    if not env_path.exists():
        raise FileNotFoundError(f".env não encontrado em {env_path}")
    load_dotenv(dotenv_path=env_path)


def get_db_conn():
    user = os.getenv('SUPABASE_USER')
    password = os.getenv('SUPABASE_PASSWORD')
    host = os.getenv('SUPABASE_HOST')
    port = os.getenv('SUPABASE_PORT')
    dbname = os.getenv('SUPABASE_DBNAME')

    if not all([user, password, host, port, dbname]):
        raise RuntimeError('Variáveis de conexão ao DB ausentes no .env')

    conn_str = f"host={host} port={port} dbname={dbname} user={user} password={password}"
    return psycopg2.connect(conn_str)


def create_table_if_not_exists(conn):
    cols_sql = ',\n'.join([f"{c} TEXT" for c in EXPECTED_COLS])
    create_sql = f"""
    CREATE TABLE IF NOT EXISTS public.cnae (
    {cols_sql},
    PRIMARY KEY (cod_total)
    );
    """
    with conn.cursor() as cur:
        cur.execute(create_sql)
    conn.commit()


def normalize_df_columns(df: pd.DataFrame) -> pd.DataFrame:
    # Normalize column names: strip, lower, replace spaces
    new_cols = {c: c.strip().lower().replace(' ', '_') for c in df.columns}
    df = df.rename(columns=new_cols)
    # Ensure expected columns exist
    missing = [c for c in EXPECTED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Colunas esperadas ausentes no arquivo: {missing}")
    # Fillna and ensure strings
    df = df[EXPECTED_COLS].fillna('').astype(str)
    # Strip whitespace from values
    for c in EXPECTED_COLS:
        df[c] = df[c].str.strip()
    return df


def upsert_df(conn, df: pd.DataFrame, batch_size: int = 500):
    records = df.to_records(index=False)
    tuples = [tuple(r) for r in records]
    cols = EXPECTED_COLS
    cols_sql = ','.join(cols)
    vals_sql = ','.join([f'%s' for _ in cols])
    update_sql = ','.join([f"{c}=EXCLUDED.{c}" for c in cols if c != 'cod_total'])

    insert_sql = f"INSERT INTO public.cnae ({cols_sql}) VALUES %s ON CONFLICT (cod_total) DO UPDATE SET {update_sql}"

    inserted = 0
    with conn.cursor() as cur:
        for i in range(0, len(tuples), batch_size):
            batch = tuples[i:i+batch_size]
            execute_values(cur, insert_sql, batch)
            inserted += len(batch)
    conn.commit()
    return inserted


def read_input_file(path: Path) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {path}")
    if path.suffix.lower() in ['.xlsx', '.xls']:
        df = pd.read_excel(path, dtype=str)
    elif path.suffix.lower() in ['.csv', '.txt']:
        df = pd.read_csv(path, sep=';', dtype=str, encoding='utf-8')
    else:
        raise ValueError('Formato não suportado. Use .xlsx ou .csv')
    return df


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--file', required=True, help='Caminho para o arquivo .xlsx ou .csv (separador ; )')
    parser.add_argument('--env', default=str(Path(__file__).resolve().parent / '.env'), help='Caminho para .env')
    args = parser.parse_args()

    env_path = Path(args.env)
    load_env(env_path)

    input_path = Path(args.file)
    print(f"Lendo arquivo: {input_path}")
    df_raw = read_input_file(input_path)
    print(f"Linhas lidas: {len(df_raw)}")

    try:
        df = normalize_df_columns(df_raw)
    except Exception as e:
        print(f"Erro ao normalizar colunas: {e}")
        sys.exit(1)

    conn = get_db_conn()
    try:
        create_table_if_not_exists(conn)
        inserted = upsert_df(conn, df)
        print(f"Registros processados (inseridos/atualizados): {inserted}")
    finally:
        conn.close()


if __name__ == '__main__':
    main()
