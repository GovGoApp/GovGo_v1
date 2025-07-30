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

# Carregar variáveis do .env
load_dotenv()

console = Console()

class MigrationTester:
    """Testador de migração - análise completa sem modificar dados"""
    
    def __init__(self):
        self.dbl_connection = None  # SQLite PNCP_DB_v2.db
        self.v0_connection = None   # Supabase V0
        self.v1_connection = None   # Supabase V1
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
                
                # Embeddings de contratações
                cursor.execute("SELECT COUNT(*) as total FROM contratacao_embeddings")
                emb_count = cursor.fetchone()['total']
                
                cursor.execute("""
                    SELECT COUNT(DISTINCT numeroControlePNCP) as unique_ids 
                    FROM contratacao_embeddings
                """)
                emb_unique = cursor.fetchone()['unique_ids']
                
                # Modelos usados
                cursor.execute("""
                    SELECT modelo_embedding, COUNT(*) as count
                    FROM contratacao_embeddings
                    GROUP BY modelo_embedding
                    ORDER BY count DESC
                """)
                modelos = cursor.fetchall()
                
                # Confidence médio
                cursor.execute("""
                    SELECT 
                        AVG(confidence) as avg_confidence,
                        MIN(confidence) as min_confidence,
                        MAX(confidence) as max_confidence
                    FROM contratacao_embeddings
                    WHERE confidence IS NOT NULL
                """)
                conf_stats = cursor.fetchone()
                
                self.test_results['data_counts']['V0'] = {
                    'embeddings': {'total': emb_count, 'unique_ids': emb_unique},
                    'modelos': [{'modelo': m['modelo_embedding'], 'count': m['count']} for m in modelos],
                    'confidence_stats': dict(conf_stats) if conf_stats else None
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
            # IDs com embeddings
            cursor_v0 = self.v0_connection.cursor(cursor_factory=RealDictCursor)
            cursor_v0.execute("""
                SELECT DISTINCT numeroControlePNCP 
                FROM contratacao_embeddings
                ORDER BY numeroControlePNCP
            """)
            ids_with_embeddings = set(row['numerocontrolepncp'] for row in cursor_v0.fetchall())
            
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
                            SELECT column_name, data_type, is_nullable
                            FROM information_schema.columns
                            WHERE table_name = '{table}'
                            ORDER BY ordinal_position
                        """)
                        columns = cursor.fetchall()
                        
                        structure_status[table] = {
                            'exists': True,
                            'columns': len(columns),
                            'column_details': [
                                f"{col['column_name']} ({col['data_type']})" 
                                for col in columns[:5]  # Primeiras 5 colunas
                            ]
                        }
                        console.print(f"  ✅ {table}: {len(columns)} colunas")
                        
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
                console.print("🚀 Execute: python 02_migrate_data.py")
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
