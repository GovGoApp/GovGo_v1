#!/usr/bin/env python3
"""
GovGo V1 - 04 - Coleta de Dados via API
=======================================
Busca dados que NÃO estão na base local via API PNCP
Complementa a migração local com dados faltantes

EXECUÇÃO: Após 03_migrate_from_local.py
PRÓXIMO: 05_reconcile_data.py
"""

import os
import sys
import json
import requests
import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime, timedelta
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeRemainingColumn
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Adicionar o diretório pai ao path
sys.path.append(str(os.path.dirname(os.path.dirname(__file__))))

from core.config import config
from core.utils import configurar_logging

console = Console()
configurar_logging()

class APIDataCollector:
    """Coletor de dados via API PNCP para complementar a base local"""
    
    def __init__(self):
        self.connection = None
        self.base_url = "https://pncp.gov.br/api/consulta/v1"
        self.stats = {
            "contratos_coletados": 0,
            "atas_coletadas": 0,
            "pcas_coletados": 0,
            "erros_api": 0,
            "dados_existentes": 0
        }
        
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
    
    def identificar_dados_faltantes(self):
        """Identifica quais dados estão faltando na base"""
        console.print(Panel("🔍 Identificando dados faltantes", style="blue"))
        
        dados_faltantes = {
            "contratos_sem_dados": [],
            "contratacoes_sem_contratos": [],
            "periodos_atas": [],
            "anos_pcas": []
        }
        
        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                
                # 1. Contratações que não têm contratos associados
                cursor.execute("""
                    SELECT c.numero_controle_pncp, c.ano_compra, c.orgao_entidade_cnpj
                    FROM contratacoes c
                    LEFT JOIN contratos ct ON c.numero_controle_pncp = ct.numero_controle_pncp_compra
                    WHERE ct.numero_controle_pncp_compra IS NULL
                    AND c.existe_contrato_associado = 1
                    ORDER BY c.ano_compra DESC, c.numero_controle_pncp
                    LIMIT 1000
                """)
                
                dados_faltantes["contratacoes_sem_contratos"] = [
                    {
                        "numero_controle": row["numero_controle_pncp"],
                        "ano": row["ano_compra"],
                        "cnpj": row["orgao_entidade_cnpj"]
                    }
                    for row in cursor.fetchall()
                ]
                
                # 2. Períodos para buscar ATAs (últimos 12 meses)
                data_fim = datetime.now()
                for i in range(12):
                    data_periodo = data_fim - timedelta(days=30*i)
                    dados_faltantes["periodos_atas"].append({
                        "data_inicio": (data_periodo - timedelta(days=30)).strftime("%Y%m%d"),
                        "data_fim": data_periodo.strftime("%Y%m%d"),
                        "mes_ano": data_periodo.strftime("%m/%Y")
                    })
                
                # 3. Anos para buscar PCAs (últimos 3 anos)
                ano_atual = datetime.now().year
                dados_faltantes["anos_pcas"] = [ano_atual, ano_atual-1, ano_atual-2]
                
                console.print(f"📊 Contratações sem contratos: {len(dados_faltantes['contratacoes_sem_contratos'])}")
                console.print(f"📊 Períodos para ATAs: {len(dados_faltantes['periodos_atas'])}")
                console.print(f"📊 Anos para PCAs: {len(dados_faltantes['anos_pcas'])}")
                
                return dados_faltantes
                
        except Exception as e:
            console.print(f"❌ Erro ao identificar dados faltantes: {e}")
            return None
    
    def buscar_contratos_api(self, contratacoes_sem_contratos):
        """Busca contratos via API para contratações que não têm contratos"""
        console.print(Panel("🔍 Buscando contratos via API", style="green"))
        
        if not contratacoes_sem_contratos:
            console.print("ℹ️ Nenhuma contratação sem contrato encontrada")
            return
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task(
                "Buscando contratos...", 
                total=len(contratacoes_sem_contratos)
            )
            
            def buscar_contrato_individual(contratacao):
                """Busca contrato individual via API"""
                try:
                    numero_controle = contratacao["numero_controle"]
                    url = f"{self.base_url}/contratos"
                    
                    params = {
                        "numeroControlePNCP": numero_controle,
                        "pagina": 1,
                        "tamanhoPagina": 100
                    }
                    
                    response = requests.get(url, params=params, timeout=30)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if "data" in data and data["data"]:
                            return self._processar_contratos_api(data["data"], numero_controle)
                    
                    return 0
                    
                except Exception as e:
                    self.stats["erros_api"] += 1
                    return 0
            
            # Processar em lotes para não sobrecarregar a API
            lote_size = 10
            for i in range(0, len(contratacoes_sem_contratos), lote_size):
                lote = contratacoes_sem_contratos[i:i+lote_size]
                
                with ThreadPoolExecutor(max_workers=3) as executor:
                    futures = [executor.submit(buscar_contrato_individual, cont) for cont in lote]
                    
                    for future in as_completed(futures):
                        result = future.result()
                        self.stats["contratos_coletados"] += result
                        progress.advance(task)
                
                # Pausa entre lotes para não sobrecarregar a API
                time.sleep(2)
        
        console.print(f"✅ Contratos coletados via API: {self.stats['contratos_coletados']}")
    
    def buscar_atas_api(self, periodos_atas):
        """Busca ATAs via API por período"""
        console.print(Panel("🔍 Buscando ATAs via API", style="yellow"))
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task("Buscando ATAs...", total=len(periodos_atas))
            
            for periodo in periodos_atas:
                try:
                    url = f"{self.base_url}/atas"
                    params = {
                        "dataInicial": periodo["data_inicio"],
                        "dataFinal": periodo["data_fim"],
                        "pagina": 1,
                        "tamanhoPagina": 100
                    }
                    
                    response = requests.get(url, params=params, timeout=30)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if "data" in data and data["data"]:
                            resultado = self._processar_atas_api(data["data"])
                            self.stats["atas_coletadas"] += resultado
                            progress.update(task, description=f"ATAs {periodo['mes_ano']}: +{resultado}")
                    
                    progress.advance(task)
                    time.sleep(1)  # Pausa entre requests
                    
                except Exception as e:
                    self.stats["erros_api"] += 1
                    progress.advance(task)
        
        console.print(f"✅ ATAs coletadas via API: {self.stats['atas_coletadas']}")
    
    def buscar_pcas_api(self, anos_pcas):
        """Busca PCAs via API por ano"""
        console.print(Panel("🔍 Buscando PCAs via API", style="magenta"))
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeRemainingColumn(),
            console=console
        ) as progress:
            
            task = progress.add_task("Buscando PCAs...", total=len(anos_pcas))
            
            for ano in anos_pcas:
                try:
                    url = f"{self.base_url}/pca"
                    params = {
                        "ano": str(ano),
                        "pagina": 1,
                        "tamanhoPagina": 100
                    }
                    
                    response = requests.get(url, params=params, timeout=30)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if "data" in data and data["data"]:
                            resultado = self._processar_pcas_api(data["data"])
                            self.stats["pcas_coletados"] += resultado
                            progress.update(task, description=f"PCAs {ano}: +{resultado}")
                    
                    progress.advance(task)
                    time.sleep(1)  # Pausa entre requests
                    
                except Exception as e:
                    self.stats["erros_api"] += 1
                    progress.advance(task)
        
        console.print(f"✅ PCAs coletados via API: {self.stats['pcas_coletados']}")
    
    def _processar_contratos_api(self, contratos_data, numero_controle_compra):
        """Processa dados de contratos da API e insere no banco"""
        try:
            contratos_inseridos = 0
            
            with self.connection.cursor() as cursor:
                for contrato in contratos_data:
                    # Verificar se já existe
                    cursor.execute(
                        "SELECT id FROM contratos WHERE numero_controle_pncp = %s",
                        (contrato.get("numeroControlePNCP"),)
                    )
                    
                    if cursor.fetchone():
                        self.stats["dados_existentes"] += 1
                        continue
                    
                    # Inserir contrato
                    insert_sql = """
                        INSERT INTO contratos (
                            numero_controle_pncp_compra,
                            numero_controle_pncp,
                            numero_contrato_empenho,
                            ano_contrato,
                            data_assinatura,
                            data_vigencia_inicio,
                            data_vigencia_fim,
                            ni_fornecedor,
                            tipo_pessoa,
                            nome_razao_social_fornecedor,
                            valor_inicial,
                            valor_global,
                            objeto_contrato,
                            orgao_entidade_cnpj,
                            created_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                        )
                    """
                    
                    valores = (
                        numero_controle_compra,
                        contrato.get("numeroControlePNCP"),
                        contrato.get("numeroContratoEmpenho"),
                        contrato.get("anoContrato"),
                        contrato.get("dataAssinatura"),
                        contrato.get("dataVigenciaInicio"),
                        contrato.get("dataVigenciaFim"),
                        contrato.get("niFornecedor"),
                        contrato.get("tipoPessoa"),
                        contrato.get("nomeRazaoSocialFornecedor"),
                        contrato.get("valorInicial"),
                        contrato.get("valorGlobal"),
                        contrato.get("objetoContrato"),
                        contrato.get("orgaoEntidade", {}).get("cnpj")
                    )
                    
                    cursor.execute(insert_sql, valores)
                    contratos_inseridos += 1
                
                self.connection.commit()
                return contratos_inseridos
                
        except Exception as e:
            console.print(f"❌ Erro ao processar contratos: {e}")
            self.connection.rollback()
            return 0
    
    def _processar_atas_api(self, atas_data):
        """Processa dados de ATAs da API e insere no banco"""
        try:
            atas_inseridas = 0
            
            with self.connection.cursor() as cursor:
                for ata in atas_data:
                    # Verificar se já existe
                    cursor.execute(
                        "SELECT id FROM atas WHERE numero_ata_registro_preco = %s AND numero_controle_pncp_compra = %s",
                        (ata.get("numeroAtaRegistroPreco"), ata.get("numeroControlePNCPCompra"))
                    )
                    
                    if cursor.fetchone():
                        self.stats["dados_existentes"] += 1
                        continue
                    
                    # Inserir ATA
                    insert_sql = """
                        INSERT INTO atas (
                            numero_controle_pncp_compra,
                            numero_ata_registro_preco,
                            ano_ata,
                            data_assinatura,
                            data_vigencia_inicio,
                            data_vigencia_fim,
                            orgao_gerenciador_cnpj,
                            objeto_ata,
                            valor_estimado_total,
                            fornecedores,
                            created_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW()
                        )
                    """
                    
                    valores = (
                        ata.get("numeroControlePNCPCompra"),
                        ata.get("numeroAtaRegistroPreco"),
                        ata.get("anoAta"),
                        ata.get("dataAssinatura"),
                        ata.get("dataVigenciaInicio"),
                        ata.get("dataVigenciaFim"),
                        ata.get("orgaoGerenciador", {}).get("cnpj"),
                        ata.get("objetoAta"),
                        ata.get("valorEstimadoTotal"),
                        json.dumps(ata.get("fornecedores", []))
                    )
                    
                    cursor.execute(insert_sql, valores)
                    atas_inseridas += 1
                
                self.connection.commit()
                return atas_inseridas
                
        except Exception as e:
            console.print(f"❌ Erro ao processar ATAs: {e}")
            self.connection.rollback()
            return 0
    
    def _processar_pcas_api(self, pcas_data):
        """Processa dados de PCAs da API e insere no banco"""
        try:
            pcas_inseridos = 0
            
            with self.connection.cursor() as cursor:
                for pca in pcas_data:
                    # Verificar se já existe
                    cursor.execute(
                        "SELECT id FROM pcas WHERE orgao_cnpj = %s AND codigo_unidade = %s AND ano_pca = %s",
                        (pca.get("orgaoCnpj"), pca.get("codigoUnidade"), pca.get("anoPca"))
                    )
                    
                    if cursor.fetchone():
                        self.stats["dados_existentes"] += 1
                        continue
                    
                    # Inserir PCA
                    insert_sql = """
                        INSERT INTO pcas (
                            orgao_cnpj,
                            codigo_unidade,
                            ano_pca,
                            unidade_nome,
                            valor_total_estimado,
                            quantidade_itens,
                            itens_plano,
                            created_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, %s, NOW()
                        )
                    """
                    
                    valores = (
                        pca.get("orgaoCnpj"),
                        pca.get("codigoUnidade"),
                        pca.get("anoPca"),
                        pca.get("unidadeNome"),
                        pca.get("valorTotalEstimado"),
                        len(pca.get("itensPlano", [])),
                        json.dumps(pca.get("itensPlano", []))
                    )
                    
                    cursor.execute(insert_sql, valores)
                    pcas_inseridos += 1
                
                self.connection.commit()
                return pcas_inseridos
                
        except Exception as e:
            console.print(f"❌ Erro ao processar PCAs: {e}")
            self.connection.rollback()
            return 0
    
    def gerar_relatorio_coleta(self):
        """Gera relatório da coleta via API"""
        console.print(Panel("📊 Relatório da Coleta via API", style="cyan"))
        
        table = Table(title="Estatísticas da Coleta")
        table.add_column("Tipo", style="cyan")
        table.add_column("Coletados", style="green")
        table.add_column("Status", style="yellow")
        
        table.add_row("Contratos", str(self.stats["contratos_coletados"]), "✅ Sucesso")
        table.add_row("ATAs", str(self.stats["atas_coletadas"]), "✅ Sucesso")
        table.add_row("PCAs", str(self.stats["pcas_coletados"]), "✅ Sucesso")
        table.add_row("Já existentes", str(self.stats["dados_existentes"]), "ℹ️ Ignorados")
        table.add_row("Erros API", str(self.stats["erros_api"]), "⚠️ Falhas")
        
        console.print(table)
        
        # Salvar estatísticas em arquivo
        relatorio = {
            "data_coleta": datetime.now().isoformat(),
            "estatisticas": self.stats,
            "total_coletado": (
                self.stats["contratos_coletados"] + 
                self.stats["atas_coletadas"] + 
                self.stats["pcas_coletados"]
            )
        }
        
        with open("relatorio_coleta_api.json", "w", encoding="utf-8") as f:
            json.dump(relatorio, f, indent=2, ensure_ascii=False)
        
        console.print("💾 Relatório salvo em: relatorio_coleta_api.json")
    
    def executar_coleta_completa(self):
        """Executa a coleta completa de dados via API"""
        console.print(Panel.fit(
            "[bold blue]GovGo V1 - Coleta de Dados via API[/bold blue]\n"
            "Buscando dados que NÃO estão na base local:\n"
            "• Contratos faltantes\n"
            "• ATAs de Registro de Preço\n"
            "• Planos de Contratações (PCAs)",
            title="🌐 API Data Collector"
        ))
        
        if not self.connect_database():
            return False
        
        try:
            # 1. Identificar dados faltantes
            dados_faltantes = self.identificar_dados_faltantes()
            if not dados_faltantes:
                return False
            
            # 2. Buscar contratos faltantes
            self.buscar_contratos_api(dados_faltantes["contratacoes_sem_contratos"])
            
            # 3. Buscar ATAs
            self.buscar_atas_api(dados_faltantes["periodos_atas"])
            
            # 4. Buscar PCAs
            self.buscar_pcas_api(dados_faltantes["anos_pcas"])
            
            # 5. Gerar relatório
            self.gerar_relatorio_coleta()
            
            console.print("\n🎉 [bold green]Coleta via API concluída com sucesso![/bold green]")
            return True
            
        except Exception as e:
            console.print(f"\n❌ [bold red]Erro durante a coleta: {e}[/bold red]")
            return False
        
        finally:
            if self.connection:
                self.connection.close()
                console.print("🔌 Conexão fechada")

def main():
    """Função principal"""
    collector = APIDataCollector()
    
    if collector.executar_coleta_completa():
        console.print("\n✅ [bold green]Coleta de dados via API concluída![/bold green]")
        console.print("🚀 Próximo passo: execute 05_reconcile_data.py")
    else:
        console.print("\n❌ [bold red]Falha na coleta de dados via API[/bold red]")
        exit(1)

if __name__ == "__main__":
    main()
