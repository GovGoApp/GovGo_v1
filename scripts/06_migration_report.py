#!/usr/bin/env python3
"""
GovGo V1 - 06 - Relatório Final de Migração
============================================
Gera relatório completo da migração V0->V1
Valida integridade e performance da nova base

EXECUÇÃO: Após 05_reconcile_data.py
RESULTADO: Relatório final e validação completa
"""

import os
import sys
import json
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
import sqlite3

# Adicionar o diretório pai ao path
sys.path.append(str(os.path.dirname(os.path.dirname(__file__))))

from core.config import config
from core.utils import configurar_logging

console = Console()
configurar_logging()

class MigrationReporter:
    """Gerador de relatório final da migração V0->V1"""
    
    def __init__(self):
        self.supabase_connection = None
        self.sqlite_connection = None
        self.relatorio = {
            "data_relatorio": datetime.now().isoformat(),
            "versao_origem": "V0 (SQLite)",
            "versao_destino": "V1 (Supabase)",
            "status_migracao": "unknown",
            "estatisticas": {},
            "comparacao_dados": {},
            "validacoes": {},
            "performance": {},
            "recomendacoes": []
        }
        
    def connect_databases(self):
        """Conecta aos bancos de dados V0 (SQLite) e V1 (Supabase)"""
        try:
            # Conectar Supabase V1
            self.supabase_connection = psycopg2.connect(
                host=config.supabase_host,
                database=config.supabase_database,
                user=config.supabase_user,
                password=config.supabase_password,
                port=config.supabase_port
            )
            console.print("✅ Conectado ao Supabase V1")
            
            # Conectar SQLite V0
            sqlite_path = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "v0", "database", "govgo.db"
            )
            
            if os.path.exists(sqlite_path):
                self.sqlite_connection = sqlite3.connect(sqlite_path)
                self.sqlite_connection.row_factory = sqlite3.Row
                console.print("✅ Conectado ao SQLite V0")
                return True
            else:
                console.print(f"❌ Banco SQLite não encontrado: {sqlite_path}")
                return False
                
        except Exception as e:
            console.print(f"❌ Erro ao conectar aos bancos: {e}")
            return False
    
    def coletar_estatisticas_v0(self):
        """Coleta estatísticas do banco V0 (SQLite)"""
        console.print(Panel("📊 Coletando estatísticas V0 (SQLite)", style="blue"))
        
        stats_v0 = {}
        
        try:
            cursor = self.sqlite_connection.cursor()
            
            # Contagem por tabela
            tabelas_v0 = ['contratacao', 'contrato', 'item_contratacao', 'item_classificacao', 'categoria']
            
            for tabela in tabelas_v0:
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM {tabela}")
                    count = cursor.fetchone()[0]
                    stats_v0[f"{tabela}_count"] = count
                    console.print(f"  • {tabela}: {count:,} registros")
                except Exception as e:
                    stats_v0[f"{tabela}_count"] = 0
                    console.print(f"  • {tabela}: 0 registros (erro: {e})")
            
            # Período dos dados
            try:
                cursor.execute("""
                    SELECT MIN(ano_compra) as ano_min, MAX(ano_compra) as ano_max,
                           COUNT(DISTINCT ano_compra) as anos_distintos
                    FROM contratacao
                """)
                periodo = cursor.fetchone()
                if periodo and periodo[0]:
                    stats_v0["periodo_dados"] = f"{periodo[0]} - {periodo[1]}"
                    stats_v0["anos_dados"] = periodo[2]
                    console.print(f"  • Período: {periodo[0]} - {periodo[1]} ({periodo[2]} anos)")
            except:
                stats_v0["periodo_dados"] = "N/A"
                stats_v0["anos_dados"] = 0
            
            # Órgãos únicos
            try:
                cursor.execute("SELECT COUNT(DISTINCT orgao_entidade_cnpj) FROM contratacao")
                orgaos = cursor.fetchone()[0]
                stats_v0["orgaos_unicos"] = orgaos
                console.print(f"  • Órgãos únicos: {orgaos:,}")
            except:
                stats_v0["orgaos_unicos"] = 0
            
            self.relatorio["estatisticas"]["v0"] = stats_v0
            return stats_v0
            
        except Exception as e:
            console.print(f"❌ Erro ao coletar estatísticas V0: {e}")
            return {}
    
    def coletar_estatisticas_v1(self):
        """Coleta estatísticas do banco V1 (Supabase)"""
        console.print(Panel("📊 Coletando estatísticas V1 (Supabase)", style="green"))
        
        stats_v1 = {}
        
        try:
            with self.supabase_connection.cursor(cursor_factory=RealDictCursor) as cursor:
                
                # Contagem por tabela
                tabelas_v1 = ['contratacoes', 'contratos', 'itens_contratacao', 'classificacoes_itens', 'categorias', 'atas', 'pcas']
                
                for tabela in tabelas_v1:
                    try:
                        cursor.execute(f"SELECT COUNT(*) as total FROM {tabela}")
                        count = cursor.fetchone()["total"]
                        stats_v1[f"{tabela}_count"] = count
                        console.print(f"  • {tabela}: {count:,} registros")
                    except Exception as e:
                        stats_v1[f"{tabela}_count"] = 0
                        console.print(f"  • {tabela}: 0 registros (erro: {e})")
                
                # Período dos dados
                try:
                    cursor.execute("""
                        SELECT MIN(ano_compra) as ano_min, MAX(ano_compra) as ano_max,
                               COUNT(DISTINCT ano_compra) as anos_distintos
                        FROM contratacoes
                    """)
                    periodo = cursor.fetchone()
                    if periodo and periodo["ano_min"]:
                        stats_v1["periodo_dados"] = f"{periodo['ano_min']} - {periodo['ano_max']}"
                        stats_v1["anos_dados"] = periodo["anos_distintos"]
                        console.print(f"  • Período: {periodo['ano_min']} - {periodo['ano_max']} ({periodo['anos_distintos']} anos)")
                except:
                    stats_v1["periodo_dados"] = "N/A"
                    stats_v1["anos_dados"] = 0
                
                # Órgãos únicos
                try:
                    cursor.execute("SELECT COUNT(DISTINCT orgao_entidade_cnpj) as total FROM contratacoes")
                    orgaos = cursor.fetchone()["total"]
                    stats_v1["orgaos_unicos"] = orgaos
                    console.print(f"  • Órgãos únicos: {orgaos:,}")
                except:
                    stats_v1["orgaos_unicos"] = 0
                
                # Dados por fonte
                try:
                    cursor.execute("""
                        SELECT data_source, COUNT(*) as total 
                        FROM contratacoes 
                        GROUP BY data_source
                    """)
                    fontes = {row["data_source"]: row["total"] for row in cursor.fetchall()}
                    stats_v1["dados_por_fonte"] = fontes
                    console.print("  • Dados por fonte:")
                    for fonte, total in fontes.items():
                        console.print(f"    - {fonte}: {total:,}")
                except:
                    stats_v1["dados_por_fonte"] = {}
                
                # Dados novos (ATAs e PCAs)
                stats_v1["dados_novos"] = {
                    "atas": stats_v1.get("atas_count", 0),
                    "pcas": stats_v1.get("pcas_count", 0)
                }
                
                console.print(f"  • Novos dados (ATAs): {stats_v1['dados_novos']['atas']:,}")
                console.print(f"  • Novos dados (PCAs): {stats_v1['dados_novos']['pcas']:,}")
                
                self.relatorio["estatisticas"]["v1"] = stats_v1
                return stats_v1
                
        except Exception as e:
            console.print(f"❌ Erro ao coletar estatísticas V1: {e}")
            return {}
    
    def comparar_dados_migrados(self):
        """Compara dados entre V0 e V1 para validar migração"""
        console.print(Panel("🔍 Comparando dados migrados", style="yellow"))
        
        comparacao = {}
        
        try:
            stats_v0 = self.relatorio["estatisticas"].get("v0", {})
            stats_v1 = self.relatorio["estatisticas"].get("v1", {})
            
            # Mapeamento de tabelas V0 -> V1
            mapeamento = {
                "contratacao": "contratacoes",
                "contrato": "contratos", 
                "item_contratacao": "itens_contratacao",
                "item_classificacao": "classificacoes_itens",
                "categoria": "categorias"
            }
            
            for tabela_v0, tabela_v1 in mapeamento.items():
                count_v0 = stats_v0.get(f"{tabela_v0}_count", 0)
                count_v1 = stats_v1.get(f"{tabela_v1}_count", 0)
                
                diferenca = count_v1 - count_v0
                percentual = (diferenca / count_v0 * 100) if count_v0 > 0 else 0
                
                comparacao[tabela_v0] = {
                    "v0": count_v0,
                    "v1": count_v1,
                    "diferenca": diferenca,
                    "percentual": round(percentual, 2),
                    "status": "OK" if abs(percentual) <= 5 else "ATENÇÃO" if abs(percentual) <= 15 else "ERRO"
                }
                
                status_emoji = "✅" if comparacao[tabela_v0]["status"] == "OK" else "⚠️" if comparacao[tabela_v0]["status"] == "ATENÇÃO" else "❌"
                console.print(f"  {status_emoji} {tabela_v0}: {count_v0:,} → {count_v1:,} ({diferenca:+,} | {percentual:+.1f}%)")
            
            self.relatorio["comparacao_dados"] = comparacao
            return comparacao
            
        except Exception as e:
            console.print(f"❌ Erro ao comparar dados: {e}")
            return {}
    
    def validar_integridade_final(self):
        """Validação final de integridade dos dados"""
        console.print(Panel("🔍 Validação final de integridade", style="cyan"))
        
        validacoes = {}
        
        try:
            with self.supabase_connection.cursor(cursor_factory=RealDictCursor) as cursor:
                
                # 1. Chaves estrangeiras
                console.print("  🔗 Validando chaves estrangeiras...")
                
                # Contratos sem contratação
                cursor.execute("""
                    SELECT COUNT(*) as total
                    FROM contratos c
                    LEFT JOIN contratacoes ct ON c.numero_controle_pncp_compra = ct.numero_controle_pncp
                    WHERE ct.numero_controle_pncp IS NULL 
                      AND c.numero_controle_pncp_compra IS NOT NULL
                """)
                contratos_orfaos = cursor.fetchone()["total"]
                
                # Itens sem contratação
                cursor.execute("""
                    SELECT COUNT(*) as total
                    FROM itens_contratacao i
                    LEFT JOIN contratacoes c ON i.numero_controle_pncp = c.numero_controle_pncp
                    WHERE c.numero_controle_pncp IS NULL
                """)
                itens_orfaos = cursor.fetchone()["total"]
                
                validacoes["integridade_referencial"] = {
                    "contratos_orfaos": contratos_orfaos,
                    "itens_orfaos": itens_orfaos,
                    "status": "OK" if (contratos_orfaos + itens_orfaos) == 0 else "ERRO"
                }
                
                console.print(f"    • Contratos órfãos: {contratos_orfaos}")
                console.print(f"    • Itens órfãos: {itens_orfaos}")
                
                # 2. Dados obrigatórios
                console.print("  📋 Validando campos obrigatórios...")
                
                cursor.execute("SELECT COUNT(*) as total FROM contratacoes WHERE numero_controle_pncp IS NULL")
                contratacoes_sem_numero = cursor.fetchone()["total"]
                
                cursor.execute("SELECT COUNT(*) as total FROM contratacoes WHERE orgao_entidade_cnpj IS NULL")
                contratacoes_sem_cnpj = cursor.fetchone()["total"]
                
                validacoes["campos_obrigatorios"] = {
                    "contratacoes_sem_numero": contratacoes_sem_numero,
                    "contratacoes_sem_cnpj": contratacoes_sem_cnpj,
                    "status": "OK" if (contratacoes_sem_numero + contratacoes_sem_cnpj) == 0 else "ATENÇÃO"
                }
                
                console.print(f"    • Contratações sem número: {contratacoes_sem_numero}")
                console.print(f"    • Contratações sem CNPJ: {contratacoes_sem_cnpj}")
                
                # 3. Duplicatas
                console.print("  🔄 Verificando duplicatas...")
                
                cursor.execute("""
                    SELECT COUNT(*) as total FROM (
                        SELECT numero_controle_pncp, COUNT(*) 
                        FROM contratacoes 
                        GROUP BY numero_controle_pncp 
                        HAVING COUNT(*) > 1
                    ) t
                """)
                duplicatas_contratacoes = cursor.fetchone()["total"]
                
                cursor.execute("""
                    SELECT COUNT(*) as total FROM (
                        SELECT numero_controle_pncp, COUNT(*) 
                        FROM contratos 
                        WHERE numero_controle_pncp IS NOT NULL
                        GROUP BY numero_controle_pncp 
                        HAVING COUNT(*) > 1
                    ) t
                """)
                duplicatas_contratos = cursor.fetchone()["total"]
                
                validacoes["duplicatas"] = {
                    "contratacoes": duplicatas_contratacoes,
                    "contratos": duplicatas_contratos,
                    "status": "OK" if (duplicatas_contratacoes + duplicatas_contratos) == 0 else "ATENÇÃO"
                }
                
                console.print(f"    • Duplicatas em contratações: {duplicatas_contratacoes}")
                console.print(f"    • Duplicatas em contratos: {duplicatas_contratos}")
                
                self.relatorio["validacoes"] = validacoes
                return validacoes
                
        except Exception as e:
            console.print(f"❌ Erro na validação: {e}")
            return {}
    
    def testar_performance(self):
        """Testa performance das consultas principais"""
        console.print(Panel("⚡ Testando performance", style="magenta"))
        
        performance = {}
        
        try:
            with self.supabase_connection.cursor(cursor_factory=RealDictCursor) as cursor:
                
                # Teste 1: Consulta simples por ano
                inicio = datetime.now()
                cursor.execute("""
                    SELECT COUNT(*) as total 
                    FROM contratacoes 
                    WHERE ano_compra = 2023
                """)
                resultado = cursor.fetchone()
                tempo_consulta_ano = (datetime.now() - inicio).total_seconds()
                
                performance["consulta_por_ano"] = {
                    "tempo_segundos": round(tempo_consulta_ano, 3),
                    "registros": resultado["total"] if resultado else 0,
                    "status": "OK" if tempo_consulta_ano < 1.0 else "LENTO"
                }
                
                # Teste 2: Join complexo
                inicio = datetime.now()
                cursor.execute("""
                    SELECT c.numero_controle_pncp, c.objeto_contrato, 
                           COUNT(i.id) as total_itens,
                           SUM(i.valor_estimado_item) as valor_total
                    FROM contratacoes c
                    LEFT JOIN itens_contratacao i ON c.numero_controle_pncp = i.numero_controle_pncp
                    WHERE c.ano_compra >= 2022
                    GROUP BY c.numero_controle_pncp, c.objeto_contrato
                    LIMIT 100
                """)
                resultados = cursor.fetchall()
                tempo_join = (datetime.now() - inicio).total_seconds()
                
                performance["join_complexo"] = {
                    "tempo_segundos": round(tempo_join, 3),
                    "registros": len(resultados),
                    "status": "OK" if tempo_join < 2.0 else "LENTO"
                }
                
                # Teste 3: Busca por texto
                inicio = datetime.now()
                cursor.execute("""
                    SELECT COUNT(*) as total
                    FROM contratacoes 
                    WHERE objeto_contrato ILIKE '%equipamento%'
                    LIMIT 1000
                """)
                resultado = cursor.fetchone()
                tempo_busca = (datetime.now() - inicio).total_seconds()
                
                performance["busca_texto"] = {
                    "tempo_segundos": round(tempo_busca, 3),
                    "registros": resultado["total"] if resultado else 0,
                    "status": "OK" if tempo_busca < 3.0 else "LENTO"
                }
                
                # Status geral de performance
                todos_ok = all(teste["status"] == "OK" for teste in performance.values())
                performance["status_geral"] = "OK" if todos_ok else "ATENÇÃO"
                
                console.print(f"  • Consulta por ano: {performance['consulta_por_ano']['tempo_segundos']}s")
                console.print(f"  • Join complexo: {performance['join_complexo']['tempo_segundos']}s") 
                console.print(f"  • Busca por texto: {performance['busca_texto']['tempo_segundos']}s")
                
                self.relatorio["performance"] = performance
                return performance
                
        except Exception as e:
            console.print(f"❌ Erro no teste de performance: {e}")
            return {}
    
    def gerar_recomendacoes(self):
        """Gera recomendações baseadas na análise"""
        console.print(Panel("💡 Gerando recomendações", style="green"))
        
        recomendacoes = []
        
        # Baseado na comparação de dados
        comparacao = self.relatorio.get("comparacao_dados", {})
        for tabela, dados in comparacao.items():
            if dados["status"] == "ERRO":
                recomendacoes.append({
                    "tipo": "CRÍTICO",
                    "categoria": "Integridade de Dados",
                    "problema": f"Grande divergência na tabela {tabela} ({dados['percentual']:+.1f}%)",
                    "solucao": "Revisar processo de migração e verificar filtros aplicados"
                })
            elif dados["status"] == "ATENÇÃO":
                recomendacoes.append({
                    "tipo": "ATENÇÃO",
                    "categoria": "Integridade de Dados", 
                    "problema": f"Pequena divergência na tabela {tabela} ({dados['percentual']:+.1f}%)",
                    "solucao": "Monitorar e investigar causas da diferença"
                })
        
        # Baseado nas validações
        validacoes = self.relatorio.get("validacoes", {})
        
        if validacoes.get("integridade_referencial", {}).get("status") == "ERRO":
            recomendacoes.append({
                "tipo": "CRÍTICO",
                "categoria": "Integridade Referencial",
                "problema": "Registros órfãos encontrados",
                "solucao": "Executar limpeza de dados e revalidar chaves estrangeiras"
            })
        
        if validacoes.get("duplicatas", {}).get("status") == "ATENÇÃO":
            recomendacoes.append({
                "tipo": "ATENÇÃO",
                "categoria": "Qualidade dos Dados",
                "problema": "Duplicatas encontradas",
                "solucao": "Executar processo de deduplicação"
            })
        
        # Baseado na performance
        performance = self.relatorio.get("performance", {})
        if performance.get("status_geral") == "ATENÇÃO":
            recomendacoes.append({
                "tipo": "ATENÇÃO",
                "categoria": "Performance",
                "problema": "Consultas lentas detectadas",
                "solucao": "Criar índices adicionais e otimizar consultas"
            })
        
        # Recomendações gerais
        stats_v1 = self.relatorio["estatisticas"].get("v1", {})
        if stats_v1.get("dados_novos", {}).get("atas", 0) > 0:
            recomendacoes.append({
                "tipo": "SUCESSO",
                "categoria": "Novos Dados",
                "problema": f"ATAs coletadas: {stats_v1['dados_novos']['atas']:,}",
                "solucao": "Implementar coleta automática periódica"
            })
        
        if stats_v1.get("dados_novos", {}).get("pcas", 0) > 0:
            recomendacoes.append({
                "tipo": "SUCESSO", 
                "categoria": "Novos Dados",
                "problema": f"PCAs coletados: {stats_v1['dados_novos']['pcas']:,}",
                "solucao": "Implementar coleta automática anual"
            })
        
        # Mostrar recomendações
        for rec in recomendacoes:
            emoji = "🔴" if rec["tipo"] == "CRÍTICO" else "🟡" if rec["tipo"] == "ATENÇÃO" else "🟢"
            console.print(f"  {emoji} [{rec['categoria']}] {rec['problema']}")
            console.print(f"     💡 {rec['solucao']}")
        
        self.relatorio["recomendacoes"] = recomendacoes
        return recomendacoes
    
    def determinar_status_final(self):
        """Determina o status final da migração"""
        comparacao = self.relatorio.get("comparacao_dados", {})
        validacoes = self.relatorio.get("validacoes", {})
        
        # Verificar se há erros críticos
        erros_criticos = 0
        atencoes = 0
        
        for dados in comparacao.values():
            if dados["status"] == "ERRO":
                erros_criticos += 1
            elif dados["status"] == "ATENÇÃO":
                atencoes += 1
        
        for validacao in validacoes.values():
            if validacao.get("status") == "ERRO":
                erros_criticos += 1
            elif validacao.get("status") == "ATENÇÃO":
                atencoes += 1
        
        if erros_criticos > 0:
            status = "FALHA"
        elif atencoes > 2:
            status = "PARCIAL"
        else:
            status = "SUCESSO"
        
        self.relatorio["status_migracao"] = status
        return status
    
    def salvar_relatorio_completo(self):
        """Salva o relatório completo em múltiplos formatos"""
        console.print(Panel("💾 Salvando relatório completo", style="cyan"))
        
        # 1. JSON completo
        with open("relatorio_migracao_completo.json", "w", encoding="utf-8") as f:
            json.dump(self.relatorio, f, indent=2, ensure_ascii=False)
        console.print("  ✅ JSON: relatorio_migracao_completo.json")
        
        # 2. Resumo em texto
        with open("relatorio_migracao_resumo.txt", "w", encoding="utf-8") as f:
            f.write("RELATÓRIO DE MIGRAÇÃO GOVGO V0 → V1\n")
            f.write("=" * 50 + "\n\n")
            f.write(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}\n")
            f.write(f"Status: {self.relatorio['status_migracao']}\n\n")
            
            # Estatísticas
            f.write("ESTATÍSTICAS:\n")
            f.write("-" * 20 + "\n")
            stats_v0 = self.relatorio["estatisticas"].get("v0", {})
            stats_v1 = self.relatorio["estatisticas"].get("v1", {})
            
            f.write(f"V0 (SQLite):\n")
            f.write(f"  - Contratações: {stats_v0.get('contratacao_count', 0):,}\n")
            f.write(f"  - Contratos: {stats_v0.get('contrato_count', 0):,}\n")
            f.write(f"  - Itens: {stats_v0.get('item_contratacao_count', 0):,}\n\n")
            
            f.write(f"V1 (Supabase):\n")
            f.write(f"  - Contratações: {stats_v1.get('contratacoes_count', 0):,}\n")
            f.write(f"  - Contratos: {stats_v1.get('contratos_count', 0):,}\n")
            f.write(f"  - Itens: {stats_v1.get('itens_contratacao_count', 0):,}\n")
            f.write(f"  - ATAs: {stats_v1.get('atas_count', 0):,}\n")
            f.write(f"  - PCAs: {stats_v1.get('pcas_count', 0):,}\n\n")
            
            # Recomendações
            f.write("RECOMENDAÇÕES:\n")
            f.write("-" * 20 + "\n")
            for rec in self.relatorio.get("recomendacoes", []):
                f.write(f"[{rec['tipo']}] {rec['categoria']}: {rec['problema']}\n")
                f.write(f"  → {rec['solucao']}\n\n")
        
        console.print("  ✅ TXT: relatorio_migracao_resumo.txt")
        
        # 3. CSV com comparação
        if self.relatorio.get("comparacao_dados"):
            df_comparacao = pd.DataFrame(self.relatorio["comparacao_dados"]).T
            df_comparacao.to_csv("comparacao_dados_migracao.csv", encoding="utf-8-sig")
            console.print("  ✅ CSV: comparacao_dados_migracao.csv")
    
    def gerar_relatorio_completo(self):
        """Gera o relatório completo da migração"""
        console.print(Panel.fit(
            "[bold blue]GovGo V1 - Relatório Final de Migração[/bold blue]\n"
            "Validação completa da migração V0 → V1:\n"
            "• Comparação de dados\n"
            "• Validação de integridade\n"
            "• Teste de performance\n"
            "• Recomendações finais",
            title="📊 Migration Reporter"
        ))
        
        if not self.connect_databases():
            return False
        
        try:
            # 1. Coletar estatísticas
            self.coletar_estatisticas_v0()
            self.coletar_estatisticas_v1()
            
            # 2. Comparar dados
            self.comparar_dados_migrados()
            
            # 3. Validar integridade
            self.validar_integridade_final()
            
            # 4. Testar performance
            self.testar_performance()
            
            # 5. Gerar recomendações
            self.gerar_recomendacoes()
            
            # 6. Determinar status final
            status = self.determinar_status_final()
            
            # 7. Salvar relatório
            self.salvar_relatorio_completo()
            
            # 8. Mostrar resumo final
            self._mostrar_resumo_final(status)
            
            return True
            
        except Exception as e:
            console.print(f"\n❌ [bold red]Erro ao gerar relatório: {e}[/bold red]")
            return False
        
        finally:
            if self.supabase_connection:
                self.supabase_connection.close()
            if self.sqlite_connection:
                self.sqlite_connection.close()
            console.print("🔌 Conexões fechadas")
    
    def _mostrar_resumo_final(self, status):
        """Mostra resumo final da migração"""
        console.print("\n" + "="*60)
        
        if status == "SUCESSO":
            console.print("🎉 [bold green]MIGRAÇÃO CONCLUÍDA COM SUCESSO![/bold green]")
            emoji = "✅"
        elif status == "PARCIAL":
            console.print("⚠️ [bold yellow]MIGRAÇÃO CONCLUÍDA COM RESSALVAS[/bold yellow]")
            emoji = "🟡"
        else:
            console.print("❌ [bold red]MIGRAÇÃO COM PROBLEMAS CRÍTICOS[/bold red]")
            emoji = "🔴"
        
        # Resumo dos dados
        stats_v0 = self.relatorio["estatisticas"].get("v0", {})
        stats_v1 = self.relatorio["estatisticas"].get("v1", {})
        
        table = Table(title=f"{emoji} Resumo da Migração")
        table.add_column("Métrica", style="cyan")
        table.add_column("V0 (SQLite)", style="blue")
        table.add_column("V1 (Supabase)", style="green")
        table.add_column("Status", style="yellow")
        
        # Dados principais
        comparacao = self.relatorio.get("comparacao_dados", {})
        
        table.add_row(
            "Contratações",
            f"{stats_v0.get('contratacao_count', 0):,}",
            f"{stats_v1.get('contratacoes_count', 0):,}",
            comparacao.get("contratacao", {}).get("status", "N/A")
        )
        
        table.add_row(
            "Contratos", 
            f"{stats_v0.get('contrato_count', 0):,}",
            f"{stats_v1.get('contratos_count', 0):,}",
            comparacao.get("contrato", {}).get("status", "N/A")
        )
        
        table.add_row(
            "Itens",
            f"{stats_v0.get('item_contratacao_count', 0):,}",
            f"{stats_v1.get('itens_contratacao_count', 0):,}",
            comparacao.get("item_contratacao", {}).get("status", "N/A")
        )
        
        # Dados novos
        table.add_row("ATAs", "0", f"{stats_v1.get('atas_count', 0):,}", "NOVO ✨")
        table.add_row("PCAs", "0", f"{stats_v1.get('pcas_count', 0):,}", "NOVO ✨")
        
        console.print(table)
        
        # Recomendações críticas
        recomendacoes_criticas = [
            r for r in self.relatorio.get("recomendacoes", []) 
            if r["tipo"] == "CRÍTICO"
        ]
        
        if recomendacoes_criticas:
            console.print("\n🔴 [bold red]AÇÕES CRÍTICAS NECESSÁRIAS:[/bold red]")
            for rec in recomendacoes_criticas:
                console.print(f"  • {rec['problema']}")
                console.print(f"    💡 {rec['solucao']}")
        
        console.print(f"\n📊 Relatórios salvos:")
        console.print("  • relatorio_migracao_completo.json")
        console.print("  • relatorio_migracao_resumo.txt")
        console.print("  • comparacao_dados_migracao.csv")
        
        console.print("\n" + "="*60)

def main():
    """Função principal"""
    reporter = MigrationReporter()
    
    if reporter.gerar_relatorio_completo():
        console.print("\n🎯 [bold green]Relatório de migração gerado com sucesso![/bold green]")
        console.print("\n🚀 [bold blue]FASE 3 CONCLUÍDA![/bold blue]")
        console.print("A migração GovGo V0 → V1 foi finalizada.")
    else:
        console.print("\n❌ [bold red]Falha ao gerar relatório de migração[/bold red]")
        exit(1)

if __name__ == "__main__":
    main()
