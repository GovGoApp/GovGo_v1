"""
load_embeddings.py
====================

Este script fornece uma função e um programa utilitário para exportar
todas as categorias e seus embeddings da tabela ``categoria`` do
banco PostgreSQL (supabase) para um arquivo CSV. O objetivo é gerar
um arquivo ``cat.csv`` com as colunas:

- ``id_categoria``: identificador da categoria.
- ``cod_cat``: código da categoria.
- ``nom_cat``: nome completo da categoria.
- ``cat_embeddings``: vetor de embeddings como uma lista de números
  em formato de string (por exemplo, ``[-0.0134, 0.0494, ...]``).

O arquivo CSV será salvo em um diretório ``cat`` localizado ao lado
deste script (será criado automaticamente se não existir). Isso
permite que o script de categorização (05d) leia as categorias sem
acessar o banco de dados.

O script usa variáveis de ambiente para obter as credenciais do
banco (``SUPABASE_HOST``, ``SUPABASE_DBNAME``, ``SUPABASE_USER``,
``SUPABASE_PASSWORD``, ``SUPABASE_PORT``). Certifique-se de que o
arquivo ``.env`` esteja configurado com esses valores ou que as
variáveis de ambiente estejam exportadas antes de rodar o script.

Uso:
-----

    # Executar diretamente para criar cat/cat.csv
    python load_embeddings.py

    # Ou importar a função em outro script
    from load_embeddings import load_embeddings
    load_embeddings()

Dependências:
-------------
Requer ``psycopg2`` (ou ``psycopg2-binary``) instalado no ambiente.
Opcionalmente, utiliza ``python-dotenv`` para carregar variáveis de
ambiente de um arquivo ``.env`` se presente.
"""

import os
import csv
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv


def get_db_config() -> dict:
    """Lê as variáveis de ambiente e retorna um dicionário de conexão."""
    # Carrega .env se existir no mesmo diretório
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dotenv_path = os.path.join(script_dir, ".env")
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path)
    host = os.getenv("SUPABASE_HOST")
    dbname = os.getenv("SUPABASE_DBNAME", "postgres")
    user = os.getenv("SUPABASE_USER")
    password = os.getenv("SUPABASE_PASSWORD")
    port = int(os.getenv("SUPABASE_PORT", 5432))
    if not host or not user or password is None:
        raise ValueError(
            "Variáveis de ambiente SUPABASE_HOST, SUPABASE_USER e SUPABASE_PASSWORD devem estar definidas"
        )
    return {
        "host": host,
        "dbname": dbname,
        "user": user,
        "password": password,
        "port": port,
    }


def load_embeddings(output_dir: str | None = None) -> str:
    """
    Exporta todas as categorias e embeddings para um arquivo CSV.

    Args:
        output_dir: Diretório onde o arquivo ``cat.csv`` será salvo. Se
            ``None``, será criado um diretório ``cat`` ao lado deste script.

    Returns:
        Caminho absoluto do arquivo CSV gerado.

    Levanta:
        ValueError se configurações de banco estiverem ausentes.
        psycopg2.Error se ocorrer problema ao consultar o banco.
        OSError se não for possível criar o diretório de saída.
    """
    # Configuração do banco
    config = get_db_config()
    # Determina diretório de saída
    script_dir = os.path.dirname(os.path.abspath(__file__))
    if output_dir is None:
        output_dir = os.path.join(script_dir, "cat")
    # Cria diretório se necessário
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "cat.csv")
    # Conecta ao banco
    conn = psycopg2.connect(**config)
    try:
        with conn.cursor() as cur:
            # Consulta todas as categorias e embeddings
            cur.execute(
                """
                SELECT id_categoria, cod_cat, nom_cat, cat_embeddings
                FROM categoria
                WHERE cat_embeddings IS NOT NULL
                ORDER BY id_categoria
                """
            )
            rows = cur.fetchall()
        # Escreve CSV com cabeçalho
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            # Cabeçalho
            writer.writerow(["id_categoria", "cod_cat", "nom_cat", "cat_embeddings"])
            for row in rows:
                id_cat = row[0]
                cod = row[1]
                nom = row[2]
                emb = row[3]
                # Converte o vetor (pgvector) em string JSON
                if isinstance(emb, list):
                    emb_str = str(emb)
                else:
                    emb_str = str(emb)
                writer.writerow([id_cat, cod, nom, emb_str])
    finally:
        conn.close()
    return output_path


if __name__ == "__main__":
    try:
        csv_path = load_embeddings()
        print(f"Arquivo CSV gerado em: {csv_path}")
    except Exception as exc:
        print(f"Erro ao gerar cat.csv: {exc}")