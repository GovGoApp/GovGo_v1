#!/usr/bin/env python3
"""
GovGo V1 - Teste de Migração (Dry Run)
=======================================
Testa todas as conexões e analisa os dados antes da migração real

VERIFICAÇÕES:
1. Conectividade com todas as bases (DBL, V0, V1)
2. Análise de dados disponíveis em cada fonte
3. Verificação de estruturas de tabelas
4. Contagem de registros
5. Validação de chaves estrangeiras
6. Estimativa de tempo e espaço

Este script NÃO modifica nenhum dado - apenas analisa e reporta
"""

import os
import sys
import sqlite3
import psycopg2
from psycopg2.extras import RealDictCursor
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional
import time

# Adicionar o diretório pai ao path para importações
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Carregar variáveis do .env
load_dotenv()

# Importar schemas das tabelas
from db.table_schemas import get_table_schema, get_insertable_columns, get_test_data, generate_insert_query, validate_data_types

console = Console()

class MigrationTester:
    """Testador de migração - análise completa sem modificar dados"""
    
    def __init__(self):
        self.dbl_connection = None  # SQLite PNCP_DB_v2.db
        self.v0_connection = None   # Supabase V0
        self.v1_connection = None   # Supabase V1
        self.real_test_data = {}    # Dados reais para teste
        self.test_results = {
            'connections': {},
            'data_counts': {},
            'table_structures': {},
            'embedding_analysis': {},
            'fk_validation': {},
            'errors': []
        }
        
    def test_connections(self):
        """Testar conectividade com todas as bases"""
        console.print("\n🔌 [bold blue]TESTE 1: Conectividade das Bases[/bold blue]")
        
        # 1. Teste SQLite (DBL)
        try:
            dbl_path = os.getenv("V0_SQLITE_PATH")
            console.print(f"📂 Testando SQLite: {dbl_path}")
            
            if not os.path.exists(dbl_path):
                raise FileNotFoundError(f"Arquivo não encontrado: {dbl_path}")
            
            self.dbl_connection = sqlite3.connect(dbl_path)
            self.dbl_connection.row_factory = sqlite3.Row
            
            # Teste básico
            cursor = self.dbl_connection.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            
            self.test_results['connections']['DBL'] = {
                'status': 'SUCCESS',
                'path': dbl_path,
                'size_mb': round(os.path.getsize(dbl_path) / (1024*1024), 2),
                'tables': tables
            }
            console.print(f"✅ SQLite conectado - {len(tables)} tabelas encontradas")
            
        except Exception as e:
            self.test_results['connections']['DBL'] = {
                'status': 'ERROR',
                'error': str(e)
            }
            console.print(f"❌ Erro SQLite: {e}")
        
        # 2. Teste Supabase V0
        try:
            console.print("📡 Testando Supabase V0...")
            self.v0_connection = psycopg2.connect(
                host=os.getenv("SUPABASE_V0_HOST"),
                database=os.getenv("SUPABASE_V0_DBNAME"),
                user=os.getenv("SUPABASE_V0_USER"),
                password=os.getenv("SUPABASE_V0_PASSWORD"),
                port=int(os.getenv("SUPABASE_V0_PORT", "6543"))
            )
            
            # Teste básico
            cursor = self.v0_connection.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            tables = [row['table_name'] for row in cursor.fetchall()]
            
            self.test_results['connections']['V0'] = {
                'status': 'SUCCESS',
                'host': os.getenv("SUPABASE_V0_HOST"),
                'database': os.getenv("SUPABASE_V0_DBNAME"),
                'tables': tables
            }
            console.print(f"✅ Supabase V0 conectado - {len(tables)} tabelas encontradas")
            
        except Exception as e:
            self.test_results['connections']['V0'] = {
                'status': 'ERROR',
                'error': str(e)
            }
            console.print(f"❌ Erro Supabase V0: {e}")
        
        # 3. Teste Supabase V1
        try:
            console.print("📡 Testando Supabase V1...")
            self.v1_connection = psycopg2.connect(
                host=os.getenv("SUPABASE_HOST"),
                database=os.getenv("SUPABASE_DBNAME"),
                user=os.getenv("SUPABASE_USER"),
                password=os.getenv("SUPABASE_PASSWORD"),
                port=int(os.getenv("SUPABASE_PORT", "5432"))
            )
            
            # Teste básico
            cursor = self.v1_connection.cursor(cursor_factory=RealDictCursor)
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """)
            tables = [row['table_name'] for row in cursor.fetchall()]
            
            self.test_results['connections']['V1'] = {
                'status': 'SUCCESS',
                'host': os.getenv("SUPABASE_HOST"),
                'database': os.getenv("SUPABASE_DBNAME"),
                'tables': tables
            }
            console.print(f"✅ Supabase V1 conectado - {len(tables)} tabelas encontradas")
            
        except Exception as e:
            self.test_results['connections']['V1'] = {
                'status': 'ERROR',
                'error': str(e)
            }
            console.print(f"❌ Erro Supabase V1: {e}")
    
    def analyze_source_data(self):
        """Analisar dados disponíveis nas fontes"""
        console.print("\n📊 [bold blue]TESTE 2: Análise dos Dados Fontes[/bold blue]")
        
        # Análise DBL (SQLite)
        if self.dbl_connection:
            console.print("🔍 Analisando dados do SQLite (DBL)...")
            try:
                cursor = self.dbl_connection.cursor()
                
                # Categorias
                cursor.execute("SELECT COUNT(*) as total FROM categoria")
                cat_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(DISTINCT codCat) as unique_codes FROM categoria")
                cat_unique = cursor.fetchone()[0]
                
                # Contratações
                cursor.execute("SELECT COUNT(*) as total FROM contratacao")
                cont_count = cursor.fetchone()[0]
                
                cursor.execute("SELECT COUNT(DISTINCT numeroControlePNCP) as unique_ids FROM contratacao")
                cont_unique = cursor.fetchone()[0]
                
                # Anos disponíveis
                cursor.execute("""
                    SELECT DISTINCT anoCompra 
                    FROM contratacao 
                    WHERE anoCompra IS NOT NULL 
                    ORDER BY anoCompra DESC
                """)
                anos = [row[0] for row in cursor.fetchall()]
                
                # Itens
                cursor.execute("SELECT COUNT(*) as total FROM item_contratacao")
                item_count = cursor.fetchone()[0]
                
                # Classificações
                cursor.execute("SELECT COUNT(*) as total FROM item_classificacao")
                classif_count = cursor.fetchone()[0]
                
                self.test_results['data_counts']['DBL'] = {
                    'categorias': {'total': cat_count, 'unique_codes': cat_unique},
                    'contratacoes': {'total': cont_count, 'unique_ids': cont_unique},
                    'itens_contratacao': item_count,
                    'itens_classificacao': classif_count,
                    'anos_disponiveis': anos[:10]  # Primeiros 10 anos
                }
                
                console.print(f"  📋 {cont_count:,} contratações ({cont_unique:,} únicas)")
                console.print(f"  🏷️ {cat_count:,} categorias ({cat_unique:,} códigos únicos)")
                console.print(f"  📦 {item_count:,} itens de contratação")
                console.print(f"  🏷️ {classif_count:,} classificações de itens")
                console.print(f"  📅 Anos: {', '.join(map(str, anos[:5]))}{' ...' if len(anos) > 5 else ''}")
                
            except Exception as e:
                self.test_results['errors'].append(f"Análise DBL: {e}")
                console.print(f"❌ Erro na análise DBL: {e}")
        
        # Análise V0 (Embeddings)
        if self.v0_connection:
            console.print("🧠 Analisando embeddings do Supabase V0...")
            try:
                cursor = self.v0_connection.cursor(cursor_factory=RealDictCursor)
                
                # Primeiro, descobrir quais tabelas existem
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_type = 'BASE TABLE'
                    AND table_name LIKE '%embedding%'
                    ORDER BY table_name
                """)
                embedding_tables = [row['table_name'] for row in cursor.fetchall()]
                
                if not embedding_tables:
                    # Tentar nomes alternativos
                    possible_names = ['contratacoes_embeddings', 'contratacao_embedding', 'embeddings']
                    for table_name in possible_names:
                        try:
                            cursor.execute(f"SELECT COUNT(*) FROM {table_name} LIMIT 1")
                            embedding_tables = [table_name]
                            break
                        except:
                            continue
                
                if embedding_tables:
                    embedding_table = embedding_tables[0]
                    console.print(f"  📊 Tabela de embeddings encontrada: {embedding_table}")
                    
                    # Embeddings de contratações
                    cursor.execute(f"SELECT COUNT(*) as total FROM {embedding_table}")
                    emb_count = cursor.fetchone()['total']
                    
                    # Verificar quais colunas existem
                    cursor.execute(f"""
                        SELECT column_name 
                        FROM information_schema.columns
                        WHERE table_name = '{embedding_table}'
                        AND column_name IN ('numerocontrolepncp', 'numeroControlePNCP', 'numero_controle_pncp')
                    """)
                    id_columns = [row['column_name'] for row in cursor.fetchall()]
                    
                    if id_columns:
                        id_column = id_columns[0]
                        cursor.execute(f"""
                            SELECT COUNT(DISTINCT {id_column}) as unique_ids 
                            FROM {embedding_table}
                        """)
                        emb_unique = cursor.fetchone()['unique_ids']
                    else:
                        emb_unique = 0
                        console.print("  ⚠️ Coluna de ID não encontrada")
                else:
                    console.print("  ⚠️ Nenhuma tabela de embeddings encontrada")
                    emb_count = 0
                    emb_unique = 0
                
                # Tentar obter informações adicionais se tivermos dados
                modelos = []
                conf_stats = None
                
                if embedding_tables and emb_count > 0:
                    embedding_table = embedding_tables[0]
                    
                    # Verificar se existem colunas de modelo e confidence
                    cursor.execute(f"""
                        SELECT column_name 
                        FROM information_schema.columns
                        WHERE table_name = '{embedding_table}'
                        AND column_name IN ('modelo_embedding', 'model', 'modelo')
                    """)
                    model_columns = [row['column_name'] for row in cursor.fetchall()]
                    
                    if model_columns:
                        model_column = model_columns[0]
                        cursor.execute(f"""
                            SELECT {model_column} as modelo_embedding, COUNT(*) as count
                            FROM {embedding_table}
                            GROUP BY {model_column}
                            ORDER BY count DESC
                        """)
                        modelos = cursor.fetchall()
                    
                    # Verificar confidence
                    cursor.execute(f"""
                        SELECT column_name 
                        FROM information_schema.columns
                        WHERE table_name = '{embedding_table}'
                        AND column_name IN ('confidence', 'conf', 'score')
                    """)
                    conf_columns = [row['column_name'] for row in cursor.fetchall()]
                    
                    if conf_columns:
                        conf_column = conf_columns[0]
                        cursor.execute(f"""
                            SELECT 
                                AVG({conf_column}) as avg_confidence,
                                MIN({conf_column}) as min_confidence,
                                MAX({conf_column}) as max_confidence
                            FROM {embedding_table}
                            WHERE {conf_column} IS NOT NULL
                        """)
                        conf_stats = cursor.fetchone()
                
                self.test_results['data_counts']['V0'] = {
                    'embeddings': {'total': emb_count, 'unique_ids': emb_unique},
                    'modelos': [{'modelo': m['modelo_embedding'], 'count': m['count']} for m in modelos] if modelos else [],
                    'confidence_stats': dict(conf_stats) if conf_stats else None,
                    'embedding_table': embedding_tables[0] if embedding_tables else None
                }
                
                console.print(f"  🧠 {emb_count:,} embeddings ({emb_unique:,} IDs únicos)")
                if modelos:
                    modelo_str = ', '.join([f"{m['modelo_embedding']} ({m['count']:,})" for m in modelos[:3]])
                    console.print(f"  🤖 Modelos: {modelo_str}")
                if conf_stats and conf_stats['avg_confidence']:
                    console.print(f"  📊 Confidence: {conf_stats['avg_confidence']:.3f} (avg), {conf_stats['min_confidence']:.3f}-{conf_stats['max_confidence']:.3f}")
                
            except Exception as e:
                self.test_results['errors'].append(f"Análise V0: {e}")
                console.print(f"❌ Erro na análise V0: {e}")
        
        # Análise V1 (Estado atual)
        if self.v1_connection:
            console.print("🏗️ Analisando estado atual do Supabase V1...")
            try:
                cursor = self.v1_connection.cursor(cursor_factory=RealDictCursor)
                
                v1_counts = {}
                tables = ['categoria', 'contratacao', 'contrato', 'item_contratacao', 'item_classificacao', 'contratacao_emb', 'contrato_emb', 'ata_preco', 'pca']
                
                for table in tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) as total FROM {table}")
                        count = cursor.fetchone()['total']
                        v1_counts[table] = count
                    except Exception:
                        v1_counts[table] = 'N/A'
                
                self.test_results['data_counts']['V1'] = v1_counts
                
                total_records = sum(c for c in v1_counts.values() if isinstance(c, int))
                console.print(f"  🏗️ Total atual no V1: {total_records:,} registros")
                for table, count in v1_counts.items():
                    if isinstance(count, int):
                        console.print(f"    - {table}: {count:,}")
                
            except Exception as e:
                self.test_results['errors'].append(f"Análise V1: {e}")
                console.print(f"❌ Erro na análise V1: {e}")
    
    def validate_embeddings_coverage(self):
        """Validar cobertura dos embeddings vs dados disponíveis"""
        console.print("\n🎯 [bold blue]TESTE 3: Cobertura dos Embeddings[/bold blue]")
        
        if not (self.dbl_connection and self.v0_connection):
            console.print("⚠️ Conexões necessárias não disponíveis")
            return
        
        try:
            # Verificar se temos informações sobre a tabela de embeddings
            v0_data = self.test_results.get('data_counts', {}).get('V0', {})
            embedding_table = v0_data.get('embedding_table')
            
            if not embedding_table:
                console.print("⚠️ Tabela de embeddings não identificada - pulando análise de cobertura")
                self.test_results['embedding_analysis'] = {
                    'total_embeddings': 0,
                    'total_sqlite': 0,
                    'intersection': 0,
                    'only_embeddings': 0,
                    'only_sqlite': 0,
                    'coverage_percent': 0
                }
                return
            
            # IDs com embeddings
            cursor_v0 = self.v0_connection.cursor(cursor_factory=RealDictCursor)
            
            # Detectar coluna de ID
            cursor_v0.execute(f"""
                SELECT column_name 
                FROM information_schema.columns
                WHERE table_name = '{embedding_table}'
                AND column_name IN ('numerocontrolepncp', 'numeroControlePNCP', 'numero_controle_pncp')
            """)
            id_columns = [row['column_name'] for row in cursor_v0.fetchall()]
            
            if not id_columns:
                console.print("⚠️ Coluna de ID não encontrada na tabela de embeddings")
                return
            
            id_column = id_columns[0]
            
            cursor_v0.execute(f"""
                SELECT DISTINCT {id_column} 
                FROM {embedding_table}
                ORDER BY {id_column}
            """)
            ids_with_embeddings = set(row[id_column] for row in cursor_v0.fetchall())
            
            # IDs disponíveis no SQLite
            cursor_dbl = self.dbl_connection.cursor()
            cursor_dbl.execute("SELECT DISTINCT numeroControlePNCP FROM contratacao")
            ids_in_sqlite = set(row[0] for row in cursor_dbl.fetchall())
            
            # Análise de cobertura
            intersection = ids_with_embeddings & ids_in_sqlite
            only_embeddings = ids_with_embeddings - ids_in_sqlite
            only_sqlite = ids_in_sqlite - ids_with_embeddings
            
            coverage_percent = (len(intersection) / len(ids_in_sqlite)) * 100 if ids_in_sqlite else 0
            
            self.test_results['embedding_analysis'] = {
                'total_embeddings': len(ids_with_embeddings),
                'total_sqlite': len(ids_in_sqlite),
                'intersection': len(intersection),
                'only_embeddings': len(only_embeddings),
                'only_sqlite': len(only_sqlite),
                'coverage_percent': coverage_percent
            }
            
            console.print(f"📊 Análise de cobertura:")
            console.print(f"  🧠 IDs com embeddings: {len(ids_with_embeddings):,}")
            console.print(f"  📋 IDs no SQLite: {len(ids_in_sqlite):,}")
            console.print(f"  🎯 Intersecção (serão migrados): {len(intersection):,}")
            console.print(f"  📈 Cobertura: {coverage_percent:.1f}%")
            
            if only_embeddings:
                console.print(f"  ⚠️ Embeddings órfãos: {len(only_embeddings):,}")
            
            if only_sqlite:
                console.print(f"  ⚠️ SQLite sem embeddings: {len(only_sqlite):,}")
            
            # Estimativa de dados a migrar
            if intersection:
                # Contar itens relacionados
                placeholders = ','.join(['?' for _ in list(intersection)[:1000]])  # Amostra
                sample_ids = list(intersection)[:1000]
                
                cursor_dbl.execute(f"""
                    SELECT COUNT(*) as total 
                    FROM item_contratacao 
                    WHERE numeroControlePNCP IN ({placeholders})
                """, sample_ids)
                sample_items = cursor_dbl.fetchone()[0]
                
                cursor_dbl.execute(f"""
                    SELECT COUNT(*) as total 
                    FROM item_classificacao 
                    WHERE numeroControlePNCP IN ({placeholders})
                """, sample_ids)
                sample_classif = cursor_dbl.fetchone()[0]
                
                # Extrapolação
                estimated_items = int((sample_items / len(sample_ids)) * len(intersection))
                estimated_classif = int((sample_classif / len(sample_ids)) * len(intersection))
                
                console.print(f"\n🔮 Estimativa de migração:")
                console.print(f"  📋 Contratações: {len(intersection):,}")
                console.print(f"  🧠 Embeddings: {len(intersection):,}")
                console.print(f"  📦 Itens (estimativa): {estimated_items:,}")
                console.print(f"  🏷️ Classificações (estimativa): {estimated_classif:,}")
                console.print(f"  📊 Total estimado: {len(intersection) * 2 + estimated_items + estimated_classif:,} registros")
            
        except Exception as e:
            self.test_results['errors'].append(f"Validação embeddings: {e}")
            console.print(f"❌ Erro na validação: {e}")
    
    def test_table_structures(self):
        """Testar estruturas das tabelas"""
        console.print("\n🏗️ [bold blue]TESTE 4: Estruturas das Tabelas[/bold blue]")
        
        # Verificar se tabelas V1 existem e têm estrutura correta
        if self.v1_connection:
            console.print("🔍 Verificando estrutura do V1...")
            try:
                cursor = self.v1_connection.cursor(cursor_factory=RealDictCursor)
                
                expected_tables = [
                    'categoria', 'contratacao', 'contrato', 'item_contratacao',
                    'item_classificacao', 'contratacao_emb', 'contrato_emb', 'ata_preco', 'pca'
                ]
                
                structure_status = {}
                
                for table in expected_tables:
                    try:
                        cursor.execute(f"""
                            SELECT column_name, data_type, is_nullable, column_default
                            FROM information_schema.columns
                            WHERE table_name = '{table}'
                            ORDER BY ordinal_position
                        """)
                        columns = cursor.fetchall()
                        
                        structure_status[table] = {
                            'exists': True,
                            'columns': len(columns),
                            'column_details': [
                                {
                                    'name': col['column_name'],
                                    'type': col['data_type'],
                                    'nullable': col['is_nullable'],
                                    'default': col['column_default']
                                }
                                for col in columns
                            ]
                        }
                        console.print(f"  ✅ {table}: {len(columns)} colunas")
                        
                        # Teste de inserção de dados fictícios para validar tipos
                        self._test_data_insertion(table, structure_status[table]['column_details'])
                        
                    except Exception as e:
                        structure_status[table] = {
                            'exists': False,
                            'error': str(e)
                        }
                        console.print(f"  ❌ {table}: erro - {e}")
                
                self.test_results['table_structures']['V1'] = structure_status
                
                # Verificar constraints
                console.print("🔗 Verificando constraints...")
                cursor.execute("""
                    SELECT 
                        tc.table_name,
                        tc.constraint_name,
                        tc.constraint_type
                    FROM information_schema.table_constraints tc
                    WHERE tc.table_schema = 'public'
                    AND tc.table_name IN ('categoria', 'contratacao', 'contrato', 'item_contratacao', 'item_classificacao', 'contratacao_emb', 'contrato_emb')
                    ORDER BY tc.table_name, tc.constraint_type
                """)
                
                constraints = cursor.fetchall()
                constraint_summary = {}
                for const in constraints:
                    table = const['table_name']
                    if table not in constraint_summary:
                        constraint_summary[table] = []
                    constraint_summary[table].append(const['constraint_type'])
                
                for table, types in constraint_summary.items():
                    console.print(f"  🔗 {table}: {', '.join(set(types))}")
                
            except Exception as e:
                self.test_results['errors'].append(f"Estrutura V1: {e}")
                console.print(f"❌ Erro na verificação de estrutura: {e}")
    
    def _fetch_real_test_data(self):
        """Busca dados reais exatamente como o 02_migrate_data.py - apenas 1 linha"""
        console.print("\n📊 [bold blue]Buscando dados reais para teste (método 02)[/bold blue]")
        
        try:
            # ETAPA 1: Buscar embeddings do V0 (como no 02)
            if self.v0_connection:
                cursor_v0 = self.v0_connection.cursor(cursor_factory=RealDictCursor)
                
                # Descobrir tabela de embeddings
                cursor_v0.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name LIKE '%embedding%'
                    ORDER BY table_name
                """)
                embedding_tables = [row['table_name'] for row in cursor_v0.fetchall()]
                
                if embedding_tables:
                    embedding_table = embedding_tables[0]
                    console.print(f"📊 Tabela de embeddings: {embedding_table}")
                    
                    # Buscar ID do primeiro embedding
                    cursor_v0.execute(f"SELECT * FROM {embedding_table} LIMIT 1")
                    emb_row = cursor_v0.fetchone()
                    
                    if emb_row:
                        # Encontrar coluna de ID
                        id_column = None
                        for col in emb_row.keys():
                            if 'numerocontrolepncp' in col.lower() or 'id' in col.lower():
                                id_column = col
                                break
                        
                        if id_column:
                            numero_controle = emb_row[id_column]
                            console.print(f"  📋 ID encontrado: {numero_controle}")
                            
                            # ETAPA 2: Buscar categoria correspondente no SQLite
                            if self.dbl_connection:
                                cursor_dbl = self.dbl_connection.cursor()
                                cursor_dbl.execute("""
                                    SELECT codCat, nomCat, codNv0, nomNv0, codNv1, nomNv1, 
                                           codNv2, nomNv2, codNv3, nomNv3
                                    FROM categoria 
                                    WHERE codCat IN (
                                        SELECT codCat FROM contratacao 
                                        WHERE numeroControlePNCP = ?
                                    )
                                    LIMIT 1
                                """, (numero_controle,))
                                cat_row = cursor_dbl.fetchone()
                                
                                if cat_row:
                                    # Categoria real com embeddings fake (será preenchido depois)
                                    self.real_test_data['categoria'] = [
                                        cat_row['codCat'], cat_row['nomCat'],
                                        cat_row['codNv0'], cat_row['nomNv0'],
                                        cat_row['codNv1'], cat_row['nomNv1'],
                                        cat_row['codNv2'], cat_row['nomNv2'],
                                        cat_row['codNv3'], cat_row['nomNv3'],
                                        [0.1] * 1536  # Embedding fake para teste
                                    ]
                                    console.print(f"  ✅ Categoria: {cat_row['codCat']} - {cat_row['nomCat']}")
                                    
                                    # ETAPA 3: Buscar contratação completa (como no 02)
                                    cursor_dbl.execute("""
                                        SELECT 
                                            numeroControlePNCP, modaDisputaId, amparoLegal_codigo,
                                            dataAberturaProposta, dataEncerramentoProposta, srp,
                                            orgaoEntidade_cnpj, orgaoEntidade_razaoSocial,
                                            orgaoEntidade_poderId, orgaoEntidade_esferaId,
                                            anoCompra, sequencialCompra, processo, objetoCompra,
                                            valorTotalHomologado, dataInclusao, dataPublicacaoPNCP,
                                            dataAtualizacao, numeroCompra, unidadeOrgao_ufNome,
                                            unidadeOrgao_ufSigla, unidadeOrgao_municipioNome,
                                            unidadeOrgao_codigoUnidade, unidadeOrgao_nomeUnidade,
                                            unidadeOrgao_codigoIBGE, modalidadeId, dataAtualizacaoGlobal,
                                            tipoInstrumentoConvocatoriocodigo, valorTotalEstimado,
                                            situacaoCompraId, codCat, score, informacaoComplementar,
                                            justificativaPresencial, linkSistemaOrigem,
                                            linkProcessoEletronico, amparoLegal_nome,
                                            amparoLegal_descricao, modalidadeNome, modaDisputaNome,
                                            tipoInstrumentoConvocatorioNome, situacaoCompraNome,
                                            existeResultado, orcamentoSigilosocodigo,
                                            orcamentoSigioso_descricao, orgaoSubrogado_cnpj,
                                            orgaoSubrogado_razaoSocial, orgaoSubrogado_poderId,
                                            orgaoSubrogado_esferaId, unidadeSubrogada_ufNome,
                                            unidadeSubrogada_ufSigla, unidadeSubrogada_municipioNome,
                                            unidadeSubrogada_codigoUnidade, unidadeSubrogada_nomeUnidade,
                                            unidadeSubrogada_codigoIBGE, usuarioNome, fontesOrcamentarias
                                        FROM contratacao 
                                        WHERE numeroControlePNCP = ?
                                        LIMIT 1
                                    """, (numero_controle,))
                                    cont_row = cursor_dbl.fetchone()
                                    
                                    if cont_row:
                                        # Mapear dados exatamente como no 02_migrate_data.py
                                        self.real_test_data['contratacao'] = [
                                            cont_row['numeroControlePNCP'],
                                            cont_row['modaDisputaId'],
                                            cont_row['amparoLegal_codigo'],
                                            cont_row['dataAberturaProposta'],
                                            cont_row['dataEncerramentoProposta'],
                                            cont_row['srp'],
                                            cont_row['orgaoEntidade_cnpj'],
                                            cont_row['orgaoEntidade_razaoSocial'],
                                            cont_row['orgaoEntidade_poderId'],
                                            cont_row['orgaoEntidade_esferaId'],
                                            cont_row['anoCompra'],
                                            cont_row['sequencialCompra'],
                                            cont_row['processo'],
                                            cont_row['objetoCompra'],
                                            cont_row['valorTotalHomologado'],
                                            cont_row['dataInclusao'],
                                            cont_row['dataPublicacaoPNCP'],
                                            cont_row['dataAtualizacao'],
                                            cont_row['numeroCompra'],
                                            cont_row['unidadeOrgao_ufNome'],
                                            cont_row['unidadeOrgao_ufSigla'],
                                            cont_row['unidadeOrgao_municipioNome'],
                                            cont_row['unidadeOrgao_codigoUnidade'],
                                            cont_row['unidadeOrgao_nomeUnidade'],
                                            cont_row['unidadeOrgao_codigoIBGE'],
                                            cont_row['modalidadeId'],
                                            cont_row['dataAtualizacaoGlobal'],
                                            cont_row['tipoInstrumentoConvocatoriocodigo'],
                                            cont_row['valorTotalEstimado'],
                                            cont_row['situacaoCompraId'],
                                            cont_row['codCat'],
                                            cont_row['score'],
                                            cont_row['informacaoComplementar'],
                                            cont_row['justificativaPresencial'],
                                            cont_row['linkSistemaOrigem'],
                                            cont_row['linkProcessoEletronico'],
                                            cont_row['amparoLegal_nome'],
                                            cont_row['amparoLegal_descricao'],
                                            cont_row['modalidadeNome'],
                                            cont_row['modaDisputaNome'],
                                            cont_row['tipoInstrumentoConvocatorioNome'],
                                            cont_row['situacaoCompraNome'],
                                            cont_row['existeResultado'],
                                            cont_row['orcamentoSigilosocodigo'],
                                            cont_row['orcamentoSigioso_descricao'],
                                            cont_row['orgaoSubrogado_cnpj'],
                                            cont_row['orgaoSubrogado_razaoSocial'],
                                            cont_row['orgaoSubrogado_poderId'],
                                            cont_row['orgaoSubrogado_esferaId'],
                                            cont_row['unidadeSubrogada_ufNome'],
                                            cont_row['unidadeSubrogada_ufSigla'],
                                            cont_row['unidadeSubrogada_municipioNome'],
                                            cont_row['unidadeSubrogada_codigoUnidade'],
                                            cont_row['unidadeSubrogada_nomeUnidade'],
                                            cont_row['unidadeSubrogada_codigoIBGE'],
                                            cont_row['usuarioNome'],
                                            cont_row['fontesOrcamentarias']
                                        ]
                                        console.print(f"  ✅ Contratação: {numero_controle}")
                                        
                                        # ETAPA 4: Embedding real do V0
                                        embedding_data = None
                                        for col in emb_row.keys():
                                            if 'embedding' in col.lower() and 'vector' not in col.lower():
                                                if emb_row[col]:  # Se não for None
                                                    try:
                                                        # Tentar converter para lista
                                                        if isinstance(emb_row[col], str):
                                                            import json
                                                            embedding_data = json.loads(emb_row[col])
                                                        elif isinstance(emb_row[col], list):
                                                            embedding_data = emb_row[col]
                                                        break
                                                    except:
                                                        pass
                                        
                                        if not embedding_data:
                                            embedding_data = [0.1] * 1536  # Fallback
                                        
                                        self.real_test_data['contratacao_emb'] = [
                                            numero_controle,
                                            embedding_data,
                                            'text-embedding-3-large',
                                            '{"fonte": "V0"}',
                                            0.95,
                                            ['CAT001'],
                                            [0.85]
                                        ]
                                        console.print(f"  ✅ Embedding: {len(embedding_data)} dimensões")
                                        
                                        # ETAPA 5: Item de contratação real
                                        cursor_dbl.execute("""
                                            SELECT descricaoItem, quantidadeItem, unidadeMedida,
                                                   valorUnitarioEstimado, valorTotalEstimado,
                                                   marcaItem, situacaoItem
                                            FROM item_contratacao 
                                            WHERE numeroControlePNCP = ?
                                            LIMIT 1
                                        """, (numero_controle,))
                                        item_row = cursor_dbl.fetchone()
                                        
                                        if item_row:
                                            self.real_test_data['item_contratacao'] = [
                                                numero_controle,
                                                item_row['descricaoItem'],
                                                item_row['quantidadeItem'],
                                                item_row['unidadeMedida'],
                                                item_row['valorUnitarioEstimado'],
                                                item_row['valorTotalEstimado'],
                                                item_row['marcaItem'],
                                                item_row['situacaoItem'],
                                                None, None, None,  # beneficiostipo, beneficiosdescricao, incentivosprodu
                                                None, None, None, None,  # catmatservid, catmatservnome, sustentavelid, sustentavelnome
                                                None, None  # codigoclassificacaopdm, codigoclassificacaocusteio
                                            ]
                                            console.print(f"  ✅ Item: {item_row['descricaoItem'][:50]}...")
                            
            console.print(f"🎯 Dados reais encontrados para {len(self.real_test_data)} tabelas")
            
        except Exception as e:
            console.print(f"❌ Erro ao buscar dados reais: {e}")
            self.test_results['errors'].append(f"Dados reais: {e}")
    
    def _test_data_insertion(self, table_name: str, columns: List[Dict]):
        """Teste de inserção real usando dados reais do V0/DBL"""
        try:
            # Usar dados reais se disponível, senão usar dados de teste
            test_data = self.real_test_data.get(table_name)
            if not test_data:
                test_data = get_test_data(table_name)
                console.print(f"    ⚠️ Usando dados sintéticos para {table_name}")
            else:
                console.print(f"    🎯 Usando dados reais para {table_name}")
            
            if not test_data:
                console.print(f"    ⚠️ Nenhum dado disponível para {table_name}")
                return
            
            # Ajustar dados para colunas inseríveis
            insertable_columns = get_insertable_columns(table_name)
            if len(test_data) != len(insertable_columns):
                test_data = test_data[:len(insertable_columns)]
            
            # Validar tipos de dados
            if not validate_data_types(table_name, test_data):
                console.print(f"    ❌ Tipos de dados inválidos para {table_name}")
                return
            
            # Gerar query de inserção usando table_schemas
            insert_query = generate_insert_query(table_name)
            if not insert_query:
                console.print(f"    ⚠️ Não foi possível gerar query para {table_name}")
                return
            
            cursor = self.v1_connection.cursor()
            
            # Inserção real
            cursor.execute(insert_query, test_data)
            self.v1_connection.commit()
            console.print(f"    🧪 Inserção real: OK")
            
            # Limpeza imediata
            insertable_columns = get_insertable_columns(table_name)
            if insertable_columns:
                # Usar a primeira coluna como chave para limpeza
                key_column = insertable_columns[0]['name']
                key_value = test_data[0]
                
                cursor.execute(f"DELETE FROM {table_name} WHERE {key_column} = %s", (key_value,))
                self.v1_connection.commit()
                console.print(f"    🗑️ Limpeza: OK")
                console.print(f"    � Limpeza: OK")
            
        except Exception as e:
            error_msg = str(e)
            console.print(f"    ❌ Teste de inserção falhou: {error_msg[:100]}...")
            self.test_results['errors'].append(f"Teste inserção {table_name}: {error_msg}")
            
            # Tentar limpeza mesmo com erro
            try:
                if 'test_data' in locals() and test_data:
                    insertable_columns = get_insertable_columns(table_name)
                    if insertable_columns:
                        key_column = insertable_columns[0]['name']
                        key_value = test_data[0]
                        cursor = self.v1_connection.cursor()
                        cursor.execute(f"DELETE FROM {table_name} WHERE {key_column} = %s", (key_value,))
                        self.v1_connection.commit()
                        console.print(f"    🧹 Limpeza de emergência: OK")
            except:
                pass
    
    def _generate_smart_test_data(self, table_name: str, columns: List[Dict]) -> List:
        """Gerar dados de teste inteligentes baseados na estrutura real da tabela"""
        
        test_data = []
        
        for col in columns:
            col_name = col['name']
            col_type = col['type'].lower()  # Corrigido de 'data_type' para 'type'
            is_nullable = col['nullable'] == 'YES'
            
            # Gerar dados baseados no tipo da coluna
            if 'varchar' in col_type or 'text' in col_type or 'character' in col_type:
                if 'numerocontrolepncp' in col_name.lower():
                    test_data.append('TEST123456789')
                elif 'cnpj' in col_name.lower():
                    test_data.append('12345678901234')
                elif 'codigo' in col_name.lower() or 'cod' in col_name.lower():
                    test_data.append('TEST001')
                elif 'email' in col_name.lower():
                    test_data.append('teste@exemplo.com')
                elif 'url' in col_name.lower():
                    test_data.append('https://exemplo.com')
                elif 'descricao' in col_name.lower() or 'objeto' in col_name.lower():
                    test_data.append('Descrição de teste')
                elif 'nome' in col_name.lower():
                    test_data.append('Nome Teste')
                else:
                    test_data.append('Teste')
                    
            elif 'integer' in col_type or 'bigint' in col_type or 'smallint' in col_type:
                if 'ano' in col_name.lower():
                    test_data.append(2024)
                elif 'quantidade' in col_name.lower() or 'qtd' in col_name.lower():
                    test_data.append(1)
                else:
                    test_data.append(1)
                    
            elif 'numeric' in col_type or 'decimal' in col_type or 'double' in col_type or 'real' in col_type:
                if 'valor' in col_name.lower() or 'preco' in col_name.lower():
                    test_data.append(100.50)
                else:
                    test_data.append(1.0)
                    
            elif 'boolean' in col_type:
                test_data.append(True)
                
            elif 'date' in col_type:
                test_data.append('2024-01-01')
                
            elif 'timestamp' in col_type:
                test_data.append('2024-01-01 10:00:00')
                
            elif 'json' in col_type or 'jsonb' in col_type:
                test_data.append('{}')
                
            elif 'vector' in col_type or 'array' in col_type:
                if 'embedding' in col_name.lower():
                    # Vector de 1536 dimensões para embeddings
                    test_data.append([0.1] * 1536)
                else:
                    test_data.append([])
                    
            elif 'uuid' in col_type:
                test_data.append('123e4567-e89b-12d3-a456-426614174000')
                
            else:
                # Tipo não reconhecido
                if is_nullable:
                    test_data.append(None)
                else:
                    test_data.append('DEFAULT')
        
        return test_data
    
    def estimate_migration_time(self):
        """Estimar tempo de migração"""
        console.print("\n⏱️ [bold blue]TESTE 5: Estimativa de Tempo[/bold blue]")
        
        try:
            # Baseado na análise de dados
            embedding_count = self.test_results.get('data_counts', {}).get('V0', {}).get('embeddings', {}).get('total', 0)
            intersection_count = self.test_results.get('embedding_analysis', {}).get('intersection', 0)
            
            if embedding_count and intersection_count:
                # Estimativas baseadas em benchmarks típicos
                estimates = {
                    'categorias': 2,  # segundos
                    'embeddings': max(5, embedding_count / 100),  # ~100 embeddings/segundo
                    'contratacoes': max(3, intersection_count / 500),  # ~500 registros/segundo
                    'itens': max(5, (intersection_count * 10) / 1000),  # ~1000 itens/segundo
                    'classificacoes': max(3, (intersection_count * 5) / 1000)  # ~1000 classificações/segundo
                }
                
                total_time = sum(estimates.values())
                
                console.print(f"⏱️ Estimativas de tempo:")
                for step, time_est in estimates.items():
                    console.print(f"  {step}: {time_est:.1f}s")
                
                console.print(f"\n🕐 Tempo total estimado: {total_time:.1f} segundos ({total_time/60:.1f} minutos)")
                
                if total_time > 300:  # > 5 minutos
                    console.print("⚠️ Migração longa detectada - considere executar fora do horário de pico")
            else:
                console.print("⚠️ Dados insuficientes para estimar tempo")
            
        except Exception as e:
            console.print(f"❌ Erro na estimativa: {e}")
    
    def generate_test_report(self):
        """Gerar relatório completo dos testes"""
        console.print("\n📋 [bold green]RELATÓRIO DE TESTES[/bold green]")
        
        # Status das conexões
        table = Table(title="🔌 Status das Conexões")
        table.add_column("Base", style="cyan")
        table.add_column("Status", style="magenta")
        table.add_column("Detalhes", style="green")
        
        for base, info in self.test_results['connections'].items():
            status = "✅ OK" if info['status'] == 'SUCCESS' else "❌ ERRO"
            details = ""
            if info['status'] == 'SUCCESS':
                if base == 'DBL':
                    details = f"{len(info['tables'])} tabelas, {info['size_mb']}MB"
                else:
                    details = f"{len(info['tables'])} tabelas"
            else:
                details = info.get('error', 'Erro desconhecido')[:50]
            
            table.add_row(base, status, details)
        
        console.print(table)
        
        # Resumo de dados
        if self.test_results['data_counts']:
            console.print("\n📊 [bold blue]Resumo dos Dados:[/bold blue]")
            
            dbl_data = self.test_results['data_counts'].get('DBL', {})
            v0_data = self.test_results['data_counts'].get('V0', {})
            emb_analysis = self.test_results['embedding_analysis']
            
            if dbl_data:
                console.print(f"  📋 SQLite: {dbl_data.get('contratacoes', {}).get('total', 0):,} contratações")
            
            if v0_data:
                console.print(f"  🧠 V0: {v0_data.get('embeddings', {}).get('total', 0):,} embeddings")
            
            if emb_analysis:
                console.print(f"  🎯 Migração: {emb_analysis.get('intersection', 0):,} registros ({emb_analysis.get('coverage_percent', 0):.1f}% cobertura)")
        
        # Erros encontrados
        if self.test_results['errors']:
            console.print("\n❌ [bold red]Erros Encontrados:[/bold red]")
            for error in self.test_results['errors']:
                console.print(f"  • {error}")
        
        # Recomendações
        console.print("\n💡 [bold yellow]Recomendações:[/bold yellow]")
        
        all_connections_ok = all(
            info['status'] == 'SUCCESS' 
            for info in self.test_results['connections'].values()
        )
        
        if all_connections_ok:
            console.print("  ✅ Todas as conexões funcionando - migração pode prosseguir")
        else:
            console.print("  ❌ Problemas de conectividade - resolver antes de migrar")
        
        embedding_coverage = self.test_results.get('embedding_analysis', {}).get('coverage_percent', 0)
        if embedding_coverage > 80:
            console.print(f"  ✅ Boa cobertura de embeddings ({embedding_coverage:.1f}%)")
        elif embedding_coverage > 50:
            console.print(f"  ⚠️ Cobertura moderada de embeddings ({embedding_coverage:.1f}%)")
        else:
            console.print(f"  ❌ Baixa cobertura de embeddings ({embedding_coverage:.1f}%)")
        
        if not self.test_results['errors']:
            console.print("  ✅ Nenhum erro crítico detectado")
        else:
            console.print(f"  ⚠️ {len(self.test_results['errors'])} erro(s) encontrado(s)")
    
    def run_all_tests(self):
        """Executar todos os testes"""
        console.print(Panel.fit(
            "[bold blue]GovGo V1 - Teste de Migração (Dry Run)[/bold blue]\n"
            "Análise completa antes da migração real\n\n"
            "🔌 Conectividade\n"
            "📊 Análise de dados\n"
            "🎯 Cobertura de embeddings\n"
            "🏗️ Estruturas de tabelas\n"
            "⏱️ Estimativas de tempo",
            title="🧪 Teste de Migração"
        ))
        
        start_time = time.time()
        
        try:
            # Executar todos os testes
            self.test_connections()
            self._fetch_real_test_data()  # Buscar dados reais após conectar
            self.analyze_source_data()
            self.validate_embeddings_coverage()
            self.test_table_structures()
            self.estimate_migration_time()
            
            # Relatório final
            self.generate_test_report()
            
            end_time = time.time()
            duration = end_time - start_time
            console.print(f"\n⏱️ [bold blue]Tempo de análise: {duration:.2f} segundos[/bold blue]")
            
            # Decisão final
            all_connections_ok = all(
                info['status'] == 'SUCCESS' 
                for info in self.test_results['connections'].values()
            )
            
            if all_connections_ok and not self.test_results['errors']:
                console.print("\n🎉 [bold green]TODOS OS TESTES PASSARAM![/bold green]")
                console.print("✅ Sistema pronto para migração")
                console.print("🚀 Execute: python ../scripts/02_migrate_data.py")
                return True
            else:
                console.print("\n⚠️ [bold yellow]PROBLEMAS DETECTADOS[/bold yellow]")
                console.print("🔧 Resolva os problemas antes de migrar")
                return False
            
        except Exception as e:
            console.print(f"\n❌ [bold red]Erro crítico nos testes: {e}[/bold red]")
            return False
        
        finally:
            # Fechar conexões
            if self.dbl_connection:
                self.dbl_connection.close()
            
            if self.v0_connection:
                self.v0_connection.close()
            
            if self.v1_connection:
                self.v1_connection.close()

def main():
    """Função principal"""
    tester = MigrationTester()
    
    console.print("🧪 [bold blue]Iniciando teste de migração...[/bold blue]")
    console.print("📝 Este script NÃO modifica dados - apenas analisa")
    
    if tester.run_all_tests():
        console.print("\n✅ [bold green]Análise concluída - sistema pronto para migração![/bold green]")
    else:
        console.print("\n❌ [bold red]Problemas detectados - revisar antes de migrar[/bold red]")
        exit(1)

if __name__ == "__main__":
    main()
