# =======================================================================
# CRIAÇÃO DA TABELA CATEGORIAS NO SUPABASE
# =======================================================================
# Este script cria a tabela 'categorias' no banco Supabase com base na
# estrutura da planilha CATEGORIAS.xlsx analisada anteriormente.
# 
# Funcionalidades:
# - Conexão com Supabase usando configurações do .env
# - Criação da tabela categorias com todos os campos
# - Adição do campo cat_embeddings para vetores de busca semântica
# - Criação de índices otimizados para performance
# - Verificação de integridade da tabela criada
# 
# Resultado: Tabela categorias pronta para receber dados e embeddings.
# =======================================================================

import psycopg2
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Configure Rich console
console = Console()

def load_database_config():
    """Carrega configurações do banco de dados"""
    
    script_dir = os.path.dirname(os.path.abspath(__file__))
    env_path = os.path.join(script_dir, "supabase_v0.env")
    
    console.print(f"📂 [cyan]Carregando configuração: {env_path}[/cyan]")
    
    if not os.path.exists(env_path):
        console.print(f"[red]❌ Arquivo não encontrado: {env_path}[/red]")
        sys.exit(1)
    
    load_dotenv(env_path)
    
    config = {
        'user': os.getenv('user'),
        'password': os.getenv('password'),
        'host': os.getenv('host'),
        'port': os.getenv('port'),
        'dbname': os.getenv('dbname')
    }
    
    # Verificar se todas as configurações estão presentes
    missing = [k for k, v in config.items() if not v]
    if missing:
        console.print(f"[red]❌ Configurações faltando: {', '.join(missing)}[/red]")
        sys.exit(1)
    
    console.print(f"[green]✓ Configurações carregadas com sucesso[/green]")
    console.print(f"   Host: {config['host']}")
    console.print(f"   Port: {config['port']}")
    console.print(f"   Database: {config['dbname']}")
    console.print(f"   User: {config['user']}")
    
    return config

def create_categorias_table():
    """Cria a tabela categorias no Supabase"""
    
    console.print(Panel("[bold green]CRIAÇÃO DA TABELA CATEGORIAS[/bold green]"))
    
    # Carregar configurações
    config = load_database_config()
    
    # Conectar ao banco
    console.print("🔌 [yellow]Conectando ao Supabase...[/yellow]")
    
    try:
        conn = psycopg2.connect(
            user=config['user'],
            password=config['password'],
            host=config['host'],
            port=config['port'],
            dbname=config['dbname']
        )
        
        console.print(f"[green]✓ Conectado ao Supabase: {config['host']}[/green]")
        
    except Exception as e:
        console.print(f"[red]❌ Erro ao conectar: {e}[/red]")
        sys.exit(1)
    
    cursor = conn.cursor()
    
    try:
        # 1. VERIFICAR SE A TABELA JÁ EXISTE
        console.print("🔍 [cyan]Verificando se a tabela já existe...[/cyan]")
        
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'categorias'
            );
        """)
        
        table_exists = cursor.fetchone()[0]
        
        if table_exists:
            console.print("⚠️ [yellow]Tabela 'categorias' já existe![/yellow]")
            response = input("Deseja recriar a tabela? (s/n): ").lower().strip()
            
            if response == 's':
                console.print("🗑️ [red]Removendo tabela existente...[/red]")
                cursor.execute("DROP TABLE IF EXISTS categorias CASCADE;")
                conn.commit()
                console.print("[green]✓ Tabela removida[/green]")
            else:
                console.print("[yellow]Operação cancelada pelo usuário[/yellow]")
                return False
        
        # 2. CRIAR A TABELA
        console.print("🏗️ [blue]Criando tabela categorias...[/blue]")
        
        create_table_sql = """
        CREATE TABLE IF NOT EXISTS categorias (
            id SERIAL PRIMARY KEY,
            codcat VARCHAR(100) NOT NULL,
            nomcat TEXT NOT NULL,
            codnv0 VARCHAR(100) NOT NULL,
            nomnv0 VARCHAR(100) NOT NULL,
            codnv1 INTEGER NOT NULL,
            nomnv1 VARCHAR(500) NOT NULL,
            codnv2 INTEGER NOT NULL,
            nomnv2 VARCHAR(500) NOT NULL,
            codnv3 INTEGER NOT NULL,
            nomnv3 VARCHAR(500) NOT NULL,
            cat_embeddings VECTOR(3072),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """
        
        cursor.execute(create_table_sql)
        conn.commit()
        console.print("[green]✓ Tabela criada com sucesso![/green]")
        
        # 3. CRIAR ÍNDICES
        console.print("📋 [blue]Criando índices...[/blue]")
        
        indices_sql = [
            # Índice para busca por código da categoria
            "CREATE INDEX IF NOT EXISTS idx_categorias_codcat ON categorias(codcat);",
            
            # Índice para busca por níveis
            "CREATE INDEX IF NOT EXISTS idx_categorias_nivel0 ON categorias(codnv0);",
            "CREATE INDEX IF NOT EXISTS idx_categorias_nivel1 ON categorias(codnv1);",
            "CREATE INDEX IF NOT EXISTS idx_categorias_nivel2 ON categorias(codnv2);",
            "CREATE INDEX IF NOT EXISTS idx_categorias_nivel3 ON categorias(codnv3);",
            
            # Índice para busca textual
            "CREATE INDEX IF NOT EXISTS idx_categorias_nomcat ON categorias USING gin(to_tsvector('portuguese', nomcat));",
            "CREATE INDEX IF NOT EXISTS idx_categorias_nomnv1 ON categorias USING gin(to_tsvector('portuguese', nomnv1));",
            "CREATE INDEX IF NOT EXISTS idx_categorias_nomnv2 ON categorias USING gin(to_tsvector('portuguese', nomnv2));",
            "CREATE INDEX IF NOT EXISTS idx_categorias_nomnv3 ON categorias USING gin(to_tsvector('portuguese', nomnv3));",
            
            # Índice para embeddings (busca semântica)
            "CREATE INDEX IF NOT EXISTS idx_categorias_embeddings ON categorias USING ivfflat (cat_embeddings vector_cosine_ops);"
        ]
        
        for i, sql in enumerate(indices_sql, 1):
            try:
                cursor.execute(sql)
                console.print(f"   ✓ Índice {i}/{len(indices_sql)} criado")
            except Exception as e:
                console.print(f"   ⚠️ Erro no índice {i}: {e}")
        
        conn.commit()
        console.print("[green]✓ Índices criados![/green]")
        
        # 4. VERIFICAR ESTRUTURA DA TABELA
        console.print("🔍 [cyan]Verificando estrutura da tabela...[/cyan]")
        
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'categorias' 
            AND table_schema = 'public'
            ORDER BY ordinal_position;
        """)
        
        columns = cursor.fetchall()
        
        # Criar tabela de estrutura
        structure_table = Table()
        structure_table.add_column("Campo", style="green")
        structure_table.add_column("Tipo", style="yellow")
        structure_table.add_column("Nulo?", style="cyan")
        structure_table.add_column("Padrão", style="magenta")
        
        for col in columns:
            structure_table.add_row(
                col[0],  # column_name
                col[1],  # data_type
                "Sim" if col[2] == "YES" else "Não",  # is_nullable
                str(col[3]) if col[3] else ""  # column_default
            )
        
        console.print(structure_table)
        
        # 5. VERIFICAR ÍNDICES CRIADOS
        console.print("📋 [cyan]Verificando índices criados...[/cyan]")
        
        cursor.execute("""
            SELECT indexname, indexdef 
            FROM pg_indexes 
            WHERE tablename = 'categorias'
            ORDER BY indexname;
        """)
        
        indices = cursor.fetchall()
        
        for idx_name, idx_def in indices:
            console.print(f"   ✓ [green]{idx_name}[/green]")
        
        console.print(f"[green]✓ Total de {len(indices)} índices encontrados[/green]")
        
        # 6. INFORMAÇÕES FINAIS
        console.print("\n📊 [bold blue]RESUMO DA TABELA CRIADA:[/bold blue]")
        console.print(f"   📋 Nome: categorias")
        console.print(f"   🔢 Campos: {len(columns)}")
        console.print(f"   📋 Índices: {len(indices)}")
        console.print(f"   🧠 Pronta para embeddings: Sim (VECTOR 3072)")
        console.print(f"   🔍 Busca textual: Sim (GIN indices)")
        console.print(f"   🎯 Busca semântica: Sim (IVFFlat index)")
        
        return True
        
    except Exception as e:
        console.print(f"[red]❌ Erro durante criação: {e}[/red]")
        conn.rollback()
        return False
        
    finally:
        cursor.close()
        conn.close()
        console.print("🔌 [yellow]Conexão fechada[/yellow]")

def main():
    """Função principal"""
    start_time = datetime.now()
    
    try:
        success = create_categorias_table()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        if success:
            console.print(Panel(f"[bold green]TABELA CATEGORIAS CRIADA COM SUCESSO EM {duration:.2f}s![/bold green]"))
            console.print("[cyan]A tabela está pronta para:[/cyan]")
            console.print("   📊 Receber dados da planilha CATEGORIAS.xlsx")
            console.print("   🧠 Gerar embeddings para busca semântica")
            console.print("   🔍 Realizar consultas textuais e por código")
        else:
            console.print(Panel(f"[bold red]FALHA NA CRIAÇÃO DA TABELA![/bold red]"))
        
    except Exception as e:
        console.print(Panel(f"[bold red]ERRO GERAL: {e}[/bold red]"))

if __name__ == "__main__":
    main()
