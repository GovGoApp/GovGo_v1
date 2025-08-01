# GovGo V1 - Migração de Dados V0_OLD/DBL → V1 (dados antigos da v0_old)
# Usa o mapeamento fiel de db/de_para_v0_v1.py e puxa dados da database v0_old

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
from db.de_para_v0_v1 import DE_PARA

load_dotenv()
console = Console()

class DataMigratorV0Old:
    def __init__(self):
        self.dbl_connection = None
        self.v0_old_connection = None  # Mudança: usar v0_old em vez de v0
        self.v1_connection = None
        self.stats = {k: 0 for k in DE_PARA.keys()}
        self.stats['errors'] = []
        self.numerocontrolepncp_list = []
        self.unique_counters = {}  # Para gerar valores únicos

    def connect_databases(self):
        try:
            dbl_path = os.getenv("V0_SQLITE_PATH")
            if not os.path.exists(dbl_path):
                raise FileNotFoundError(f"SQLite não encontrado: {dbl_path}")
            self.dbl_connection = sqlite3.connect(dbl_path)
            self.dbl_connection.row_factory = sqlite3.Row
            console.print("✅ Conectado ao SQLite (DBL)")

            # Conectar à database V0_OLD em vez da V0
            self.v0_old_connection = psycopg2.connect(
                host=os.getenv("SUPABASE_V0_OLD_HOST"),
                database=os.getenv("SUPABASE_V0_OLD_DBNAME"),
                user=os.getenv("SUPABASE_V0_OLD_USER"),
                password=os.getenv("SUPABASE_V0_OLD_PASSWORD"),
                port=int(os.getenv("SUPABASE_V0_OLD_PORT", "6543"))
            )
            console.print("✅ Conectado ao Supabase V0_OLD (dados antigos)")

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

    def migrate_table_v0_old(self, table_key: str, source: str, dest: str, campos: List, de_para_mapping: Dict, where: str = None, only_ids: List = None, batch_size: int = 100, max_workers: int = 8):
        """Migra uma tabela usando o de-para customizado para V0_OLD - VERSÃO CORRIGIDA COM RETOMADA"""
        
        # Verificar se já existem registros na tabela destino
        cursor_dest = self.v1_connection.cursor()
        cursor_dest.execute(f"SELECT COUNT(*) AS count FROM {dest}")
        already_inserted = cursor_dest.fetchone()[0]
        
        if already_inserted > 0:
            console.print(f"⚠️ Tabela {dest} já possui {already_inserted} registros.")
            resume = Confirm.ask(f"Deseja retomar a migração de onde parou?")
            if resume:
                console.print(f"🔄 Retomando migração de {dest} ({already_inserted} já migrados)")
            else:
                if Confirm.ask(f"Deseja sobrescrever os dados existentes em {dest}?"):
                    # SÓ AGORA limpa se o usuário confirmar sobrescrita
                    cursor_dest.execute(f"DELETE FROM {dest}")
                    self.v1_connection.commit()
                    console.print(f"🗑️ Tabela {dest} limpa para sobrescrita")
                    already_inserted = 0
                else:
                    console.print(f"⏭️ Pulando migração de {dest}")
                    return 0
        else:
            already_inserted = 0

        # Contar registros na origem
        if source == 'v0_old':  # Mudança: usar v0_old
            conn = self.v0_old_connection
            cursor_src = conn.cursor(cursor_factory=RealDictCursor)
        else:
            conn = self.dbl_connection
            cursor_src = conn.cursor()

        src_fields = [c[0] for c in campos]
        dest_fields = [c[1] for c in campos]
        where_clause = f" WHERE {where}" if where else ""

        # Usar tabela origem do mapeamento customizado
        origem_table = de_para_mapping[table_key]['origem']
        cursor_src.execute(f"SELECT COUNT(*) AS count FROM {origem_table}{where_clause}")
        total_rows_row = cursor_src.fetchone()
        total_rows = total_rows_row.get('count', 0) if isinstance(total_rows_row, dict) else total_rows_row[0]
        
        if total_rows == 0:
            console.print(f"⚠️ Nenhum registro encontrado em {origem_table}")
            return 0

        console.print(f"📊 {total_rows} registros encontrados para migração (V0_OLD: {origem_table})")
        
        # Calcular offset inicial para retomada
        start_offset = already_inserted
        remaining_rows = total_rows - start_offset
        
        if remaining_rows <= 0:
            console.print(f"✅ Migração de {dest} já está completa!")
            return already_inserted
            
        console.print(f"🔄 Iniciando do registro {start_offset + 1}/{total_rows}")
        
        migrated = 0
        cursor_dest = self.v1_connection.cursor()
        
        with Progress(SpinnerColumn(), BarColumn(), TaskProgressColumn(), TextColumn("{task.description}")) as progress:
            task = progress.add_task(f"Migrando {table_key} (V0_OLD)", total=remaining_rows)
            
            # MIGRAÇÃO PARALELA CORRETA - SEM COMPARTILHAR CURSORS
            from concurrent.futures import ThreadPoolExecutor, as_completed
            import threading
            
            current_batch_size = min(batch_size * 2, 200)  # Dobra o batch size, máximo 200
            batches = []
            
            # Preparar todos os batches primeiro
            offset = start_offset
            batch_num = 1
            while offset < total_rows:
                query = f"SELECT {', '.join(src_fields)} FROM {origem_table}{where_clause} OFFSET {offset} LIMIT {current_batch_size}"
                batches.append((batch_num, offset, query, current_batch_size))
                offset += current_batch_size
                batch_num += 1
            
            # Executar em paralelo com conexões independentes
            with ThreadPoolExecutor(max_workers=min(max_workers, 4)) as executor:
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
                            console.print(f"✅ Batch {batch_num}: {batch_migrated} registros migrados (V0_OLD paralelo)")
                    except Exception as e:
                        console.print(f"❌ Erro no batch {batch_num}: {e}")

        console.print(f"✅ {migrated} registros migrados para {dest} (total: {already_inserted + migrated}) [V0_OLD]")
        return already_inserted + migrated
        """Migra uma tabela usando o de-para - VERSÃO CORRIGIDA COM RETOMADA (V0_OLD)"""
        
        # Verificar se já existem registros na tabela destino
        cursor_dest = self.v1_connection.cursor()
        cursor_dest.execute(f"SELECT COUNT(*) AS count FROM {dest}")
        already_inserted = cursor_dest.fetchone()[0]
        
        if already_inserted > 0:
            console.print(f"⚠️ Tabela {dest} já possui {already_inserted} registros.")
            resume = Confirm.ask(f"Deseja retomar a migração de onde parou?")
            if resume:
                console.print(f"🔄 Retomando migração de {dest} ({already_inserted} já migrados)")
            else:
                if Confirm.ask(f"Deseja sobrescrever os dados existentes em {dest}?"):
                    # SÓ AGORA limpa se o usuário confirmar sobrescrita
                    cursor_dest.execute(f"DELETE FROM {dest}")
                    self.v1_connection.commit()
                    console.print(f"🗑️ Tabela {dest} limpa para sobrescrita")
                    already_inserted = 0
                else:
                    console.print(f"⏭️ Pulando migração de {dest}")
                    return 0
        else:
            already_inserted = 0

        # Contar registros na origem
        if source == 'v0_old':  # Mudança: usar v0_old
            conn = self.v0_old_connection
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

        console.print(f"📊 {total_rows} registros encontrados para migração (V0_OLD)")
        
        # Calcular offset inicial para retomada
        start_offset = already_inserted
        remaining_rows = total_rows - start_offset
        
        if remaining_rows <= 0:
            console.print(f"✅ Migração de {dest} já está completa!")
            return already_inserted
            
        console.print(f"🔄 Iniciando do registro {start_offset + 1}/{total_rows}")
        
        migrated = 0
        cursor_dest = self.v1_connection.cursor()
        
        with Progress(SpinnerColumn(), BarColumn(), TaskProgressColumn(), TextColumn("{task.description}")) as progress:
            task = progress.add_task(f"Migrando {table_key} (V0_OLD)", total=remaining_rows)
            
            # MIGRAÇÃO PARALELA CORRETA - SEM COMPARTILHAR CURSORS
            from concurrent.futures import ThreadPoolExecutor, as_completed
            import threading
            
            current_batch_size = min(batch_size * 2, 200)  # Dobra o batch size, máximo 200
            batches = []
            
            # Preparar todos os batches primeiro
            offset = start_offset
            batch_num = 1
            while offset < total_rows:
                query = f"SELECT {', '.join(src_fields)} FROM {DE_PARA[table_key]['origem']}{where_clause} OFFSET {offset} LIMIT {current_batch_size}"
                batches.append((batch_num, offset, query, current_batch_size))
                offset += current_batch_size
                batch_num += 1
            
            # Executar em paralelo com conexões independentes
            with ThreadPoolExecutor(max_workers=min(max_workers, 4)) as executor:
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
                            console.print(f"✅ Batch {batch_num}: {batch_migrated} registros migrados (V0_OLD paralelo)")
                    except Exception as e:
                        console.print(f"❌ Erro no batch {batch_num}: {e}")

        console.print(f"✅ {migrated} registros migrados para {dest} (total: {already_inserted + migrated}) [V0_OLD]")
        return already_inserted + migrated

    def _process_batch_parallel(self, batch_info, source, dest, dest_fields, src_fields, table_key):
        """Processa um batch em paralelo com conexões independentes (V0_OLD)"""
        batch_num, offset, query, batch_size = batch_info
        
        try:
            # Criar conexões independentes para este thread
            if source == 'v0_old':  # Mudança: usar v0_old
                conn_src = psycopg2.connect(
                    host=os.getenv("SUPABASE_V0_OLD_HOST"),
                    database=os.getenv("SUPABASE_V0_OLD_DBNAME"),
                    user=os.getenv("SUPABASE_V0_OLD_USER"),
                    password=os.getenv("SUPABASE_V0_OLD_PASSWORD"),
                    port=int(os.getenv("SUPABASE_V0_OLD_PORT", "6543"))
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
        """Inserção de batch sequencial COM MAPEAMENTO CORRETO (V0_OLD)"""
        if not rows:
            return
        
        import json
        
        def safe_json_convert(val):
            """Converte valores de forma segura para inserção no PostgreSQL"""
            if isinstance(val, dict):
                return json.dumps(val, ensure_ascii=False)
            elif val is None:
                return None
            else:
                return val
        
        # Caso especial para embeddings V0_OLD: inserir com confidence=0.0
        if table == 'contratacao_emb' and 'confidence' not in src_fields:
            # Inserção customizada para embeddings V0_OLD
            data = []
            for row in rows:
                if isinstance(row, dict):
                    data.append((
                        row.get('id'),
                        row.get('numerocontrolepncp'),
                        row.get('embedding_vector'),  # Este já deve estar no formato correto
                        row.get('modelo_embedding'),
                        safe_json_convert(row.get('metadata')),  # Converter dict para JSON string
                        row.get('created_at'),
                        0.0  # confidence padrão
                    ))
                else:
                    # Para outros tipos de row (RealDictRow, etc.)
                    values = []
                    for i, field in enumerate(['id', 'numerocontrolepncp', 'embedding_vector', 'modelo_embedding', 'metadata', 'created_at']):
                        if i < len(row):
                            val = row[i] if hasattr(row, '__getitem__') and not hasattr(row, 'get') else row.get(field, row[i] if i < len(row) else None)
                            if field == 'metadata':
                                val = safe_json_convert(val)
                            values.append(val)
                        else:
                            values.append(None)
                    values.append(0.0)  # confidence
                    data.append(tuple(values))
            
            # SQL customizado para embeddings
            sql = """INSERT INTO contratacao_emb 
                    (id, numero_controle_pncp, embedding_vector, modelo_embedding, metadata, created_at, confidence) 
                    VALUES %s"""
            execute_values(cursor, sql, data, page_size=100)
            return
        
        # Inserção padrão para outras tabelas
        def row_to_tuple(row):
            if isinstance(row, dict):
                result = []
                for i, src_field in enumerate(src_fields):
                    dest_field = fields[i] if i < len(fields) else None
                    val = row.get(src_field)
                    
                    if val is None or val == '':
                        if dest_field in ['cod_nv1', 'cod_nv2', 'cod_nv3']:
                            result.append(0)
                        elif dest_field == 'confidence':
                            result.append(0.0)
                        else:
                            result.append('')
                    else:
                        result.append(safe_json_convert(val))
                return tuple(result)
            else:
                # Para outros tipos de row
                result = []
                for i, val in enumerate(row):
                    result.append(safe_json_convert(val) if val is not None else '')
                return tuple(result)
        
        data = [row_to_tuple(row) for row in rows]
        execute_values(cursor, f"INSERT INTO {table} ({', '.join(fields)}) VALUES %s", data, page_size=100)

    def run(self):
        console.print(Panel.fit("[bold blue]GovGo V1 - Migração de Dados V0_OLD (dados antigos)[/bold blue]", title="🔄 Migração V0_OLD/DBL → V1"))
        if not self.connect_databases():
            return
        start = time.time()

        # AJUSTE ESPECÍFICO PARA V0_OLD: sobrescrever nome da tabela embeddings
        # Criar uma cópia do DE_PARA e modificar o nome da tabela origem
        DE_PARA_V0_OLD = DE_PARA.copy()
        DE_PARA_V0_OLD['contratacoes_embeddings'] = DE_PARA['contratacoes_embeddings'].copy()
        DE_PARA_V0_OLD['contratacoes_embeddings']['origem'] = 'contratacoes_embeddings_expiradas'
        
        # Mapeamento específico para V0_OLD (sem confidence, com campos corretos)
        campos_v0_old = [
            ('id', 'id'),
            ('numerocontrolepncp', 'numero_controle_pncp'),
            ('embedding_vector', 'embedding_vector'),
            ('modelo_embedding', 'modelo_embedding'),
            ('metadata', 'metadata'),
            ('created_at', 'created_at')
            # Nota: confidence não existe na V0_OLD, será definida como 0.0 na inserção
        ]
        
        DE_PARA_V0_OLD['contratacoes_embeddings']['campos'] = campos_v0_old
        
        console.print(f"🔧 Ajustado mapeamento V0_OLD:")
        console.print(f"   📋 Tabela: {DE_PARA_V0_OLD['contratacoes_embeddings']['origem']} → contratacao_emb")
        console.print(f"   📊 Campos: {len(campos_v0_old)} campos (confidence será 0.0)")
        for campo_origem, campo_destino in campos_v0_old:
            console.print(f"      {campo_origem} → {campo_destino}")

        # Steps com parâmetros otimizados para VELOCIDADE - FOCO EM CONTRATACOES_EMBEDDINGS V0_OLD
        steps = [
            ("categoria", lambda: self.migrate_table_v0_old('categoria', 'v0_old', 'categoria', DE_PARA_V0_OLD['categoria']['campos'], DE_PARA_V0_OLD, None, None, 200, 8)),
            ("contratacoes_embeddings", lambda: self.migrate_table_v0_old('contratacoes_embeddings', 'v0_old', 'contratacao_emb', DE_PARA_V0_OLD['contratacoes_embeddings']['campos'], DE_PARA_V0_OLD, None, None, 100, 8)),
            ("contratacao", None),
            ("item_contratacao", None),
            ("item_classificacao", None)
        ]

        for idx, (step_name, step_func) in enumerate(steps):
            console.rule(f"[bold yellow]Passo {idx+1}: {step_name} [V0_OLD]")
            
            if step_func is not None:
                result = step_func()
                self._show_step_result(step_name, result)
            else:
                # Passos dependentes de dados migrados
                if step_name == "contratacao":
                    # Buscar IDs dos embeddings para filtrar contratações
                    cursor_v1 = self.v1_connection.cursor()
                    cursor_v1.execute("SELECT numero_controle_pncp FROM contratacao_emb")
                    self.numerocontrolepncp_list = [row[0] for row in cursor_v1.fetchall()]
                    
                    if self.numerocontrolepncp_list:
                        console.print(f"📋 {len(self.numerocontrolepncp_list)} contratações com embeddings encontradas")
                        # Criar WHERE clause para filtrar por IDs
                        ids_str = "','".join(self.numerocontrolepncp_list)
                        where_clause = f"numeroControlePNCP IN ('{ids_str}')"
                        result = self.migrate_table_v0_old('contratacao', 'dbl', 'contratacao', DE_PARA_V0_OLD['contratacao']['campos'], DE_PARA_V0_OLD, where_clause, None, 200, 6)
                        self._show_step_result(step_name, result)
                    else:
                        console.print("⚠️ Nenhum embedding encontrado. Pulando contratações.")
                        
                elif step_name == "item_contratacao":
                    if self.numerocontrolepncp_list:
                        ids_str = "','".join(self.numerocontrolepncp_list)
                        where_clause = f"numeroControlePNCP IN ('{ids_str}')"
                        result = self.migrate_table_v0_old('item_contratacao', 'dbl', 'item_contratacao', DE_PARA_V0_OLD['item_contratacao']['campos'], DE_PARA_V0_OLD, where_clause, None, 300, 6)
                        self._show_step_result(step_name, result)
                    else:
                        console.print("⚠️ Nenhuma contratação migrada. Pulando itens de contratação.")
                        
                elif step_name == "item_classificacao":
                    if self.numerocontrolepncp_list:
                        ids_str = "','".join(self.numerocontrolepncp_list)
                        where_clause = f"numeroControlePNCP IN ('{ids_str}')"
                        result = self.migrate_table_v0_old('item_classificacao', 'dbl', 'item_classificacao', DE_PARA_V0_OLD['item_classificacao']['campos'], DE_PARA_V0_OLD, where_clause, None, 400, 6)
                        self._show_step_result(step_name, result)
                    else:
                        console.print("⚠️ Nenhuma contratação migrada. Pulando classificações.")

            # Confirmação para continuar
            if idx < len(steps) - 1:  # Não perguntar no último step
                if not Confirm.ask(f"Deseja continuar para o próximo passo?"):
                    console.print("[bold red]Execução interrompida pelo usuário.")
                    break

        elapsed = time.time() - start
        console.print(f"\n🎉 [bold green]Migração V0_OLD concluída! Tempo total: {elapsed:.1f}s[/bold green]")
        
        # Relatório final
        table = Table(title="📊 Relatório de Migração V0_OLD")
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
        if self.v0_old_connection:
            self.v0_old_connection.close()
        if self.v1_connection:
            self.v1_connection.close()

    def _show_step_result(self, step_name, result):
        table = Table(title=f"✅ Resultado: {step_name} [V0_OLD]")
        table.add_column("Tabela", style="cyan")
        table.add_column("Registros migrados", style="green")
        table.add_row(step_name, str(result))
        console.print(table)

def main():
    migrator = DataMigratorV0Old()
    migrator.run()

if __name__ == "__main__":
    main()
