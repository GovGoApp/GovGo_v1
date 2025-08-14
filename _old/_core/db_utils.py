#!/usr/bin/env python3
"""
GovGo V1 - Utilitários de Banco de Dados
=========================================
Funções auxiliares para conexão com banco de dados
"""

import asyncio
import asyncpg
import os
from typing import Optional

async def get_db_connection():
    """
    Cria conexão assíncrona com PostgreSQL/Supabase
    """
    # Configurações de conexão
    database_url = os.getenv('DATABASE_URL')
    
    if not database_url:
        # Fallback para configurações individuais
        host = os.getenv('DB_HOST', 'localhost')
        port = os.getenv('DB_PORT', '5432')
        database = os.getenv('DB_NAME', 'govgo_v1')
        user = os.getenv('DB_USER', 'postgres')
        password = os.getenv('DB_PASSWORD', '')
        
        database_url = f"postgresql://{user}:{password}@{host}:{port}/{database}"
    
    try:
        connection = await asyncpg.connect(database_url)
        return connection
    except Exception as e:
        raise Exception(f"Erro ao conectar ao banco: {str(e)}")

async def test_connection():
    """
    Testa a conexão com o banco de dados
    """
    try:
        conn = await get_db_connection()
        result = await conn.fetch("SELECT 1 as test")
        await conn.close()
        return True
    except Exception as e:
        print(f"Erro na conexão: {e}")
        return False
