"""
gvg_database.py
Conexões e utilidades de banco (VERSÃO V1 – apenas schema novo).
"""

import os
import re
import psycopg2
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Carregar configurações
load_dotenv()

def _load_env_priority():
    """Carrega variáveis de ambiente seguindo prioridade V1.

    Ordem:
      1. supabase_v1.env (se existir)
      2. .env (já carregado inicialmente)
      3. supabase_v0.env (apenas fallback – não recomendado)
    """
    for candidate in ("supabase_v1.env", ".env", "supabase_v0.env"):
        if os.path.exists(candidate):
            load_dotenv(candidate, override=False)


def create_connection():
    """Cria conexão psycopg2 com base V1 (sem lógica de versão)."""
    try:
        _load_env_priority()
        connection = psycopg2.connect(
            host=os.getenv("SUPABASE_HOST", "aws-0-sa-east-1.pooler.supabase.com"),
            database=os.getenv("SUPABASE_DBNAME", os.getenv("SUPABASE_DB_NAME", "postgres")),
            user=os.getenv("SUPABASE_USER"),
            password=os.getenv("SUPABASE_PASSWORD"),
            port=os.getenv("SUPABASE_PORT", "6543"),
            connect_timeout=10
        )
        return connection
    except Exception as e:
        print(f"Erro ao conectar ao banco: {e}")
        return None

def create_engine_connection():
    """Cria engine SQLAlchemy (uso Pandas)."""
    try:
        _load_env_priority()
        host = os.getenv('SUPABASE_HOST', 'aws-0-sa-east-1.pooler.supabase.com')
        user = os.getenv('SUPABASE_USER')
        password = os.getenv('SUPABASE_PASSWORD')
        port = os.getenv('SUPABASE_PORT', '6543')
        dbname = os.getenv('SUPABASE_DBNAME', os.getenv('SUPABASE_DB_NAME', 'postgres'))
        connection_string = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
        return create_engine(connection_string, pool_pre_ping=True)
    except Exception as e:
        print(f"Erro ao criar engine SQLAlchemy: {e}")
        return None

"""
gvg_database.py
Conexões e utilidades de banco (VERSÃO V1 – apenas schema novo).

Alterações Fase 2:
    • Remove referências a supabase_v0.env; prioriza supabase_v1.env ou .env.
    • Corrige nome de variável de ambiente SUPABASE_DBNAME.
    • Ajusta fetch_documentos para tabela 'contratacao' (antes 'contratacoes').
    • Garante comparação segura de datas (campos TEXT) usando expressão defensiva.
"""

import os
import re
import psycopg2
from sqlalchemy import create_engine
from dotenv import load_dotenv

# Carregar configurações
load_dotenv()

def _load_env_priority():
    """Carrega variáveis de ambiente seguindo prioridade V1.

    Ordem:
      1. supabase_v1.env (se existir)
      2. .env (já carregado inicialmente)
      3. supabase_v0.env (apenas fallback – não recomendado)
    """
    for candidate in ("supabase_v1.env", ".env", "supabase_v0.env"):
        if os.path.exists(candidate):
            load_dotenv(candidate, override=False)


def create_connection():
    """Cria conexão psycopg2 com base V1 (sem lógica de versão)."""
    try:
        _load_env_priority()
        connection = psycopg2.connect(
            host=os.getenv("SUPABASE_HOST", "aws-0-sa-east-1.pooler.supabase.com"),
            database=os.getenv("SUPABASE_DBNAME", os.getenv("SUPABASE_DB_NAME", "postgres")),
            user=os.getenv("SUPABASE_USER"),
            password=os.getenv("SUPABASE_PASSWORD"),
            port=os.getenv("SUPABASE_PORT", "6543"),
            connect_timeout=10
        )
        return connection
    except Exception as e:
        print(f"Erro ao conectar ao banco: {e}")
        return None

def create_engine_connection():
    """Cria engine SQLAlchemy (uso Pandas)."""
    try:
        _load_env_priority()
        host = os.getenv('SUPABASE_HOST', 'aws-0-sa-east-1.pooler.supabase.com')
        user = os.getenv('SUPABASE_USER')
        password = os.getenv('SUPABASE_PASSWORD')
        port = os.getenv('SUPABASE_PORT', '6543')
        dbname = os.getenv('SUPABASE_DBNAME', os.getenv('SUPABASE_DB_NAME', 'postgres'))
        connection_string = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
        return create_engine(connection_string, pool_pre_ping=True)
    except Exception as e:
        print(f"Erro ao criar engine SQLAlchemy: {e}")
        return None

