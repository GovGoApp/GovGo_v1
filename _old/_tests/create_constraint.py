#!/usr/bin/env python3
"""
Script para criar constraint única em item_contratacao
"""

import psycopg2
from dotenv import load_dotenv
import os
from rich.console import Console

console = Console()

# Carregar configurações
script_dir = os.path.dirname(os.path.abspath(__file__))
v1_root = os.path.dirname(script_dir)
load_dotenv(os.path.join(v1_root, ".env"))

DB_CONFIG = {
    'host': os.getenv('SUPABASE_HOST'),
    'port': os.getenv('SUPABASE_PORT'),
    'database': os.getenv('SUPABASE_DBNAME'),
    'user': os.getenv('SUPABASE_USER'),
    'password': os.getenv('SUPABASE_PASSWORD')
}

def create_missing_constraint():
    """Criar constraint única em item_contratacao se não existir"""
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Verificar se já existe constraint
        cursor.execute("""
            SELECT constraint_name 
            FROM information_schema.table_constraints 
            WHERE table_name = 'item_contratacao' 
            AND constraint_type = 'UNIQUE' 
            AND constraint_name LIKE '%numero_controle_pncp%'
        """)
        
        existing = cursor.fetchone()
        
        if existing:
            console.print(f"✅ Constraint já existe: {existing[0]}")
        else:
            console.print("🔧 Criando constraint única em item_contratacao...")
            
            # Verificar se há duplicatas primeiro
            cursor.execute("""
                SELECT numero_controle_pncp, numero_item, COUNT(*) as count
                FROM item_contratacao 
                WHERE numero_controle_pncp IS NOT NULL 
                AND numero_item IS NOT NULL
                GROUP BY numero_controle_pncp, numero_item 
                HAVING COUNT(*) > 1
                LIMIT 5
            """)
            
            duplicates = cursor.fetchall()
            
            if duplicates:
                console.print("⚠️ Duplicatas encontradas:")
                for numero_controle, numero_item, count in duplicates:
                    console.print(f"   {numero_controle} + {numero_item}: {count} ocorrências")
                
                # Remover duplicatas mantendo apenas o primeiro registro
                console.print("🧹 Removendo duplicatas...")
                cursor.execute("""
                    DELETE FROM item_contratacao 
                    WHERE id_item NOT IN (
                        SELECT MIN(id_item)
                        FROM item_contratacao 
                        WHERE numero_controle_pncp IS NOT NULL 
                        AND numero_item IS NOT NULL
                        GROUP BY numero_controle_pncp, numero_item
                    )
                    AND numero_controle_pncp IS NOT NULL 
                    AND numero_item IS NOT NULL
                """)
                
                removed = cursor.rowcount
                console.print(f"✅ {removed} registros duplicados removidos")
            
            # Criar a constraint
            cursor.execute("""
                ALTER TABLE item_contratacao 
                ADD CONSTRAINT uk_item_contratacao_numero_controle_pncp_numero_item 
                UNIQUE (numero_controle_pncp, numero_item)
            """)
            
            console.print("✅ Constraint única criada com sucesso!")
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        console.print(f"❌ Erro: {e}")

if __name__ == "__main__":
    create_missing_constraint()
