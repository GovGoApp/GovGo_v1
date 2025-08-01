#!/usr/bin/env python3
"""
GovGo V1 - Limpar Banco de Dados COMPLETO
==========================================
Remove TODAS as tabelas, funções, triggers, constraints e extensões do Supabase V1
Limpeza total para recomeçar do zero
"""

import os
import psycopg2
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from dotenv import load_dotenv

# Carregar variáveis do .env
load_dotenv()

console = Console()

def clean_database():
    """Remove TUDO do banco - limpeza total"""
    
    # Confirmação de segurança
    console.print(Panel.fit(
        "[bold red]⚠️ ATENÇÃO: LIMPEZA COMPLETA[/bold red]\n"
        "Este script vai REMOVER TODAS as tabelas do Supabase V1",
        title="🗑️ Drop All Tables"
    ))
    
    confirm = Confirm.ask("🚨 Confirma a remoção de TODAS as tabelas?")
    if not confirm:
        console.print("❌ Operação cancelada pelo usuário")
        return False
    
    try:
        # Conectar ao banco
        connection = psycopg2.connect(
            host=os.getenv("SUPABASE_HOST"),
            database=os.getenv("SUPABASE_DBNAME"),
            user=os.getenv("SUPABASE_USER"),
            password=os.getenv("SUPABASE_PASSWORD"),
            port=int(os.getenv("SUPABASE_PORT", "5432"))
        )
        
        console.print("✅ Conectado ao Supabase")
        cursor = connection.cursor()
        
        # PASSO 1: Descobrir TODAS as tabelas que existem no schema public
        console.print("🔍 Descobrindo todas as tabelas existentes...")
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        
        existing_tables = [row[0] for row in cursor.fetchall()]
        console.print(f"📋 Encontradas {len(existing_tables)} tabelas: {', '.join(existing_tables)}")
        
        # PASSO 2: Remover TODAS as tabelas com CASCADE
        if existing_tables:
            console.print("🗑️ Removendo TODAS as tabelas...")
            for table in existing_tables:
                try:
                    ######################### ATENÇÂO!!!!
                    # cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE;")
                    console.print(f"  ✅ {table} removida")
                except Exception as e:
                    console.print(f"  ❌ Erro em {table}: {e}")
        
        # PASSO 3: Remover TODAS as funções personalizadas
        console.print("🔧 Removendo funções personalizadas...")
        cursor.execute("""
            SELECT routine_name 
            FROM information_schema.routines 
            WHERE routine_schema = 'public' 
            AND routine_type = 'FUNCTION'
            ORDER BY routine_name;
        """)
        
        existing_functions = [row[0] for row in cursor.fetchall()]
        for func in existing_functions:
            try:
                cursor.execute(f"DROP FUNCTION IF EXISTS {func}() CASCADE;")
                console.print(f"  ✅ Função {func} removida")
            except Exception as e:
                console.print(f"  ❌ Erro na função {func}: {e}")
        
        # PASSO 4: Remover TODOS os tipos personalizados
        console.print("📦 Removendo tipos personalizados...")
        cursor.execute("""
            SELECT typname 
            FROM pg_type 
            WHERE typnamespace = (SELECT oid FROM pg_namespace WHERE nspname = 'public')
            AND typtype = 'c'
            ORDER BY typname;
        """)
        
        existing_types = [row[0] for row in cursor.fetchall()]
        for typ in existing_types:
            try:
                cursor.execute(f"DROP TYPE IF EXISTS {typ} CASCADE;")
                console.print(f"  ✅ Tipo {typ} removido")
            except Exception as e:
                console.print(f"  ❌ Erro no tipo {typ}: {e}")
        
        # PASSO 5: Garantir que a extensão vector existe
        console.print("🔌 Garantindo extensão vector...")
        try:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            console.print("  ✅ Extensão vector garantida")
        except Exception as e:
            console.print(f"  ❌ Erro na extensão: {e}")
        
        # PASSO 6: Confirmar mudanças
        connection.commit()
        console.print("\n🎉 LIMPEZA TOTAL CONCLUÍDA!")
        console.print("📊 Status final:")
        
        # Verificar se realmente está limpo
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE';
        """)
        remaining_tables = cursor.fetchall()
        
        if remaining_tables:
            console.print(f"  ⚠️ Ainda existem {len(remaining_tables)} tabelas")
        else:
            console.print("  ✅ Nenhuma tabela restante - banco completamente limpo")
        
        cursor.close()
        connection.close()
        console.print("🔌 Conexão fechada")
        
        return True
        
    except Exception as e:
        console.print(f"❌ Erro ao limpar tabelas: {e}")
        return False

def main():
    """Função principal"""
    if clean_database():
        console.print("\n✅ [bold green]Banco limpo com sucesso![/bold green]")
        console.print("🚀 Agora você pode executar o setup do banco novamente")
    else:
        console.print("\n❌ [bold red]Falha na limpeza[/bold red]")
        exit(1)

if __name__ == "__main__":
    main()
