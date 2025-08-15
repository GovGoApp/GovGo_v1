#!/usr/bin/env python3
## GovGo V1 - Teste de Migração (Dry Run)
## Testa todas as conexões e analisa os dados antes da migração real

import os
import sys
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
from rich.console import Console
from rich.panel import Panel
from dotenv import load_dotenv
import time
# Garante que o diretório pai (v1) está no sys.path para importar db corretamente
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from db.DEPARA_BDS0_BDS1 import DE_PARA

load_dotenv()
console = Console()

class MigrationDryRun:
    def analyze(self):
        console.print(Panel.fit("[bold blue]GovGo V1 - Teste de Migração (Dry Run)[/bold blue]\nAnálise completa antes da migração real\n\n🔌 Conectividade\n📊 Análise de dados\n🎯 Cobertura de embeddings\n🏗️ Estruturas de tabelas\n⏱️ Estimativas de tempo", title="🧪 Teste de Migração"))
        # Conectar bancos
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
        except Exception as e:
            console.print(f"❌ Erro ao conectar databases: {e}")
            self.stats['errors'].append(str(e))
            return

        start = time.time()

        # 1. Migrar categoria (V0 → V1) - tudo
        self._count_table('categoria', 'v0', DE_PARA['categoria']['campos'])

        # 2. Migrar contratacoes_embeddings (V0 → V1)
        self._count_table('contratacoes_embeddings', 'v0', DE_PARA['contratacoes_embeddings']['campos'])

        # 3. Contratações (DBL → V1, apenas IDs presentes em embeddings)
        cursor_v0 = self.v0_connection.cursor(cursor_factory=RealDictCursor)
        cursor_v0.execute(f"SELECT {DE_PARA['contratacoes_embeddings']['campos'][0][0]} FROM {DE_PARA['contratacoes_embeddings']['origem']}")
        self.numerocontrolepncp_list = [row[DE_PARA['contratacoes_embeddings']['campos'][0][0]] for row in cursor_v0.fetchall()]
        self._count_table('contratacao', 'dbl', DE_PARA['contratacao']['campos'], only_ids=self.numerocontrolepncp_list)

        # 4. Itens de contratação (DBL → V1, apenas IDs já migrados)
        self._count_table('item_contratacao', 'dbl', DE_PARA['item_contratacao']['campos'], only_ids=self.numerocontrolepncp_list)

        # 5. Itens classificação (DBL → V1, apenas IDs já migrados)
        self._count_table('item_classificacao', 'dbl', DE_PARA['item_classificacao']['campos'], only_ids=self.numerocontrolepncp_list)

        elapsed = time.time() - start
        console.print(f"\n[bold green]Dry Run concluído! Tempo total: {elapsed:.1f}s[/bold green]")
        for k, v in self.stats.items():
            if k != 'errors':
                console.print(f"  - {k}: {v}")
        if self.stats['errors']:
            console.print(f"❌ Erros: {self.stats['errors']}")
        # Fechar conexões
        if self.dbl_connection:
            self.dbl_connection.close()
        if self.v0_connection:
            self.v0_connection.close()
        if self.v1_connection:
            self.v1_connection.close()
    def __init__(self):
        self.dbl_connection = None
        self.v0_connection = None
        self.v1_connection = None
        self.stats = {k: 0 for k in DE_PARA.keys()}
        self.stats['errors'] = []
        self.numerocontrolepncp_list = []
    def _count_table(self, table_key, source, campos, only_ids=None):
        try:
            if source == 'v0':
                conn = self.v0_connection
            elif source == 'dbl':
                conn = self.dbl_connection
            else:
                raise ValueError('Fonte desconhecida')
            cursor = conn.cursor()
            # Para contratacoes_embeddings, filtrar campos extras removidos de V1 e garantir nomes corretos
            if table_key == 'contratacoes_embeddings':
                campos_filtrados = [c for c in campos if c[1] not in ('data_processamento', 'versao_modelo', 'updated_at')]
                src_fields = [c[0] for c in campos_filtrados]
                dest_fields = [c[1] for c in campos_filtrados]
            else:
                src_fields = [c[0] for c in campos]
                dest_fields = [c[1] for c in campos]

            # Sempre usar os nomes do destino (snake_case v1) nos comandos para o banco v1
            # Isso garante que SELECT/INSERT usem apenas os campos válidos do schema v1
            where_clause = ""
            total = 0
            if only_ids:
                batch_size = 1000
                for i in range(0, len(only_ids), batch_size):
                    batch_ids = only_ids[i:i+batch_size]
                    placeholders = ','.join(['?' for _ in batch_ids]) if source == 'dbl' else ','.join(['%s' for _ in batch_ids])
                    where_ids = f"{src_fields[0]} IN ({placeholders})"
                    query = f"SELECT COUNT(*) FROM {DE_PARA[table_key]['origem']} WHERE {where_ids}{where_clause}"
                    cursor.execute(query, batch_ids)
                    count = cursor.fetchone()[0]
                    total += count
            else:
                query = f"SELECT COUNT(*) FROM {DE_PARA[table_key]['origem']}{where_clause}"
                cursor.execute(query)
                total = cursor.fetchone()[0]
            self.stats[table_key] = total
            console.print(f"🔎 {table_key}: {total} registros disponíveis para migração")

            # Validação dos campos no destino (V1)
            if table_key in DE_PARA:
                v1_cursor = self.v1_connection.cursor()
                v1_table = DE_PARA[table_key]['destino']
                v1_cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{v1_table}'")
                v1_columns = set([row[0] for row in v1_cursor.fetchall()])
                missing = [f for f in dest_fields if f not in v1_columns]
                if missing:
                    self.stats['errors'].append(f"{table_key}: campos ausentes em V1: {missing}")
                    console.print(f"❌ {table_key}: campos ausentes em V1: {missing}")
                else:
                    console.print(f"✅ {table_key}: todos os campos existem em V1")

                # SELECT de teste
                try:
                    select_fields = ','.join(dest_fields)
                    v1_cursor.execute(f"SELECT {select_fields} FROM {v1_table} LIMIT 1")
                    console.print(f"✅ SELECT 1 linha de {v1_table} OK")
                except Exception as e:
                    self.stats['errors'].append(f"{table_key}: erro SELECT V1: {str(e)}")
                    console.print(f"❌ {table_key}: erro SELECT V1: {e}")

                # INSERT de teste com dados reais e DELETE após inserir
                try:
                    v1_cursor.execute("BEGIN;")
                    insert_fields = ','.join(dest_fields)
                    values_placeholder = ','.join(['%s'] * len(dest_fields))
                    # Buscar 1 linha real da origem
                    cursor.execute(f"SELECT {','.join(src_fields)} FROM {DE_PARA[table_key]['origem']} LIMIT 1")
                    real_row = cursor.fetchone()
                    if real_row:
                        mapped_values = []
                        for idx, (src, dest) in enumerate(campos):
                            val = real_row[idx]
                            # Se for contratacoes_embeddings e campo metadata, converter para JSON
                            if table_key == 'contratacoes_embeddings' and dest_fields[idx] == 'metadata' and val is not None:
                                import json
                                val = json.dumps(val) if not isinstance(val, str) else val
                            # Conversão de booleano para existe_resultado
                            if table_key == 'contratacao' and dest_fields[idx] == 'existe_resultado':
                                val = bool(val) if val is not None else None
                            # Garantir snake_case para item_contratacao e item_classificacao
                            if table_key == 'item_contratacao' and dest_fields[idx] == 'marca_item':
                                val = val
                            if table_key == 'item_classificacao' and dest_fields[idx] == 'created_at':
                                val = val
                            # Para categoria, garantir que cod_cat e cod_nv* sejam texto
                            if table_key == 'categoria' and dest in ['cod_cat','cod_nv0','cod_nv1','cod_nv2','cod_nv3'] and val is not None:
                                val = str(val)
                            mapped_values.append(val)
                        v1_cursor.execute(f"INSERT INTO {v1_table} ({insert_fields}) VALUES ({values_placeholder}) RETURNING *", mapped_values)
                        inserted = v1_cursor.fetchone()
                        pk_field = dest_fields[0]
                        pk_value = inserted[0]
                        v1_cursor.execute(f"DELETE FROM {v1_table} WHERE {pk_field} = %s", (pk_value,))
                        v1_cursor.execute("COMMIT;")
                        console.print(f"✅ INSERT/DELETE 1 linha real em {v1_table} OK")
                    else:
                        console.print(f"⚠️ Nenhum dado real disponível para teste em {table_key}")
                except Exception as e:
                    v1_cursor.execute("ROLLBACK;")
                    self.stats['errors'].append(f"{table_key}: erro INSERT/DELETE V1: {str(e)}")
                    console.print(f"❌ {table_key}: erro INSERT/DELETE V1: {e}")

                # INSERT de teste com 10 linhas reais e DELETE após inserir
                try:
                    v1_cursor.execute("BEGIN;")
                    insert_fields = ','.join(dest_fields)
                    values_placeholder = ','.join(['%s'] * len(dest_fields))
                    cursor.execute(f"SELECT {','.join(src_fields)} FROM {DE_PARA[table_key]['origem']} LIMIT 10")
                    real_rows = cursor.fetchall()
                    if real_rows:
                        for real_row in real_rows:
                            mapped_values = []
                            for idx, (src, dest) in enumerate(campos):
                                val = real_row[idx]
                                if table_key == 'contratacoes_embeddings' and dest_fields[idx] == 'metadata' and val is not None:
                                    import json
                                    val = json.dumps(val) if not isinstance(val, str) else val
                                if table_key == 'contratacao' and dest_fields[idx] == 'existe_resultado':
                                    val = bool(val) if val is not None else None
                                # Para categoria, garantir que cod_cat e cod_nv* sejam texto
                                if table_key == 'categoria' and dest in ['cod_cat','cod_nv0','cod_nv1','cod_nv2','cod_nv3'] and val is not None:
                                    val = str(val)
                                mapped_values.append(val)
                            v1_cursor.execute(f"INSERT INTO {v1_table} ({insert_fields}) VALUES ({values_placeholder}) RETURNING *", mapped_values)
                            inserted = v1_cursor.fetchone()
                            pk_field = dest_fields[0]
                            pk_value = inserted[0]
                            v1_cursor.execute(f"DELETE FROM {v1_table} WHERE {pk_field} = %s", (pk_value,))
                        v1_cursor.execute("COMMIT;")
                        console.print(f"✅ INSERT/DELETE 10 linhas reais em {v1_table} OK")
                    else:
                        console.print(f"⚠️ Menos de 10 dados reais disponíveis para teste em {table_key}")
                except Exception as e:
                    v1_cursor.execute("ROLLBACK;")
                    self.stats['errors'].append(f"{table_key}: erro INSERT/DELETE 10x V1: {str(e)}")
                    console.print(f"❌ {table_key}: erro INSERT/DELETE 10x V1: {e}")
        except Exception as e:
            self.stats['errors'].append(f"{table_key}: {str(e)}")
            console.print(f"❌ Erro ao contar {table_key}: {e}")
            cursor = conn.cursor()
            src_fields = [c[0] for c in campos]
            dest_fields = [c[1] for c in campos]
            where_clause = ""
            total = 0
            if only_ids:
                batch_size = 1000
                for i in range(0, len(only_ids), batch_size):
                    batch_ids = only_ids[i:i+batch_size]
                    placeholders = ','.join(['?' for _ in batch_ids]) if source == 'dbl' else ','.join(['%s' for _ in batch_ids])
                    where_ids = f"{src_fields[0]} IN ({placeholders})"
                    query = f"SELECT COUNT(*) FROM {DE_PARA[table_key]['origem']} WHERE {where_ids}{where_clause}"
                    cursor.execute(query, batch_ids)
                    count = cursor.fetchone()[0]
                    total += count
            else:
                query = f"SELECT COUNT(*) FROM {DE_PARA[table_key]['origem']}{where_clause}"
                cursor.execute(query)
                total = cursor.fetchone()[0]
            self.stats[table_key] = total
            console.print(f"🔎 {table_key}: {total} registros disponíveis para migração")

            # Validação dos campos no destino (V1)
            if table_key in DE_PARA:
                v1_cursor = self.v1_connection.cursor()
                v1_table = DE_PARA[table_key]['destino']
                v1_cursor.execute(f"SELECT column_name FROM information_schema.columns WHERE table_name = '{v1_table}'")
                v1_columns = set([row[0] for row in v1_cursor.fetchall()])
                missing = [f for f in dest_fields if f not in v1_columns]
                if missing:
                    self.stats['errors'].append(f"{table_key}: campos ausentes em V1: {missing}")
                    console.print(f"❌ {table_key}: campos ausentes em V1: {missing}")
                else:
                    console.print(f"✅ {table_key}: todos os campos existem em V1")

                # SELECT de teste
                # SELECT de teste
                try:
                    select_fields = ','.join(dest_fields)
                    v1_cursor.execute(f"SELECT {select_fields} FROM {v1_table} LIMIT 1")
                    console.print(f"✅ SELECT 1 linha de {v1_table} OK")
                except Exception as e:
                    self.stats['errors'].append(f"{table_key}: erro SELECT V1: {str(e)}")
                    console.print(f"❌ {table_key}: erro SELECT V1: {e}")

                # INSERT de teste (rollback)
                try:
                    v1_cursor.execute("BEGIN;")
                    insert_fields = ','.join(dest_fields)
                    values_placeholder = ','.join(['%s'] * len(dest_fields))
                    dummy_row = [None] * len(dest_fields)
                    v1_cursor.execute(f"INSERT INTO {v1_table} ({insert_fields}) VALUES ({values_placeholder})", dummy_row)
                    v1_cursor.execute("ROLLBACK;")
                    console.print(f"✅ INSERT 1 linha de teste em {v1_table} OK (rollback)")
                except Exception as e:
                    self.stats['errors'].append(f"{table_key}: erro INSERT V1: {str(e)}")
                    console.print(f"❌ {table_key}: erro INSERT V1: {e}")

                # INSERT de teste (rollback) com 10 linhas
                try:
                    v1_cursor.execute("BEGIN;")
                    insert_fields = ','.join(dest_fields)
                    values_placeholder = ','.join(['%s'] * len(dest_fields))
                    dummy_rows = [[None] * len(dest_fields) for _ in range(10)]
                    args_str = ','.join([f"({values_placeholder})" for _ in range(10)])
                    flat_args = [None] * (len(dest_fields) * 10)
                    v1_cursor.execute(f"INSERT INTO {v1_table} ({insert_fields}) VALUES {args_str}", flat_args)
                    v1_cursor.execute("ROLLBACK;")
                    console.print(f"✅ INSERT 10 linhas de teste em {v1_table} OK (rollback)")
                except Exception as e:
                    self.stats['errors'].append(f"{table_key}: erro INSERT 10x V1: {str(e)}")
                    console.print(f"❌ {table_key}: erro INSERT 10x V1: {e}")

def main():
    dryrun = MigrationDryRun()
    dryrun.analyze()

if __name__ == "__main__":
    main()
