# GovGo V1 - Migração de Dados V0/DBL → V1 (CORRIGIDO - sem bugs de concorrência)
# Usa o mapeamento fiel de db/de_para_v0_v1.py

import os
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor, execute_values
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.prompt import Confirm
from rich.table import Table
from dotenv import load_dotenv
import time
from typing import List, Dict, Any


# Garante que o diretório pai (v1) está no sys.path para importar db corretamente
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from db.DEPARA_BDS0_BDS1 import DE_PARA, TRANSFORMATIONS

load_dotenv()
console = Console()

class DataMigrator:
    def __init__(self):
        self.dbl_connection = None
        self.v0_connection = None
        self.v1_connection = None
        self.stats = {k: 0 for k in DE_PARA.keys()}
        self.stats['errors'] = []
        self.unique_counters = {}  # Para gerar valores únicos

    def connect_databases(self):
        try:
            dbl_path = os.getenv("V0_SQLITE_PATH")
            if not os.path.exists(dbl_path):
                raise FileNotFoundError(f"SQLite não encontrado: {dbl_path}")
            self.dbl_connection = sqlite3.connect(dbl_path)
            self.dbl_connection.row_factory = sqlite3.Row
            console.print("✅ Conectado ao SQLite (DBL)")

            self.v0_connection = psycopg2.connect(
                host=os.getenv("SUPABASE_V0_HOST"),
                database=os.getenv("SUPABASE_V0_DBNAME"),
                user=os.getenv("SUPABASE_V0_USER"),
                password=os.getenv("SUPABASE_V0_PASSWORD"),
                port=int(os.getenv("SUPABASE_V0_PORT", "6543"))
            )
            console.print("✅ Conectado ao Supabase V0")

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
            console.print(f"❌ Erro ao conectar databases: {e}")
            return False

    def _reconnect_v1(self):
        """Reconecta ao banco V1 em caso de perda de conexão"""
        try:
            if self.v1_connection:
                self.v1_connection.close()
            self.v1_connection = psycopg2.connect(
                host=os.getenv("SUPABASE_HOST"),
                database=os.getenv("SUPABASE_DBNAME"),
                user=os.getenv("SUPABASE_USER"),
                password=os.getenv("SUPABASE_PASSWORD"),
                port=int(os.getenv("SUPABASE_PORT", "5432")),
                connect_timeout=30,
                options="-c statement_timeout=300000"  # 5 min timeout
            )
            console.print("🔄 Reconectado ao Supabase V1")
            return True
        except Exception as e:
            console.print(f"❌ Erro ao reconectar V1: {e}")
            return False

    def migrate_table(self, table_key: str, source: str, dest: str, campos: List, where: str = None, only_ids: List = None, batch_size: int = 100, max_workers: int = 8):
        """Migra uma tabela usando o de-para - VERSÃO CORRIGIDA COM RETOMADA"""
        
        # Primeiro, contar registros na origem
        if source == 'v0':
            conn = self.v0_connection
            cursor_src = conn.cursor(cursor_factory=RealDictCursor)
        else:
            conn = self.dbl_connection
            cursor_src = conn.cursor()

        src_fields = [c[0] for c in campos]
        dest_fields = [c[1] for c in campos]
        where_clause = f" WHERE {where}" if where else ""

        cursor_src.execute(f"SELECT COUNT(*) AS count FROM {DE_PARA[table_key]['origem']}{where_clause}")
        total_rows_row = cursor_src.fetchone()
        total_rows = total_rows_row.get('count', 0) if isinstance(total_rows_row, dict) else total_rows_row[0]
        
        if total_rows == 0:
            console.print(f"⚠️ Nenhum registro encontrado em {DE_PARA[table_key]['origem']}")
            return 0

        console.print(f"📊 {total_rows} registros encontrados para migração")
        
        # Verificar se já existem registros na tabela destino
        try:
            cursor_dest = self.v1_connection.cursor()
            cursor_dest.execute(f"SELECT COUNT(*) AS count FROM {dest}")
            already_inserted = cursor_dest.fetchone()[0]
        except psycopg2.OperationalError as e:
            console.print(f"⚠️ Conexão perdida, tentando reconectar: {e}")
            if self._reconnect_v1():
                cursor_dest = self.v1_connection.cursor()
                cursor_dest.execute(f"SELECT COUNT(*) AS count FROM {dest}")
                already_inserted = cursor_dest.fetchone()[0]
            else:
                console.print("❌ Falha na reconexão. Abortando migração.")
                return 0
        
        if already_inserted > 0:
            console.print(f"⚠️ Tabela {dest} já possui {already_inserted} registros.")
            
            # VERIFICAR SE MIGRAÇÃO JÁ ESTÁ COMPLETA
            if already_inserted >= total_rows:
                console.print(f"✅ Migração de {dest} já está completa ({already_inserted}/{total_rows})")
                return already_inserted
            
            resume = Confirm.ask(f"Deseja retomar a migração de onde parou?")
            if resume:
                console.print(f"🔄 Retomando migração de {dest} (usará ON CONFLICT DO NOTHING para ignorar duplicatas)")
                # COM ON CONFLICT DO NOTHING, sempre começamos do 0 e deixamos o PostgreSQL resolver
                start_offset = 0
            else:
                if Confirm.ask(f"Deseja sobrescrever os dados existentes em {dest}?"):
                    # SÓ AGORA limpa se o usuário confirmar sobrescrita
                    cursor_dest.execute(f"DELETE FROM {dest}")
                    self.v1_connection.commit()
                    console.print(f"🗑️ Tabela {dest} limpa para sobrescrita")
                    already_inserted = 0
                    start_offset = 0
                else:
                    console.print(f"⏭️ Pulando migração de {dest}")
                    return already_inserted  # Retorna o que já tem ao invés de 0
        else:
            already_inserted = 0
            start_offset = 0
        
        # COM ON CONFLICT DO NOTHING, sempre processamos todos os registros
        # O PostgreSQL ignora duplicatas automaticamente
        remaining_rows = total_rows
        
        if remaining_rows <= 0:
            console.print(f"✅ Nenhum registro para migrar em {dest}")
            return already_inserted
            
        console.print(f"🔄 Processando todos os {total_rows} registros (duplicatas serão ignoradas)")
        
        migrated = 0
        cursor_dest = self.v1_connection.cursor()
        
        with Progress(SpinnerColumn(), BarColumn(), TaskProgressColumn(), TextColumn("{task.description}")) as progress:
            task = progress.add_task(f"Migrando {table_key}", total=remaining_rows)
            
            # MIGRAÇÃO PARALELA CORRETA - SEM COMPARTILHAR CURSORS
            from concurrent.futures import ThreadPoolExecutor, as_completed
            import threading
            
            current_batch_size = min(batch_size, 100)  # Limite máximo de 100 para evitar timeouts
            batches = []
            
            # Preparar todos os batches primeiro
            offset = start_offset
            batch_num = 1
            
            # Definir ordenação baseada na tabela
            order_clause = ""
            if table_key in ['item_contratacao', 'item_classificacao']:
                if source == 'v0':
                    order_clause = " ORDER BY numeroItem"
                else:
                    order_clause = " ORDER BY numeroItem"
            
            while offset < total_rows:
                # Sintaxe diferente para SQLite e PostgreSQL
                if source == 'v0':
                    # PostgreSQL sintaxe: LIMIT limit OFFSET offset
                    query = f"SELECT {', '.join(src_fields)} FROM {DE_PARA[table_key]['origem']}{where_clause}{order_clause} LIMIT {current_batch_size} OFFSET {offset}"
                else:
                    # SQLite sintaxe: LIMIT offset, limit
                    query = f"SELECT {', '.join(src_fields)} FROM {DE_PARA[table_key]['origem']}{where_clause}{order_clause} LIMIT {offset}, {current_batch_size}"
                batches.append((batch_num, offset, query, current_batch_size))
                offset += current_batch_size
                batch_num += 1
            
            # Executar em paralelo com conexões independentes
            with ThreadPoolExecutor(max_workers=min(max_workers, 2)) as executor:  # Máximo 2 workers
                future_to_batch = {}
                
                for batch_info in batches:
                    future = executor.submit(self._process_batch_parallel, batch_info, source, dest, dest_fields, src_fields, table_key)
                    future_to_batch[future] = batch_info
                
                # Processar resultados conforme completam
                for future in as_completed(future_to_batch):
                    batch_info = future_to_batch[future]
                    batch_num, offset, query, batch_size = batch_info
                    
                    try:
                        batch_migrated = future.result()
                        if batch_migrated > 0:
                            migrated += batch_migrated
                            self.stats[table_key] += batch_migrated
                            progress.update(task, advance=batch_migrated)
                            console.print(f"✅ Batch {batch_num}: {batch_migrated} registros processados")
                    except Exception as e:
                        console.print(f"❌ Erro no batch {batch_num}: {e}")

        # Contar registros REAIS inseridos na tabela
        try:
            cursor_dest.execute(f"SELECT COUNT(*) AS count FROM {dest}")
            final_count = cursor_dest.fetchone()[0]
        except psycopg2.OperationalError as e:
            console.print(f"⚠️ Conexão perdida na contagem final, tentando reconectar: {e}")
            if self._reconnect_v1():
                cursor_dest = self.v1_connection.cursor()
                cursor_dest.execute(f"SELECT COUNT(*) AS count FROM {dest}")
                final_count = cursor_dest.fetchone()[0]
            else:
                console.print("❌ Falha na reconexão final. Usando contagem estimada.")
                final_count = already_inserted + migrated
        actual_migrated = final_count - already_inserted
        
        console.print(f"✅ {migrated} registros processados, {actual_migrated} efetivamente inseridos em {dest} (total: {final_count})")
        return final_count

    def _process_batch_parallel(self, batch_info, source, dest, dest_fields, src_fields, table_key):
        """Processa um batch em paralelo com conexões independentes"""
        batch_num, offset, query, batch_size = batch_info
        
        try:
            # Criar conexões independentes para este thread
            if source == 'v0':
                conn_src = psycopg2.connect(
                    host=os.getenv("SUPABASE_V0_HOST"),
                    database=os.getenv("SUPABASE_V0_DBNAME"),
                    user=os.getenv("SUPABASE_V0_USER"),
                    password=os.getenv("SUPABASE_V0_PASSWORD"),
                    port=int(os.getenv("SUPABASE_V0_PORT", "6543"))
                )
                cursor_src = conn_src.cursor(cursor_factory=RealDictCursor)
            else:
                conn_src = sqlite3.connect(os.getenv("V0_SQLITE_PATH"))
                conn_src.row_factory = sqlite3.Row
                cursor_src = conn_src.cursor()
                
            conn_dest = psycopg2.connect(
                host=os.getenv("SUPABASE_HOST"),
                database=os.getenv("SUPABASE_DBNAME"),
                user=os.getenv("SUPABASE_USER"),
                password=os.getenv("SUPABASE_PASSWORD"),
                port=int(os.getenv("SUPABASE_PORT", "5432"))
            )
            cursor_dest = conn_dest.cursor()
            
            # Buscar dados
            cursor_src.execute(query)
            rows = cursor_src.fetchall()
            
            if rows:
                # Inserir dados
                self._insert_batch_worker(cursor_dest, dest, dest_fields, rows, src_fields)
                conn_dest.commit()
                
                # Fechar conexões
                cursor_src.close()
                conn_src.close()
                cursor_dest.close()
                conn_dest.close()
                
                return len(rows)
            else:
                # Fechar conexões mesmo sem dados
                cursor_src.close()
                conn_src.close()
                cursor_dest.close()
                conn_dest.close()
                return 0
                
        except Exception as e:
            # Garantir fechamento das conexões em caso de erro
            try:
                cursor_src.close()
                conn_src.close()
                cursor_dest.close()
                conn_dest.close()
            except:
                pass
            raise e

    def _insert_batch_worker(self, cursor, table, fields, rows, src_fields):
        """Inserção de batch sequencial COM TRANSFORMAÇÕES AUTOMÁTICAS DE TIPO"""
        if not rows:
            return
            
        # Encontrar campos com transformações
        current_table_key = None
        for table_key, table_info in DE_PARA.items():
            if table_info['destino'] == table:
                current_table_key = table_key
                break
        
        # Criar mapeamento de transformações baseado no DE_PARA
        field_transformations = {}
        if current_table_key:
            for campo_info in DE_PARA[current_table_key]['campos']:
                if len(campo_info) == 3:  # Tem transformação
                    src_field, dest_field, transform_type = campo_info
                    field_transformations[src_field] = TRANSFORMATIONS.get(transform_type)
        
        # Criar mapeamento src -> dest
        field_mapping = dict(zip(src_fields, fields))
        
        # Adaptar dados para inserção
        import json
        
        def safe_json_convert(val):
            """Converte valores de forma segura para inserção no PostgreSQL"""
            if isinstance(val, dict):
                return json.dumps(val, ensure_ascii=False)
            elif val is None:
                return None
            else:
                return val
        
        def row_to_tuple(row):
            if isinstance(row, dict):
                result = []
                for src_field, dest_field in field_mapping.items():
                    val = row.get(src_field)
                    
                    # Aplicar transformação se existir
                    if src_field in field_transformations and field_transformations[src_field]:
                        val = field_transformations[src_field](val)
                    # Fallback para campos conhecidos sem transformação explícita
                    elif val == '' or val is None:
                        if dest_field in ['cod_nv1', 'cod_nv2', 'cod_nv3', 'orcamento_sigiloso_codigo']:
                            val = None  # NULL para integer
                        elif dest_field in ['valor_total_homologado', 'score', 'confidence', 'valor_unitario_estimado', 'valor_total_estimado', 'quantidade_item'] or dest_field.startswith('score_'):
                            val = None  # NULL para decimal
                        elif dest_field == 'existe_resultado':
                            val = None  # NULL para boolean
                        else:
                            val = val  # Manter como está para text
                    
                    result.append(safe_json_convert(val))
                return tuple(result)
                
            elif isinstance(row, sqlite3.Row):
                result = []
                for src_field, dest_field in field_mapping.items():
                    try:
                        val = row[src_field]
                        
                        # Aplicar transformação se existir
                        if src_field in field_transformations and field_transformations[src_field]:
                            val = field_transformations[src_field](val)
                        # Fallback para campos conhecidos
                        elif val == '' or val is None:
                            if dest_field in ['cod_nv1', 'cod_nv2', 'cod_nv3', 'orcamento_sigiloso_codigo']:
                                val = None
                            elif dest_field in ['valor_total_homologado', 'score', 'confidence', 'valor_unitario_estimado', 'valor_total_estimado', 'quantidade_item'] or dest_field.startswith('score_'):
                                val = None
                            elif dest_field == 'existe_resultado':
                                val = None
                            else:
                                val = val
                        
                        result.append(safe_json_convert(val))
                    except (IndexError, KeyError):
                        # Campo não existe na row - usar NULL/valor padrão
                        if dest_field in ['cod_nv1', 'cod_nv2', 'cod_nv3', 'orcamento_sigiloso_codigo']:
                            result.append(None)
                        elif dest_field in ['valor_total_homologado', 'score', 'confidence']:
                            result.append(None)
                        else:
                            result.append('')
                return tuple(result)
            else:
                # Fallback para outros tipos
                return tuple(safe_json_convert(v) if v is not None else None for v in row)
        
        data = [row_to_tuple(row) for row in rows]
        
        # Usar INSERT com ON CONFLICT DO NOTHING para ignorar duplicatas
        # Isso permite retomar migrações sem erros de chave duplicada
        insert_sql = f"INSERT INTO {table} ({', '.join(fields)}) VALUES %s ON CONFLICT DO NOTHING"
        execute_values(cursor, insert_sql, data, page_size=100)

    def run(self):
        console.print(Panel.fit("[bold blue]GovGo V1 - Migração de Dados (VERSÃO CORRIGIDA)[/bold blue]", title="🔄 Migração V0/DBL → V1"))
        if not self.connect_databases():
            return
        start = time.time()

        # Steps com parâmetros otimizados para VELOCIDADE
        steps = [
            ("categoria", lambda: self.migrate_table('categoria', 'v0', 'categoria', DE_PARA['categoria']['campos'], None, None, 200, 8)),
            ("contratacoes_embeddings", lambda: self.migrate_table('contratacoes_embeddings', 'v0', 'contratacao_emb', DE_PARA['contratacoes_embeddings']['campos'], None, None, 100, 8)),
            ("contratacao", None),
            ("item_contratacao", None),
            ("item_classificacao", None)
        ]

        for idx, (step_name, step_func) in enumerate(steps):
            console.rule(f"[bold yellow]Passo {idx+1}: {step_name}")
            
            if step_func is not None:
                result = step_func()
                self._show_step_result(step_name, result)
            else:
                # Passos dependentes de dados migrados
                if step_name == "contratacao":
                    # Buscar IDs dos embeddings para filtrar contratações
                    try:
                        cursor_v1 = self.v1_connection.cursor()
                        cursor_v1.execute("SELECT numero_controle_pncp FROM contratacao_emb")
                        migrated_emb_contratos = [row[0] for row in cursor_v1.fetchall()]
                    except psycopg2.OperationalError as e:
                        console.print(f"⚠️ Conexão perdida ao buscar embeddings, tentando reconectar: {e}")
                        if self._reconnect_v1():
                            cursor_v1 = self.v1_connection.cursor()
                            cursor_v1.execute("SELECT numero_controle_pncp FROM contratacao_emb")
                            migrated_emb_contratos = [row[0] for row in cursor_v1.fetchall()]
                        else:
                            console.print("❌ Falha na reconexão. Pulando contratações.")
                            migrated_emb_contratos = []
                    
                    if migrated_emb_contratos:
                        console.print(f"📋 {len(migrated_emb_contratos)} contratações com embeddings encontradas")
                        # Criar WHERE clause para filtrar por IDs
                        ids_str = "','".join(migrated_emb_contratos)
                        where_clause = f"numeroControlePNCP IN ('{ids_str}')"
                        result = self.migrate_table('contratacao', 'dbl', 'contratacao', DE_PARA['contratacao']['campos'], where_clause, None, 200, 6)
                        self._show_step_result(step_name, result)
                    else:
                        console.print("⚠️ Nenhum embedding encontrado. Pulando contratações.")
                        
                elif step_name == "item_contratacao":
                    # Usar IDs REALMENTE presentes na tabela contratacao migrada
                    try:
                        cursor_v1 = self.v1_connection.cursor()
                        cursor_v1.execute("SELECT numero_controle_pncp FROM contratacao")
                        migrated_contratos = [row[0] for row in cursor_v1.fetchall()]
                    except psycopg2.OperationalError as e:
                        console.print(f"⚠️ Conexão perdida ao buscar contratações, tentando reconectar: {e}")
                        if self._reconnect_v1():
                            cursor_v1 = self.v1_connection.cursor()
                            cursor_v1.execute("SELECT numero_controle_pncp FROM contratacao")
                            migrated_contratos = [row[0] for row in cursor_v1.fetchall()]
                        else:
                            console.print("❌ Falha na reconexão. Pulando itens de contratação.")
                            migrated_contratos = []
                    
                    if migrated_contratos:
                        console.print(f"📋 {len(migrated_contratos)} contratações realmente migradas encontradas")
                        ids_str = "','".join(migrated_contratos)
                        where_clause = f"numeroControlePNCP IN ('{ids_str}')"
                        result = self.migrate_table('item_contratacao', 'dbl', 'item_contratacao', DE_PARA['item_contratacao']['campos'], where_clause, None, 100, 2)
                        self._show_step_result(step_name, result)
                    else:
                        console.print("⚠️ Nenhuma contratação migrada. Pulando itens de contratação.")
                        
                elif step_name == "item_classificacao":
                    # Usar IDs REALMENTE presentes na tabela contratacao migrada
                    try:
                        cursor_v1 = self.v1_connection.cursor()
                        cursor_v1.execute("SELECT numero_controle_pncp FROM contratacao")
                        migrated_contratos = [row[0] for row in cursor_v1.fetchall()]
                    except psycopg2.OperationalError as e:
                        console.print(f"⚠️ Conexão perdida ao buscar contratações, tentando reconectar: {e}")
                        if self._reconnect_v1():
                            cursor_v1 = self.v1_connection.cursor()
                            cursor_v1.execute("SELECT numero_controle_pncp FROM contratacao")
                            migrated_contratos = [row[0] for row in cursor_v1.fetchall()]
                        else:
                            console.print("❌ Falha na reconexão. Pulando classificações.")
                            migrated_contratos = []
                    
                    if migrated_contratos:
                        console.print(f"📋 {len(migrated_contratos)} contratações realmente migradas encontradas")
                        ids_str = "','".join(migrated_contratos)
                        where_clause = f"numeroControlePNCP IN ('{ids_str}')"
                        result = self.migrate_table('item_classificacao', 'dbl', 'item_classificacao', DE_PARA['item_classificacao']['campos'], where_clause, None, 100, 2)
                        self._show_step_result(step_name, result)
                    else:
                        console.print("⚠️ Nenhuma contratação migrada. Pulando classificações.")

            # Confirmação para continuar
            if idx < len(steps) - 1:  # Não perguntar no último step
                if not Confirm.ask(f"Deseja continuar para o próximo passo?"):
                    console.print("[bold red]Execução interrompida pelo usuário.")
                    break

        elapsed = time.time() - start
        console.print(f"\n🎉 [bold green]Migração concluída! Tempo total: {elapsed:.1f}s[/bold green]")
        
        # Relatório final
        table = Table(title="📊 Relatório de Migração")
        table.add_column("Tabela", style="cyan")
        table.add_column("Registros migrados", style="green")
        
        for k, v in self.stats.items():
            if k != 'errors' and v > 0:
                table.add_row(k, str(v))
        console.print(table)
        
        if self.stats['errors']:
            console.print(f"❌ Erros: {self.stats['errors']}")

        # Fechar conexões principais
        if self.dbl_connection:
            self.dbl_connection.close()
        if self.v0_connection:
            self.v0_connection.close()
        if self.v1_connection:
            self.v1_connection.close()

    def _show_step_result(self, step_name, result):
        table = Table(title=f"✅ Resultado: {step_name}")
        table.add_column("Tabela", style="cyan")
        table.add_column("Registros migrados", style="green")
        table.add_row(step_name, str(result))
        console.print(table)

def main():
    migrator = DataMigrator()
    migrator.run()

if __name__ == "__main__":
    main()
