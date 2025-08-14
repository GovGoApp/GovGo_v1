#!/usr/bin/env python3
"""
Teste abrangente para verificar alinhamento entre API PNCP e tabelas do banco
"""

import os
import sys
import json
import requests
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

console = Console()

# Adicionar o diretório db ao path
script_dir = os.path.dirname(os.path.abspath(__file__))
v1_root = os.path.dirname(script_dir)
db_dir = os.path.join(v1_root, "db")
sys.path.insert(0, db_dir)

# Carregar configurações
load_dotenv(os.path.join(v1_root, ".env"))

# Importar mapeamento
from de_para_pncp_v1 import DE_PARA_PNCP, apply_field_transformation

# Configurações do banco
DB_CONFIG = {
    'host': os.getenv('SUPABASE_HOST', 'localhost'),
    'port': os.getenv('SUPABASE_PORT', '6543'),
    'database': os.getenv('SUPABASE_DBNAME', 'postgres'),
    'user': os.getenv('SUPABASE_USER', 'postgres'),
    'password': os.getenv('SUPABASE_PASSWORD', '')
}

def get_table_columns(conn, table_name):
    """Obter colunas de uma tabela do PostgreSQL"""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = %s 
            AND table_schema = 'public'
            ORDER BY ordinal_position
        """, (table_name,))
        
        columns = {}
        for row in cursor.fetchall():
            columns[row[0]] = {
                'type': row[1],
                'nullable': row[2] == 'YES',
                'default': row[3]
            }
        return columns
        
    except Exception as e:
        console.print(f"[red]❌ Erro ao obter colunas de {table_name}: {str(e)}[/red]")
        return {}

def fetch_real_api_data():
    """Buscar dados reais da API PNCP para análise"""
    console.print("[blue]🌐 Buscando dados reais da API PNCP...[/blue]")
    
    try:
        # Tentar diferentes datas e códigos
        test_dates = ["20250801", "20250731", "20250730", "20250729"]
        test_codes = [8, 5, 1, 12]
        
        base_url = "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"
        
        for date_str in test_dates:
            for code in test_codes:
                console.print(f"[cyan]🔍 Testando data {date_str}, código {code}...[/cyan]")
                
                params = {
                    "dataInicial": date_str,
                    "dataFinal": date_str,
                    "codigoModalidadeContratacao": code,
                    "pagina": 1,
                    "tamanhoPagina": 5  # Apenas alguns registros para análise
                }
                
                response = requests.get(base_url, params=params, timeout=30)
                
                if response.status_code == 200:
                    contracts = response.json().get("data", [])
                    if contracts:
                        console.print(f"[green]✅ {len(contracts)} contratos obtidos da API (data: {date_str}, código: {code})[/green]")
                        
                        # Buscar itens do primeiro contrato
                        first_contract = contracts[0]
                        numero_controle = first_contract.get('numeroControlePNCP')
                        
                        if numero_controle:
                            # Extrair informações do número de controle para buscar itens
                            parts = numero_controle.split("-")
                            if len(parts) == 3:
                                cnpj = parts[0]
                                seq_and_year = parts[2].split("/")
                                if len(seq_and_year) == 2:
                                    seq = seq_and_year[0]
                                    ano_compra = seq_and_year[1]
                                    sequencial_compra = str(int(seq))
                                    
                                    items_url = f"https://pncp.gov.br/api/pncp//v1/orgaos/{cnpj}/compras/{ano_compra}/{sequencial_compra}/itens"
                                    items_response = requests.get(items_url, timeout=30)
                                    
                                    if items_response.status_code == 200:
                                        items = items_response.json()
                                        console.print(f"[green]✅ {len(items)} itens obtidos da API[/green]")
                                        return contracts, items
                                    else:
                                        console.print(f"[yellow]⚠️ Erro ao buscar itens: HTTP {items_response.status_code}[/yellow]")
                        
                        return contracts, []
                
                elif response.status_code == 400:
                    console.print(f"[yellow]⚠️ HTTP 400 para data {date_str}, código {code}[/yellow]")
                else:
                    console.print(f"[red]❌ Erro HTTP {response.status_code} para data {date_str}, código {code}[/red]")
        
        console.print("[red]❌ Nenhuma combinação de data/código retornou dados[/red]")
        return None, None
        
    except Exception as e:
        console.print(f"[red]❌ Erro ao buscar dados da API: {str(e)}[/red]")
        return None, None

def get_simulated_api_data():
    """Criar dados simulados baseados na estrutura conhecida da API PNCP"""
    console.print("[blue]🧪 Criando dados simulados para análise estrutural...[/blue]")
    
    # Dados simulados de contrato baseados na estrutura da API PNCP
    simulated_contract = {
        "numeroControlePNCP": "12345678000100-1-000001/2025",
        "objetoCompra": "Aquisição de equipamentos de informática",
        "valorTotalEstimado": 150000.50,
        "valorTotalHomologado": 145000.00,
        "dataPublicacaoPncp": "2025-08-01",
        "dataInicialProposta": "2025-08-05",
        "dataFinalProposta": "2025-08-10",
        "modalidade": {
            "codigo": 8,
            "nome": "Pregão Eletrônico"
        },
        "situacaoCompra": {
            "codigo": 1,
            "nome": "Homologada"
        },
        "modoDisputa": {
            "codigo": 1,
            "nome": "Aberto"
        },
        "tipoInstrumentoConvocatorio": {
            "codigo": 1,
            "nome": "Edital"
        },
        "orgaoEntidade": {
            "cnpj": "12345678000100",
            "razaoSocial": "Prefeitura Municipal de Exemplo",
            "poderId": 3,
            "esferaId": 3
        },
        "unidadeOrgao": {
            "ufNome": "São Paulo",
            "ufSigla": "SP",
            "municipioNome": "São Paulo",
            "codigoUnidade": "123456",
            "nomeUnidade": "Secretaria de Administração",
            "codigoIbge": "3550308"
        },
        "informacaoComplementar": "Processo licitatório para modernização do parque tecnológico",
        "linkSistemaOrigem": "http://exemplo.gov.br/licitacao/123",
        "usuarioNome": "João da Silva",
        "nupProcesso": "123456789.2025.1.01.0001",
        "orcamentoSigiloso": {
            "codigo": 0,
            "descricao": "Não"
        },
        "amparoLegal": {
            "codigo": 1,
            "nome": "Lei 14.133/2021",
            "descricao": "Lei de Licitações e Contratos"
        }
    }
    
    # Dados simulados de item
    simulated_item = {
        "numeroItem": 1,
        "descricao": "Computador Desktop",
        "quantidade": 10,
        "unidadeMedida": "UNIDADE",
        "valorUnitarioEstimado": 2500.00,
        "valorTotalEstimado": 25000.00,
        "valorUnitarioHomologado": 2400.00,
        "valorTotalHomologado": 24000.00,
        "tipoItem": {
            "codigo": 1,
            "nome": "Material"
        },
        "situacaoCompraItem": {
            "codigo": 1,
            "nome": "Homologado"
        },
        "criterioJulgamento": {
            "codigo": 1,
            "nome": "Menor Preço"
        },
        "beneficioId": 1,
        "incentivoId": 1
    }
    
    console.print("[green]✅ Dados simulados criados com base na estrutura da API PNCP[/green]")
    return [simulated_contract], [simulated_item]

def analyze_api_fields(contracts, items):
    """Analisar campos presentes nos dados da API"""
    console.print("[blue]🔍 Analisando campos da API...[/blue]")
    
    # Analisar campos de contratações
    contract_fields = set()
    if contracts:
        for contract in contracts:
            contract_fields.update(get_nested_keys(contract))
    
    # Analisar campos de itens
    item_fields = set()
    if items:
        for item in items:
            item_fields.update(get_nested_keys(item))
    
    return contract_fields, item_fields

def get_nested_keys(obj, prefix=''):
    """Obter todas as chaves aninhadas de um objeto JSON"""
    keys = set()
    
    if isinstance(obj, dict):
        for key, value in obj.items():
            full_key = f"{prefix}.{key}" if prefix else key
            keys.add(full_key)
            
            if isinstance(value, (dict, list)):
                keys.update(get_nested_keys(value, full_key))
    elif isinstance(obj, list) and obj:
        # Analisar o primeiro item da lista
        keys.update(get_nested_keys(obj[0], prefix))
    
    return keys

def compare_mappings(db_columns, api_fields, table_name):
    """Comparar mapeamentos entre API e tabelas"""
    console.print(f"[blue]📊 Analisando mapeamento para tabela '{table_name}'...[/blue]")
    
    # Obter mapeamento do arquivo de_para usando a estrutura correta
    from de_para_pncp_v1 import get_table_fields
    
    try:
        mapped_fields_list = get_table_fields(table_name)
        mapped_fields = set(mapped_fields_list)
    except:
        console.print(f"[red]❌ Erro ao obter campos mapeados para {table_name}[/red]")
        mapped_fields = set()
    
    # Criar tabela de comparação
    table = Table(title=f"Análise de Mapeamento - {table_name}")
    table.add_column("Campo DB", style="cyan")
    table.add_column("Mapeado", style="green")
    table.add_column("Tipo DB", style="yellow")
    table.add_column("Status", style="bold")
    
    # Verificar quais campos do DB estão mapeados
    for db_field in sorted(db_columns.keys()):
        db_type = db_columns[db_field]['type']
        
        if db_field in mapped_fields:
            status = "✅ MAPEADO"
            mapped_status = "SIM"
        else:
            status = "❌ NÃO MAPEADO"
            mapped_status = "NÃO"
        
        table.add_row(db_field, mapped_status, db_type, status)
    
    console.print(table)
    
    # Resumo
    total_db_fields = len(db_columns)
    mapped_count = len(mapped_fields.intersection(set(db_columns.keys())))
    coverage = (mapped_count / total_db_fields) * 100 if total_db_fields > 0 else 0
    
    console.print(f"\n[bold]📈 Cobertura de mapeamento para {table_name}:[/bold]")
    console.print(f"   • Campos no DB: {total_db_fields}")
    console.print(f"   • Campos mapeados: {mapped_count}")
    console.print(f"   • Cobertura: {coverage:.1f}%")
    
    unmapped_db_fields = set(db_columns.keys()) - mapped_fields
    
    return mapped_count, total_db_fields, unmapped_db_fields

def test_field_transformations(contracts, items):
    """Testar transformações de campos com dados reais"""
    console.print("[blue]🧪 Testando transformações com dados reais...[/blue]")
    
    if contracts:
        # Testar normalização de contrato
        test_contract = contracts[0]
        console.print(f"[cyan]📋 Testando contrato: {test_contract.get('numeroControlePNCP', 'N/A')}[/cyan]")
        
        try:
            normalized_contract = apply_field_transformation(test_contract, 'contratacao')
            console.print(f"[green]✅ Contrato normalizado com {len(normalized_contract)} campos[/green]")
            
            # Verificar campos essenciais
            essential_fields = ['numero_controle_pncp', 'objeto_compra', 'modalidade_nome']
            for field in essential_fields:
                value = normalized_contract.get(field)
                if value is not None:
                    console.print(f"   • {field}: {str(value)[:100]}...")
                else:
                    console.print(f"   • {field}: ❌ NULL")
                    
        except Exception as e:
            console.print(f"[red]❌ Erro na normalização de contrato: {str(e)}[/red]")
    
    if items:
        # Testar normalização de item
        test_item = items[0]
        numero_controle = contracts[0].get('numeroControlePNCP') if contracts else 'TEST-1-001/2025'
        
        try:
            normalized_item = apply_field_transformation(test_item, 'item_contratacao', numero_controle)
            console.print(f"[green]✅ Item normalizado com {len(normalized_item)} campos[/green]")
            
            # Verificar campos essenciais
            essential_fields = ['numero_controle_pncp', 'numero_item', 'descricao', 'valor_unitario_homologado']
            for field in essential_fields:
                value = normalized_item.get(field)
                if value is not None:
                    console.print(f"   • {field}: {str(value)[:100]}...")
                else:
                    console.print(f"   • {field}: ❌ NULL")
                    
        except Exception as e:
            console.print(f"[red]❌ Erro na normalização de item: {str(e)}[/red]")

def main():
    console.print(Panel("[bold blue]🔍 VERIFICAÇÃO DE ALINHAMENTO API ↔ BANCO[/bold blue]"))
    
    try:
        # Conectar ao banco
        conn = psycopg2.connect(**DB_CONFIG)
        console.print("[green]✅ Conectado ao banco PostgreSQL V1[/green]")
        
        # 1. Obter estrutura das tabelas
        console.print("\n[bold]1️⃣ ESTRUTURA DAS TABELAS[/bold]")
        contratacao_columns = get_table_columns(conn, 'contratacao')
        item_columns = get_table_columns(conn, 'item_contratacao')
        
        console.print(f"   • Tabela 'contratacao': {len(contratacao_columns)} campos")
        console.print(f"   • Tabela 'item_contratacao': {len(item_columns)} campos")
        
        # 2. Buscar dados reais da API
        console.print("\n[bold]2️⃣ DADOS DA API PNCP[/bold]")
        contracts, items = fetch_real_api_data()
        
        # Se não conseguir dados da API, usar dados simulados para teste de estrutura
        if contracts is None:
            console.print("[yellow]⚠️ Usando dados simulados para análise estrutural[/yellow]")
            contracts, items = get_simulated_api_data()
        
        if contracts is None:
            console.print("[red]❌ Não foi possível obter ou simular dados. Teste interrompido.[/red]")
            return
        
        # 3. Analisar campos da API
        console.print("\n[bold]3️⃣ ANÁLISE DE CAMPOS DA API[/bold]")
        contract_api_fields, item_api_fields = analyze_api_fields(contracts, items)
        
        console.print(f"   • Campos únicos em contratos: {len(contract_api_fields)}")
        console.print(f"   • Campos únicos em itens: {len(item_api_fields)}")
        
        # 4. Comparar mapeamentos
        console.print("\n[bold]4️⃣ COMPARAÇÃO DE MAPEAMENTOS[/bold]")
        
        # Análise de contratação
        mapped_contract, total_contract, unmapped_contract = compare_mappings(
            contratacao_columns, contract_api_fields, 'contratacao'
        )
        
        # Análise de item_contratacao
        mapped_item, total_item, unmapped_item = compare_mappings(
            item_columns, item_api_fields, 'item_contratacao'
        )
        
        # 5. Testar transformações
        console.print("\n[bold]5️⃣ TESTE DE TRANSFORMAÇÕES[/bold]")
        test_field_transformations(contracts, items)
        
        # 6. Relatório final
        console.print("\n[bold]6️⃣ RELATÓRIO FINAL[/bold]")
        
        total_coverage = ((mapped_contract + mapped_item) / (total_contract + total_item)) * 100
        
        console.print(f"[bold green]✅ COBERTURA GERAL: {total_coverage:.1f}%[/bold green]")
        
        if unmapped_contract:
            console.print(f"\n[yellow]⚠️ Campos não mapeados em 'contratacao':[/yellow]")
            for field in sorted(unmapped_contract):
                console.print(f"   • {field}")
        
        if unmapped_item:
            console.print(f"\n[yellow]⚠️ Campos não mapeados em 'item_contratacao':[/yellow]")
            for field in sorted(unmapped_item):
                console.print(f"   • {field}")
        
        if total_coverage >= 90:
            console.print(Panel("[bold green]🎯 ALINHAMENTO EXCELENTE (≥90%)[/bold green]"))
        elif total_coverage >= 80:
            console.print(Panel("[bold yellow]⚠️ ALINHAMENTO BOM (≥80%)[/bold yellow]"))
        else:
            console.print(Panel("[bold red]❌ ALINHAMENTO PRECISA MELHORAR (<80%)[/bold red]"))
        
        conn.close()
        
    except Exception as e:
        console.print(f"[red]❌ Erro crítico: {str(e)}[/red]")

if __name__ == "__main__":
    main()
