#!/usr/bin/env python3
"""
GovGo V1 - 05 - Reconciliação de Dados
=======================================
Reconcilia dados migrados do local com dados coletados via API
Resolve conflitos e duplicatas

EXECUÇÃO: Após 04_collect_from_api.py
PRÓXIMO: 06_migration_report.py
"""

import os
import sys
import json
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from difflib import SequenceMatcher

# Adicionar o diretório pai ao path
sys.path.append(str(os.path.dirname(os.path.dirname(__file__))))

from core.config import config
from core.utils import configurar_logging

console = Console()
configurar_logging()

class DataReconciliator:
    """Reconciliador de dados entre migração local e coleta API"""
    
    def __init__(self):
        self.connection = None
        self.stats = {
            "duplicatas_encontradas": 0,
            "duplicatas_resolvidas": 0,
            "conflitos_dados": 0,
            "conflitos_resolvidos": 0,
            "registros_unificados": 0,
            "dados_complementados": 0
        }
        self.conflitos_detectados = []
        
    def connect_database(self):
        """Conecta ao banco de dados Supabase"""
        try:
            self.connection = psycopg2.connect(
                host=config.supabase_host,
                database=config.supabase_database,
                user=config.supabase_user,
                password=config.supabase_password,
                port=config.supabase_port
            )
            console.print("✅ Conectado ao Supabase com sucesso!")
            return True
        except Exception as e:
            console.print(f"❌ Erro ao conectar: {e}")
            return False
    
    def detectar_duplicatas_contratacoes(self):
        """Detecta duplicatas na tabela contratacoes"""
        console.print(Panel("🔍 Detectando duplicatas em contratações", style="blue"))
        
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                # Buscar registros com mesmo número de controle
                cursor.execute("""
                    SELECT numero_controle_pncp, COUNT(*) as total,
                           MIN(id) as id_manter, 
                           ARRAY_AGG(id ORDER BY created_at ASC) as todos_ids,
                           ARRAY_AGG(data_source ORDER BY created_at ASC) as fontes
                    FROM contratacoes
                    GROUP BY numero_controle_pncp
                    HAVING COUNT(*) > 1
                    ORDER BY total DESC
                """)
                
                duplicatas = cursor.fetchall()
                self.stats["duplicatas_encontradas"] += len(duplicatas)
                
                if duplicatas:
                    console.print(f"⚠️ Encontradas {len(duplicatas)} duplicatas em contratações")
                    return duplicatas
                else:
                    console.print("✅ Nenhuma duplicata encontrada em contratações")
                    return []
                    
        except Exception as e:
            console.print(f"❌ Erro ao detectar duplicatas: {e}")
            return []
    
    def detectar_duplicatas_contratos(self):
        """Detecta duplicatas na tabela contratos"""
        console.print(Panel("🔍 Detectando duplicatas em contratos", style="blue"))
        
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                # Buscar registros com mesmo número de controle
                cursor.execute("""
                    SELECT numero_controle_pncp, COUNT(*) as total,
                           MIN(id) as id_manter, 
                           ARRAY_AGG(id ORDER BY created_at ASC) as todos_ids,
                           ARRAY_AGG(data_source ORDER BY created_at ASC) as fontes
                    FROM contratos
                    WHERE numero_controle_pncp IS NOT NULL
                    GROUP BY numero_controle_pncp
                    HAVING COUNT(*) > 1
                    ORDER BY total DESC
                """)
                
                duplicatas = cursor.fetchall()
                self.stats["duplicatas_encontradas"] += len(duplicatas)
                
                if duplicatas:
                    console.print(f"⚠️ Encontradas {len(duplicatas)} duplicatas em contratos")
                    return duplicatas
                else:
                    console.print("✅ Nenhuma duplicata encontrada em contratos")
                    return []
                    
        except Exception as e:
            console.print(f"❌ Erro ao detectar duplicatas: {e}")
            return []
    
    def resolver_duplicatas_contratacoes(self, duplicatas):
        """Resolve duplicatas em contratações mantendo o melhor registro"""
        console.print(Panel("🔧 Resolvendo duplicatas em contratações", style="green"))
        
        if not duplicatas:
            return
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            
            task = progress.add_task("Resolvendo duplicatas...", total=len(duplicatas))
            
            for duplicata in duplicatas:
                try:
                    numero_controle = duplicata["numero_controle_pncp"]
                    todos_ids = duplicata["todos_ids"]
                    id_manter = todos_ids[0]  # Primeiro cronologicamente
                    ids_remover = todos_ids[1:]
                    
                    with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                        # Buscar todos os registros duplicados
                        cursor.execute("""
                            SELECT * FROM contratacoes 
                            WHERE numero_controle_pncp = %s 
                            ORDER BY created_at ASC
                        """, (numero_controle,))
                        
                        registros = cursor.fetchall()
                        
                        if len(registros) > 1:
                            # Criar registro unificado com os melhores dados
                            registro_unificado = self._unificar_contratacao(registros)
                            
                            # Atualizar o registro que vamos manter
                            self._atualizar_contratacao_unificada(cursor, id_manter, registro_unificado)
                            
                            # Remover duplicatas
                            for id_remover in ids_remover:
                                cursor.execute("DELETE FROM contratacoes WHERE id = %s", (id_remover,))
                            
                            self.stats["duplicatas_resolvidas"] += 1
                            self.stats["registros_unificados"] += 1
                            
                            progress.update(task, description=f"Resolvida: {numero_controle}")
                    
                    progress.advance(task)
                    
                except Exception as e:
                    console.print(f"❌ Erro ao resolver duplicata {numero_controle}: {e}")
                    progress.advance(task)
            
            self.connection.commit()
        
        console.print(f"✅ Duplicatas resolvidas: {self.stats['duplicatas_resolvidas']}")
    
    def resolver_duplicatas_contratos(self, duplicatas):
        """Resolve duplicatas em contratos mantendo o melhor registro"""
        console.print(Panel("🔧 Resolvendo duplicatas em contratos", style="green"))
        
        if not duplicatas:
            return
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            console=console
        ) as progress:
            
            task = progress.add_task("Resolvendo duplicatas...", total=len(duplicatas))
            
            for duplicata in duplicatas:
                try:
                    numero_controle = duplicata["numero_controle_pncp"]
                    todos_ids = duplicata["todos_ids"]
                    id_manter = todos_ids[0]  # Primeiro cronologicamente
                    ids_remover = todos_ids[1:]
                    
                    with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                        # Buscar todos os registros duplicados
                        cursor.execute("""
                            SELECT * FROM contratos 
                            WHERE numero_controle_pncp = %s 
                            ORDER BY created_at ASC
                        """, (numero_controle,))
                        
                        registros = cursor.fetchall()
                        
                        if len(registros) > 1:
                            # Criar registro unificado com os melhores dados
                            registro_unificado = self._unificar_contrato(registros)
                            
                            # Atualizar o registro que vamos manter
                            self._atualizar_contrato_unificado(cursor, id_manter, registro_unificado)
                            
                            # Remover duplicatas
                            for id_remover in ids_remover:
                                cursor.execute("DELETE FROM contratos WHERE id = %s", (id_remover,))
                            
                            self.stats["duplicatas_resolvidas"] += 1
                            self.stats["registros_unificados"] += 1
                            
                            progress.update(task, description=f"Resolvida: {numero_controle}")
                    
                    progress.advance(task)
                    
                except Exception as e:
                    console.print(f"❌ Erro ao resolver duplicata {numero_controle}: {e}")
                    progress.advance(task)
            
            self.connection.commit()
        
        console.print(f"✅ Duplicatas resolvidas: {self.stats['duplicatas_resolvidas']}")
    
    def _unificar_contratacao(self, registros):
        """Unifica múltiplos registros de contratação em um só com os melhores dados"""
        registro_base = dict(registros[0])
        
        # Para cada campo, escolher o melhor valor disponível
        for registro in registros[1:]:
            for campo, valor in registro.items():
                if campo in ['id', 'created_at', 'updated_at']:
                    continue
                
                # Se o campo atual está vazio/nulo e o novo tem valor
                if not registro_base.get(campo) and valor:
                    registro_base[campo] = valor
                    self.stats["dados_complementados"] += 1
                
                # Para campos numéricos, manter o maior valor
                elif campo in ['valor_estimado_contrato', 'valor_homologado_global'] and valor:
                    valor_atual = registro_base.get(campo) or 0
                    if valor > valor_atual:
                        registro_base[campo] = valor
                
                # Para campos de texto, manter o mais completo
                elif campo in ['objeto_contrato', 'descricao'] and valor:
                    valor_atual = registro_base.get(campo) or ""
                    if len(str(valor)) > len(str(valor_atual)):
                        registro_base[campo] = valor
        
        return registro_base
    
    def _unificar_contrato(self, registros):
        """Unifica múltiplos registros de contrato em um só com os melhores dados"""
        registro_base = dict(registros[0])
        
        # Para cada campo, escolher o melhor valor disponível
        for registro in registros[1:]:
            for campo, valor in registro.items():
                if campo in ['id', 'created_at', 'updated_at']:
                    continue
                
                # Se o campo atual está vazio/nulo e o novo tem valor
                if not registro_base.get(campo) and valor:
                    registro_base[campo] = valor
                    self.stats["dados_complementados"] += 1
                
                # Para campos numéricos, manter o maior valor
                elif campo in ['valor_inicial', 'valor_global'] and valor:
                    valor_atual = registro_base.get(campo) or 0
                    if valor > valor_atual:
                        registro_base[campo] = valor
                
                # Para campos de texto, manter o mais completo
                elif campo in ['objeto_contrato'] and valor:
                    valor_atual = registro_base.get(campo) or ""
                    if len(str(valor)) > len(str(valor_atual)):
                        registro_base[campo] = valor
        
        return registro_base
    
    def _atualizar_contratacao_unificada(self, cursor, id_manter, registro_unificado):
        """Atualiza contratação com dados unificados"""
        campos_update = []
        valores = []
        
        # Campos que podem ser atualizados
        campos_atualizaveis = [
            'objeto_contrato', 'descricao', 'valor_estimado_contrato',
            'valor_homologado_global', 'modalidade_codigo', 'modalidade_nome',
            'tipo_contrato', 'criterio_julgamento', 'situacao_contratacao',
            'data_abertura_proposta', 'data_encerramento_proposta',
            'data_homologacao', 'data_source'
        ]
        
        for campo in campos_atualizaveis:
            if campo in registro_unificado and registro_unificado[campo] is not None:
                campos_update.append(f"{campo} = %s")
                valores.append(registro_unificado[campo])
        
        if campos_update:
            campos_update.append("updated_at = NOW()")
            sql = f"UPDATE contratacoes SET {', '.join(campos_update)} WHERE id = %s"
            valores.append(id_manter)
            cursor.execute(sql, valores)
    
    def _atualizar_contrato_unificado(self, cursor, id_manter, registro_unificado):
        """Atualiza contrato com dados unificados"""
        campos_update = []
        valores = []
        
        # Campos que podem ser atualizados
        campos_atualizaveis = [
            'numero_contrato_empenho', 'data_assinatura', 'data_vigencia_inicio',
            'data_vigencia_fim', 'ni_fornecedor', 'tipo_pessoa',
            'nome_razao_social_fornecedor', 'valor_inicial', 'valor_global',
            'objeto_contrato', 'orgao_entidade_cnpj', 'data_source'
        ]
        
        for campo in campos_atualizaveis:
            if campo in registro_unificado and registro_unificado[campo] is not None:
                campos_update.append(f"{campo} = %s")
                valores.append(registro_unificado[campo])
        
        if campos_update:
            campos_update.append("updated_at = NOW()")
            sql = f"UPDATE contratos SET {', '.join(campos_update)} WHERE id = %s"
            valores.append(id_manter)
            cursor.execute(sql, valores)
    
    def detectar_conflitos_dados(self):
        """Detecta conflitos de dados entre registros similares"""
        console.print(Panel("🔍 Detectando conflitos de dados", style="yellow"))
        
        conflitos = []
        
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                # Buscar contratos com valores muito diferentes para o mesmo numero_controle_pncp_compra
                cursor.execute("""
                    SELECT numero_controle_pncp_compra, 
                           COUNT(*) as total_contratos,
                           MIN(valor_global) as valor_min,
                           MAX(valor_global) as valor_max,
                           AVG(valor_global) as valor_medio,
                           ARRAY_AGG(id) as ids,
                           ARRAY_AGG(valor_global) as valores
                    FROM contratos 
                    WHERE numero_controle_pncp_compra IS NOT NULL 
                      AND valor_global IS NOT NULL
                      AND valor_global > 0
                    GROUP BY numero_controle_pncp_compra
                    HAVING COUNT(*) > 1 
                       AND (MAX(valor_global) - MIN(valor_global)) / MIN(valor_global) > 0.1
                    ORDER BY (MAX(valor_global) - MIN(valor_global)) DESC
                """)
                
                conflitos_valores = cursor.fetchall()
                
                for conflito in conflitos_valores:
                    self.conflitos_detectados.append({
                        "tipo": "valor_conflitante",
                        "numero_controle": conflito["numero_controle_pncp_compra"],
                        "detalhes": f"Valores: {conflito['valor_min']:,.2f} - {conflito['valor_max']:,.2f}",
                        "ids_afetados": conflito["ids"]
                    })
                
                self.stats["conflitos_dados"] += len(conflitos_valores)
                
                if conflitos_valores:
                    console.print(f"⚠️ Encontrados {len(conflitos_valores)} conflitos de valores")
                else:
                    console.print("✅ Nenhum conflito de valores encontrado")
                
                return len(conflitos_valores)
                
        except Exception as e:
            console.print(f"❌ Erro ao detectar conflitos: {e}")
            return 0
    
    def validar_integridade_referencial(self):
        """Valida integridade referencial entre tabelas"""
        console.print(Panel("🔍 Validando integridade referencial", style="cyan"))
        
        problemas = []
        
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                # 1. Contratos sem contratação associada
                cursor.execute("""
                    SELECT COUNT(*) as total
                    FROM contratos c
                    LEFT JOIN contratacoes ct ON c.numero_controle_pncp_compra = ct.numero_controle_pncp
                    WHERE ct.numero_controle_pncp IS NULL
                      AND c.numero_controle_pncp_compra IS NOT NULL
                """)
                
                contratos_orfaos = cursor.fetchone()["total"]
                if contratos_orfaos > 0:
                    problemas.append(f"Contratos sem contratação: {contratos_orfaos}")
                
                # 2. Itens sem contratação associada
                cursor.execute("""
                    SELECT COUNT(*) as total
                    FROM itens_contratacao i
                    LEFT JOIN contratacoes c ON i.numero_controle_pncp = c.numero_controle_pncp
                    WHERE c.numero_controle_pncp IS NULL
                """)
                
                itens_orfaos = cursor.fetchone()["total"]
                if itens_orfaos > 0:
                    problemas.append(f"Itens sem contratação: {itens_orfaos}")
                
                # 3. Classificações sem item associado
                cursor.execute("""
                    SELECT COUNT(*) as total
                    FROM classificacoes_itens ci
                    LEFT JOIN itens_contratacao i ON ci.item_id = i.id
                    WHERE i.id IS NULL
                """)
                
                classificacoes_orfas = cursor.fetchone()["total"]
                if classificacoes_orfas > 0:
                    problemas.append(f"Classificações sem item: {classificacoes_orfas}")
                
                if problemas:
                    console.print("⚠️ Problemas de integridade encontrados:")
                    for problema in problemas:
                        console.print(f"  • {problema}")
                else:
                    console.print("✅ Integridade referencial OK")
                
                return len(problemas)
                
        except Exception as e:
            console.print(f"❌ Erro ao validar integridade: {e}")
            return 0
    
    def gerar_relatorio_reconciliacao(self):
        """Gera relatório detalhado da reconciliação"""
        console.print(Panel("📊 Relatório da Reconciliação", style="cyan"))
        
        # Estatísticas gerais
        table = Table(title="Estatísticas da Reconciliação")
        table.add_column("Métrica", style="cyan")
        table.add_column("Quantidade", style="green")
        table.add_column("Status", style="yellow")
        
        table.add_row("Duplicatas encontradas", str(self.stats["duplicatas_encontradas"]), "🔍 Detectadas")
        table.add_row("Duplicatas resolvidas", str(self.stats["duplicatas_resolvidas"]), "✅ Resolvidas")
        table.add_row("Conflitos encontrados", str(self.stats["conflitos_dados"]), "⚠️ Detectados")
        table.add_row("Registros unificados", str(self.stats["registros_unificados"]), "🔧 Processados")
        table.add_row("Dados complementados", str(self.stats["dados_complementados"]), "📝 Melhorados")
        
        console.print(table)
        
        # Detalhes dos conflitos
        if self.conflitos_detectados:
            console.print("\n⚠️ Conflitos detectados:")
            for conflito in self.conflitos_detectados[:10]:  # Mostra só os primeiros 10
                console.print(f"  • {conflito['tipo']}: {conflito['numero_controle']} - {conflito['detalhes']}")
        
        # Salvar relatório completo
        relatorio = {
            "data_reconciliacao": datetime.now().isoformat(),
            "estatisticas": self.stats,
            "conflitos_detectados": self.conflitos_detectados,
            "total_problemas_resolvidos": (
                self.stats["duplicatas_resolvidas"] + 
                self.stats["conflitos_resolvidos"]
            )
        }
        
        with open("relatorio_reconciliacao.json", "w", encoding="utf-8") as f:
            json.dump(relatorio, f, indent=2, ensure_ascii=False)
        
        console.print("💾 Relatório salvo em: relatorio_reconciliacao.json")
    
    def executar_reconciliacao_completa(self):
        """Executa o processo completo de reconciliação"""
        console.print(Panel.fit(
            "[bold blue]GovGo V1 - Reconciliação de Dados[/bold blue]\n"
            "Unificando dados da migração local com coleta API:\n"
            "• Detectar e resolver duplicatas\n"
            "• Unificar registros com melhores dados\n"
            "• Validar integridade referencial\n"
            "• Detectar conflitos de dados",
            title="🔧 Data Reconciliator"
        ))
        
        if not self.connect_database():
            return False
        
        try:
            # 1. Detectar e resolver duplicatas em contratações
            duplicatas_contratacoes = self.detectar_duplicatas_contratacoes()
            self.resolver_duplicatas_contratacoes(duplicatas_contratacoes)
            
            # 2. Detectar e resolver duplicatas em contratos
            duplicatas_contratos = self.detectar_duplicatas_contratos()
            self.resolver_duplicatas_contratos(duplicatas_contratos)
            
            # 3. Detectar conflitos de dados
            conflitos = self.detectar_conflitos_dados()
            
            # 4. Validar integridade referencial
            problemas_integridade = self.validar_integridade_referencial()
            
            # 5. Gerar relatório
            self.gerar_relatorio_reconciliacao()
            
            console.print("\n🎉 [bold green]Reconciliação concluída com sucesso![/bold green]")
            
            if conflitos > 0 or problemas_integridade > 0:
                console.print("⚠️ [yellow]Alguns conflitos/problemas foram detectados. Verifique o relatório.[/yellow]")
            
            return True
            
        except Exception as e:
            console.print(f"\n❌ [bold red]Erro durante a reconciliação: {e}[/bold red]")
            return False
        
        finally:
            if self.connection:
                self.connection.close()
                console.print("🔌 Conexão fechada")

def main():
    """Função principal"""
    reconciliator = DataReconciliator()
    
    if reconciliator.executar_reconciliacao_completa():
        console.print("\n✅ [bold green]Reconciliação de dados concluída![/bold green]")
        console.print("🚀 Próximo passo: execute 06_migration_report.py")
    else:
        console.print("\n❌ [bold red]Falha na reconciliação de dados[/bold red]")
        exit(1)

if __name__ == "__main__":
    main()
