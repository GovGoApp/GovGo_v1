#!/usr/bin/env python3
"""
GovGo V1 - Testes de Migração
=============================
Valida estrutura e compatibilidade antes da migração
Baseado nas estruturas reais do 01_setup_database.py
"""

import os
import sys
import logging
from typing import Dict, List, Any
from decimal import Decimal
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Carregar variáveis do .env
load_dotenv()

# Adicionar o diretório pai ao path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from db.table_schemas import get_table_schema, get_insertable_columns, get_test_data, generate_insert_query, validate_data_types
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel

console = Console()

class MigrationTester:
    def __init__(self):
        self.connection = None
        self.tests_passed = 0
        self.tests_failed = 0
        
    def connect_database(self):
        """Conecta ao banco de dados V1"""
        try:
            self.connection = psycopg2.connect(
                host=os.getenv("SUPABASE_HOST"),
                database=os.getenv("SUPABASE_DBNAME"),
                user=os.getenv("SUPABASE_USER"),
                password=os.getenv("SUPABASE_PASSWORD"),
                port=int(os.getenv("SUPABASE_PORT", "6543"))
            )
            console.print("[green]✓[/green] Conexão com banco V1 estabelecida")
            return True
        except Exception as e:
            console.print(f"[red]✗[/red] Erro de conexão: {str(e)}")
            return False
    
    def test_database_structure(self):
        """Testa a estrutura das tabelas"""
        console.print("\n[bold blue]TESTE 1: Verificação da Estrutura do Banco[/bold blue]")
        
        expected_tables = [
            'categoria', 'contratacao', 'contrato', 'item_contratacao',
            'item_classificacao', 'contratacao_emb', 'contrato_emb', 'ata_preco', 'pca'
        ]
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Verificando tabelas...", total=len(expected_tables))
            
            existing_tables = []
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            
            for table in expected_tables:
                query = """
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = %s
                """
                cursor.execute(query, (table,))
                result = cursor.fetchall()
                
                if result:
                    existing_tables.append(table)
                    console.print(f"  [green]✓[/green] Tabela '{table}' encontrada")
                    self.tests_passed += 1
                else:
                    console.print(f"  [red]✗[/red] Tabela '{table}' não encontrada")
                    self.tests_failed += 1
                
                progress.advance(task)
            
            cursor.close()
        
        return len(existing_tables) == len(expected_tables)
    
    def test_vector_extension(self):
        """Testa se a extensão pgvector está instalada"""
        console.print("\n[bold blue]TESTE 2: Verificação da Extensão pgvector[/bold blue]")
        
        cursor = self.connection.cursor(cursor_factory=RealDictCursor)
        query = "SELECT extname FROM pg_extension WHERE extname = 'vector'"
        cursor.execute(query)
        result = cursor.fetchall()
        cursor.close()
        
        if result:
            console.print("[green]✓[/green] Extensão pgvector instalada")
            self.tests_passed += 1
            return True
        else:
            console.print("[red]✗[/red] Extensão pgvector não encontrada")
            self.tests_failed += 1
            return False
    
    def test_table_columns(self):
        """Testa as colunas das tabelas principais usando schemas reais"""
        console.print("\n[bold blue]TESTE 3: Verificação das Colunas (Baseado no 01_setup_database.py)[/bold blue]")
        
        test_tables = ['categoria', 'contratacao', 'contratacao_emb', 'item_contratacao']
        
        all_passed = True
        cursor = self.connection.cursor(cursor_factory=RealDictCursor)
        
        for table_name in test_tables:
            console.print(f"\n  Verificando tabela '{table_name}':")
            
            # Obter esquema esperado
            schema = get_table_schema(table_name)
            if not schema:
                console.print(f"    [yellow]⚠[/yellow] Esquema para '{table_name}' não definido")
                continue
                
            expected_columns = [col['name'] for col in schema['columns']]
            
            # Consultar colunas reais
            query = """
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = %s AND table_schema = 'public'
                ORDER BY ordinal_position
            """
            cursor.execute(query, (table_name,))
            columns = cursor.fetchall()
            existing_columns = [col['column_name'] for col in columns]
            
            # Verificar cada coluna esperada
            for col in expected_columns:
                if col in existing_columns:
                    console.print(f"    [green]✓[/green] Coluna '{col}' encontrada")
                    self.tests_passed += 1
                else:
                    console.print(f"    [red]✗[/red] Coluna '{col}' não encontrada")
                    self.tests_failed += 1
                    all_passed = False
        
        cursor.close()
        return all_passed
    
    def test_sample_insertions(self):
        """Testa inserções usando dados de teste das estruturas reais"""
        console.print("\n[bold blue]TESTE 4: Verificação de Inserções (Baseado no 01_setup_database.py)[/bold blue]")
        
        test_tables = ['categoria', 'contratacao', 'contratacao_emb', 'item_contratacao']
        
        try:
            inserted_keys = []  # Para rastrear dados inseridos para limpeza
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            
            for table_name in test_tables:
                console.print(f"\n  Testando inserção em '{table_name}':")
                
                # Obter dados de teste
                test_data = get_test_data(table_name)
                if not test_data:
                    console.print(f"    [yellow]⚠[/yellow] Dados de teste não definidos para '{table_name}'")
                    continue
                
                # Validar tipos de dados
                if not validate_data_types(table_name, test_data):
                    console.print(f"    [red]✗[/red] Tipos de dados inválidos para '{table_name}'")
                    self.tests_failed += 1
                    continue
                
                # Gerar query de inserção
                insert_query = generate_insert_query(table_name)
                if not insert_query:
                    console.print(f"    [yellow]⚠[/yellow] Não foi possível gerar query para '{table_name}'")
                    continue
                
                # Executar inserção
                try:
                    cursor.execute(insert_query, test_data)
                    self.connection.commit()
                    console.print(f"    [green]✓[/green] Inserção em '{table_name}' bem-sucedida")
                    self.tests_passed += 1
                    
                    # Rastrear para limpeza
                    if table_name == 'categoria':
                        inserted_keys.append(('categoria', 'codcat', test_data[0]))  # codcat
                    elif table_name == 'contratacao':
                        inserted_keys.append(('contratacao', 'numerocontrolepncp', test_data[0]))  # numerocontrolepncp
                    elif table_name == 'contratacao_emb':
                        inserted_keys.append(('contratacao_emb', 'numerocontrolepncp', test_data[0]))  # numerocontrolepncp
                    elif table_name == 'item_contratacao':
                        inserted_keys.append(('item_contratacao', 'numerocontrolepncp', test_data[0]))  # numerocontrolepncp
                        
                except Exception as e:
                    console.print(f"    [red]✗[/red] Erro na inserção em '{table_name}': {str(e)}")
                    self.tests_failed += 1
            
            # Limpeza dos dados de teste (ordem reversa para respeitar FKs)
            console.print("\n  Removendo dados de teste:")
            for table_name, column, value in reversed(inserted_keys):
                try:
                    cursor.execute(f"DELETE FROM {table_name} WHERE {column} = %s", (value,))
                    self.connection.commit()
                    console.print(f"    [green]✓[/green] Dados removidos de '{table_name}'")
                except Exception as e:
                    console.print(f"    [yellow]⚠[/yellow] Erro ao remover de '{table_name}': {str(e)}")
            
            cursor.close()
            return self.tests_failed == 0
            
        except Exception as e:
            console.print(f"[red]✗[/red] Erro geral na inserção: {str(e)}")
            self.tests_failed += 1
            return False
    
    def test_embedding_readiness(self):
        """Testa se o sistema está pronto para embeddings"""
        console.print("\n[bold blue]TESTE 5: Verificação de Prontidão para Embeddings[/bold blue]")
        
        # Verificar se há dados na tabela contratacoes_embeddings (V0)
        try:
            cursor = self.connection.cursor(cursor_factory=RealDictCursor)
            
            # Descobrir o nome real da tabela de embeddings V0
            query = """
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name LIKE '%embedding%'
            """
            cursor.execute(query)
            embedding_tables = cursor.fetchall()
            
            if embedding_tables:
                for table in embedding_tables:
                    table_name = table['table_name']
                    count_query = f"SELECT COUNT(*) as total FROM {table_name}"
                    cursor.execute(count_query)
                    result = cursor.fetchone()
                    count = result['total'] if result else 0
                    
                    console.print(f"  [blue]ℹ[/blue] Tabela '{table_name}': {count:,} registros")
                    if count > 0:
                        self.tests_passed += 1
                    else:
                        console.print(f"    [yellow]⚠[/yellow] Tabela vazia")
                        
            else:
                console.print("[yellow]⚠[/yellow] Nenhuma tabela de embeddings encontrada no V0")
            
            cursor.close()    
            return True
            
        except Exception as e:
            console.print(f"[red]✗[/red] Erro ao verificar embeddings: {str(e)}")
            self.tests_failed += 1
            return False
    
    def generate_test_report(self):
        """Gera relatório final dos testes"""
        console.print("\n" + "="*60)
        console.print("[bold]RELATÓRIO DE TESTES DE MIGRAÇÃO[/bold]")
        console.print("="*60)
        
        total_tests = self.tests_passed + self.tests_failed
        success_rate = (self.tests_passed / total_tests * 100) if total_tests > 0 else 0
        
        # Tabela de resultados
        table = Table(title="Resultados dos Testes")
        table.add_column("Métrica", style="cyan")
        table.add_column("Valor", style="magenta")
        
        table.add_row("Testes Executados", str(total_tests))
        table.add_row("Testes Aprovados", f"[green]{self.tests_passed}[/green]")
        table.add_row("Testes Falharam", f"[red]{self.tests_failed}[/red]")
        table.add_row("Taxa de Sucesso", f"{success_rate:.1f}%")
        
        console.print(table)
        
        # Status geral
        if self.tests_failed == 0:
            status = Panel(
                "[green]✓ SISTEMA PRONTO PARA MIGRAÇÃO[/green]\n"
                "Todas as verificações passaram com sucesso!",
                title="Status Final",
                border_style="green"
            )
        else:
            status = Panel(
                f"[red]✗ SISTEMA NÃO ESTÁ PRONTO[/red]\n"
                f"{self.tests_failed} teste(s) falharam. Verifique os problemas acima.",
                title="Status Final",
                border_style="red"
            )
        
        console.print(status)
        
        return self.tests_failed == 0
    
    def close(self):
        """Fecha a conexão com o banco"""
        if self.connection:
            self.connection.close()

def main():
    """Função principal"""
    console.print(Panel(
        "[bold blue]GovGo V1 - Testes de Migração[/bold blue]\n"
        "Validação pré-migração usando estruturas reais",
        title="Sistema de Testes",
        border_style="blue"
    ))
    
    tester = MigrationTester()
    
    try:
        # Conectar ao banco
        if not tester.connect_database():
            return
        
        # Executar testes
        tester.test_database_structure()
        tester.test_vector_extension()
        tester.test_table_columns()
        tester.test_sample_insertions()
        tester.test_embedding_readiness()
        
        # Relatório final
        tester.generate_test_report()
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Testes interrompidos pelo usuário[/yellow]")
    except Exception as e:
        console.print(f"\n[red]Erro fatal: {str(e)}[/red]")
    finally:
        tester.close()

if __name__ == "__main__":
    main()
