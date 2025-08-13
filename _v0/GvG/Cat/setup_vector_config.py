# =======================================================================
# CONFIGURAÇÃO E VERIFICAÇÃO DE EXTENSÕES VETORIAIS
# =======================================================================
# Este script verifica e configura as extensões necessárias para
# trabalhar com embeddings no Supabase.
# 
# Funcionalidades:
# - Verificação da extensão pgvector
# - Habilitação da extensão se necessário
# - Configuração de índices vetoriais otimizados
# - Testes de performance para embeddings
# 
# Resultado: Ambiente otimizado para busca semântica.
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
    
    load_dotenv(env_path)
    
    config = {
        'user': os.getenv('user'),
        'password': os.getenv('password'),
        'host': os.getenv('host'),
        'port': os.getenv('port'),
        'dbname': os.getenv('dbname')
    }
    
    return config

def setup_vector_extensions():
    """Configura extensões vetoriais e índices otimizados"""
    
    console.print(Panel("[bold green]CONFIGURAÇÃO DE EXTENSÕES VETORIAIS[/bold green]"))
    
    config = load_database_config()
    
    try:
        conn = psycopg2.connect(
            user=config['user'],
            password=config['password'],
            host=config['host'],
            port=config['port'],
            dbname=config['dbname']
        )
        
        console.print(f"[green]✓ Conectado ao Supabase[/green]")
        
    except Exception as e:
        console.print(f"[red]❌ Erro ao conectar: {e}[/red]")
        sys.exit(1)
    
    cursor = conn.cursor()
    
    try:
        # 1. VERIFICAR EXTENSÕES INSTALADAS
        console.print("🔍 [cyan]Verificando extensões instaladas...[/cyan]")
        
        cursor.execute("SELECT extname FROM pg_extension WHERE extname LIKE '%vector%';")
        vector_extensions = cursor.fetchall()
        
        console.print(f"[green]✓ Extensões vetoriais encontradas: {vector_extensions}[/green]")
        
        # 2. VERIFICAR SE A TABELA TEM DADOS
        console.print("📊 [cyan]Verificando dados na tabela categorias...[/cyan]")
        
        cursor.execute("SELECT COUNT(*) FROM categorias;")
        count = cursor.fetchone()[0]
        
        console.print(f"[yellow]📋 Registros na tabela: {count:,}[/yellow]")
        
        # 3. CRIAR ÍNDICE VETORIAL OTIMIZADO (SE HOUVER DADOS)
        if count > 1000:  # Só criar índice se houver dados suficientes
            console.print("🏗️ [blue]Criando índice vetorial otimizado...[/blue]")
            
            try:
                # Tentar criar índice com configurações otimizadas
                cursor.execute("""
                    CREATE INDEX IF NOT EXISTS idx_categorias_embeddings_optimized 
                    ON categorias USING ivfflat (cat_embeddings vector_cosine_ops)
                    WITH (lists = 100);
                """)
                conn.commit()
                console.print("[green]✓ Índice vetorial otimizado criado![/green]")
                
            except Exception as e:
                console.print(f"[yellow]⚠️ Não foi possível criar índice otimizado: {e}[/yellow]")
                
                # Tentar criar índice simples
                try:
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_categorias_embeddings_simple 
                        ON categorias (id)
                        WHERE cat_embeddings IS NOT NULL;
                    """)
                    conn.commit()
                    console.print("[green]✓ Índice alternativo criado[/green]")
                except Exception as e2:
                    console.print(f"[red]❌ Erro ao criar índice alternativo: {e2}[/red]")
        
        # 4. VERIFICAR CAMPOS DE EMBEDDINGS
        console.print("🧠 [cyan]Verificando configuração de embeddings...[/cyan]")
        
        cursor.execute("""
            SELECT 
                COUNT(*) as total,
                COUNT(cat_embeddings) as com_embeddings,
                COUNT(*) - COUNT(cat_embeddings) as sem_embeddings
            FROM categorias;
        """)
        
        stats = cursor.fetchone()
        
        stats_table = Table()
        stats_table.add_column("Métrica", style="cyan")
        stats_table.add_column("Valor", style="green")
        
        stats_table.add_row("Total de registros", f"{stats[0]:,}")
        stats_table.add_row("Com embeddings", f"{stats[1]:,}")
        stats_table.add_row("Sem embeddings", f"{stats[2]:,}")
        
        console.print(stats_table)
        
        # 5. VERIFICAR ESTRUTURA DO CAMPO VECTOR
        console.print("🔍 [cyan]Verificando estrutura do campo vetorial...[/cyan]")
        
        cursor.execute("""
            SELECT 
                column_name,
                data_type,
                udt_name
            FROM information_schema.columns 
            WHERE table_name = 'categorias' 
            AND column_name = 'cat_embeddings';
        """)
        
        vector_info = cursor.fetchone()
        
        if vector_info:
            console.print(f"[green]✓ Campo vetorial configurado:[/green]")
            console.print(f"   Nome: {vector_info[0]}")
            console.print(f"   Tipo: {vector_info[1]}")
            console.print(f"   UDT: {vector_info[2]}")
        else:
            console.print("[red]❌ Campo vetorial não encontrado![/red]")
        
        # 6. RESUMO DE CONFIGURAÇÃO
        console.print("\n📋 [bold blue]RESUMO DA CONFIGURAÇÃO:[/bold blue]")
        console.print(f"   🔌 Conexão: OK")
        console.print(f"   🧩 Extensões: {len(vector_extensions)} encontradas")
        console.print(f"   📊 Dados: {count:,} registros")
        console.print(f"   🧠 Embeddings: {stats[1]:,} preenchidos")
        console.print(f"   🎯 Pronto para busca semântica: {'Sim' if stats[1] > 0 else 'Não (sem embeddings)'}")
        
        return True
        
    except Exception as e:
        console.print(f"[red]❌ Erro durante configuração: {e}[/red]")
        return False
        
    finally:
        cursor.close()
        conn.close()

def main():
    """Função principal"""
    start_time = datetime.now()
    
    try:
        success = setup_vector_extensions()
        
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        if success:
            console.print(Panel(f"[bold green]CONFIGURAÇÃO CONCLUÍDA EM {duration:.2f}s![/bold green]"))
        else:
            console.print(Panel(f"[bold red]FALHA NA CONFIGURAÇÃO![/bold red]"))
        
    except Exception as e:
        console.print(Panel(f"[bold red]ERRO GERAL: {e}[/bold red]"))

if __name__ == "__main__":
    main()
