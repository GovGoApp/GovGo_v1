# GovGo V1 - Remoção de Duplicatas
# Remove registros duplicados das tabelas migradas

import os
import psycopg2
from psycopg2.extras import RealDictCursor
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.prompt import Confirm
from rich.table import Table
from dotenv import load_dotenv
import time

load_dotenv()
console = Console()

class DuplicateRemover:
    def __init__(self):
        self.v1_connection = None
        self.stats = {}

    def connect_database(self):
        try:
            self.v1_connection = psycopg2.connect(
                host=os.getenv("SUPABASE_HOST"),
                database=os.getenv("SUPABASE_DBNAME"),
                user=os.getenv("SUPABASE_USER"),
                password=os.getenv("SUPABASE_PASSWORD"),
                port=int(os.getenv("SUPABASE_PORT", "5432"))
            )
            console.print("✅ Conectado ao Supabase V1")
            return True
        except Exception as e:
            console.print(f"❌ Erro ao conectar database: {e}")
            return False

    def analyze_duplicates(self, table_name, primary_keys):
        """Analisa duplicatas em uma tabela"""
        cursor = self.v1_connection.cursor(cursor_factory=RealDictCursor)
        
        # Construir query para encontrar duplicatas
        pk_fields = ", ".join(primary_keys)
        
        # Query para contar duplicatas
        query = f"""
        SELECT {pk_fields}, COUNT(*) as duplicate_count
        FROM {table_name}
        GROUP BY {pk_fields}
        HAVING COUNT(*) > 1
        ORDER BY duplicate_count DESC
        """
        
        cursor.execute(query)
        duplicates = cursor.fetchall()
        
        if duplicates:
            console.print(f"⚠️ Encontradas {len(duplicates)} chaves duplicadas em {table_name}")
            
            # Mostrar alguns exemplos
            for i, dup in enumerate(duplicates[:5]):  # Mostrar apenas 5 primeiros
                keys_str = ", ".join([f"{k}: {dup[k]}" for k in primary_keys])
                console.print(f"  📋 {keys_str} → {dup['duplicate_count']} registros")
            
            if len(duplicates) > 5:
                console.print(f"  ... e mais {len(duplicates) - 5} duplicatas")
                
            return duplicates
        else:
            console.print(f"✅ Nenhuma duplicata encontrada em {table_name}")
            return []

    def remove_duplicates(self, table_name, primary_keys):
        """Remove duplicatas mantendo apenas o primeiro registro de cada grupo"""
        cursor = self.v1_connection.cursor()
        
        # Primeiro, analisar duplicatas
        duplicates = self.analyze_duplicates(table_name, primary_keys)
        
        if not duplicates:
            return 0
            
        if not Confirm.ask(f"Deseja remover as duplicatas de {table_name}?"):
            console.print(f"⏭️ Pulando remoção de duplicatas em {table_name}")
            return 0
        
        # Construir WHERE clause para chaves primárias
        pk_conditions = " AND ".join([f"t1.{pk} = t2.{pk}" for pk in primary_keys])
        
        # Query para remover duplicatas (mantém o registro com menor ctid - PostgreSQL row identifier)
        query = f"""
        DELETE FROM {table_name} t1
        USING {table_name} t2
        WHERE {pk_conditions}
        AND t1.ctid > t2.ctid
        """
        
        console.print(f"🧹 Removendo duplicatas de {table_name}...")
        
        try:
            cursor.execute(query)
            removed_count = cursor.rowcount
            self.v1_connection.commit()
            
            console.print(f"✅ Removidos {removed_count} registros duplicados de {table_name}")
            return removed_count
            
        except Exception as e:
            console.print(f"❌ Erro ao remover duplicatas de {table_name}: {e}")
            self.v1_connection.rollback()
            return 0

    def get_table_count(self, table_name):
        """Conta registros em uma tabela"""
        cursor = self.v1_connection.cursor()
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        return cursor.fetchone()[0]

    def run(self):
        console.print(Panel.fit("[bold red]GovGo V1 - Remoção de Duplicatas[/bold red]", title="🧹 Limpeza de Dados"))
        
        if not self.connect_database():
            return
            
        # Definir tabelas e suas chaves primárias
        tables_to_clean = [
            ("categoria", ["codigo"]),
            ("contratacao_emb", ["numero_controle_pncp"]),
            ("contratacao", ["numero_controle_pncp"]),
            ("item_contratacao", ["numero_controle_pncp", "numero_item"]),  # Chave composta
            ("item_classificacao", ["numero_controle_pncp", "numero_item"])  # Chave composta
        ]
        
        total_removed = 0
        
        console.print("\n📊 **Análise Inicial de Registros:**")
        initial_counts = {}
        for table_name, _ in tables_to_clean:
            try:
                count = self.get_table_count(table_name)
                initial_counts[table_name] = count
                console.print(f"  📋 {table_name}: {count:,} registros")
            except Exception as e:
                console.print(f"  ❌ Erro ao contar {table_name}: {e}")
                initial_counts[table_name] = 0
        
        console.print("\n🔍 **Detectando e Removendo Duplicatas:**")
        
        for table_name, primary_keys in tables_to_clean:
            console.rule(f"[bold yellow]Limpando: {table_name}")
            
            try:
                removed = self.remove_duplicates(table_name, primary_keys)
                total_removed += removed
                self.stats[table_name] = {
                    'initial': initial_counts[table_name],
                    'removed': removed,
                    'final': self.get_table_count(table_name)
                }
                
            except Exception as e:
                console.print(f"❌ Erro ao processar {table_name}: {e}")
                self.stats[table_name] = {
                    'initial': initial_counts[table_name],
                    'removed': 0,
                    'final': initial_counts[table_name],
                    'error': str(e)
                }
        
        # Relatório final
        console.print(f"\n🎉 **Limpeza Concluída!**")
        console.print(f"📊 Total de duplicatas removidas: {total_removed:,}")
        
        # Tabela de resultados
        table = Table(title="📋 Relatório de Limpeza")
        table.add_column("Tabela", style="cyan")
        table.add_column("Inicial", style="blue")
        table.add_column("Removidos", style="red")
        table.add_column("Final", style="green")
        table.add_column("Status", style="yellow")
        
        for table_name, stats in self.stats.items():
            if 'error' in stats:
                status = "❌ Erro"
            elif stats['removed'] > 0:
                status = "✅ Limpo"
            else:
                status = "✅ Sem duplicatas"
                
            table.add_row(
                table_name,
                f"{stats['initial']:,}",
                f"{stats['removed']:,}",
                f"{stats['final']:,}",
                status
            )
        
        console.print(table)
        
        # Fechar conexão
        if self.v1_connection:
            self.v1_connection.close()

def main():
    remover = DuplicateRemover()
    remover.run()

if __name__ == "__main__":
    main()
