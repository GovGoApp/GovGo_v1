#!/usr/bin/env python3
"""
Verificação final do alinhamento entre API PNCP e schema real do Supabase V1
"""

import os
import sys
import json
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
from de_para_pncp_v1 import DE_PARA_PNCP, apply_field_transformation, get_table_fields

# Configurações do banco
DB_CONFIG = {
    'host': os.getenv('SUPABASE_HOST', 'localhost'),
    'port': os.getenv('SUPABASE_PORT', '6543'),
    'database': os.getenv('SUPABASE_DBNAME', 'postgres'),
    'user': os.getenv('SUPABASE_USER', 'postgres'),
    'password': os.getenv('SUPABASE_PASSWORD', '')
}

def get_real_schema():
    """Schema real do Supabase V1 baseado no arquivo fornecido"""
    return {
        'contratacao': {
            'id_contratacao': 'bigint PRIMARY KEY',
            'numero_controle_pncp': 'text UNIQUE',
            'modo_disputa_id': 'text',
            'amparo_legal_codigo': 'text',
            'data_abertura_proposta': 'text',
            'data_encerramento_proposta': 'text',
            'srp': 'text',
            'orgao_entidade_cnpj': 'text',
            'orgao_entidade_razao_social': 'text',
            'orgao_entidade_poder_id': 'text',
            'orgao_entidade_esfera_id': 'text',
            'ano_compra': 'text',
            'sequencial_compra': 'text',
            'processo': 'text',
            'objeto_compra': 'text',
            'valor_total_homologado': 'numeric',
            'data_inclusao': 'text',
            'data_publicacao_pncp': 'text',
            'data_atualizacao': 'text',
            'numero_compra': 'text',
            'unidade_orgao_uf_nome': 'text',
            'unidade_orgao_uf_sigla': 'text',
            'unidade_orgao_municipio_nome': 'text',
            'unidade_orgao_codigo_unidade': 'text',
            'unidade_orgao_nome_unidade': 'text',
            'unidade_orgao_codigo_ibge': 'text',
            'modalidade_id': 'text',
            'data_atualizacao_global': 'text',
            'tipo_instrumento_convocatorio_codigo': 'text',
            'valor_total_estimado': 'text',
            'situacao_compra_id': 'text',
            'cod_cat': 'text',
            'score': 'numeric',
            'informacao_complementar': 'text',
            'justificativa_presencial': 'text',
            'link_sistema_origem': 'text',
            'link_processo_eletronico': 'text',
            'amparo_legal_nome': 'text',
            'amparo_legal_descricao': 'text',
            'modalidade_nome': 'text',
            'modo_disputa_nome': 'text',
            'tipo_instrumento_convocatorio_nome': 'text',
            'situacao_compra_nome': 'text',
            'existe_resultado': 'boolean',
            'orcamento_sigiloso_codigo': 'integer',
            'orcamento_sigiloso_descricao': 'text',
            'orgao_subrogado_cnpj': 'text',
            'orgao_subrogado_razao_social': 'text',
            'orgao_subrogado_poder_id': 'text',
            'orgao_subrogado_esfera_id': 'text',
            'unidade_subrogada_uf_nome': 'text',
            'unidade_subrogada_uf_sigla': 'text',
            'unidade_subrogada_municipio_nome': 'text',
            'unidade_subrogada_codigo_unidade': 'text',
            'unidade_subrogada_nome_unidade': 'text',
            'unidade_subrogada_codigo_ibge': 'text',
            'usuario_nome': 'text',
            'fontes_orcamentarias': 'text',
            'created_at': 'timestamp with time zone',
            'updated_at': 'timestamp with time zone',
        },
        'item_contratacao': {
            'id_item': 'bigint PRIMARY KEY',
            'numero_controle_pncp': 'text',
            'numero_item': 'text',
            'descricao_item': 'text',
            'material_ou_servico': 'text',
            'valor_unitario_estimado': 'numeric',
            'valor_total_estimado': 'numeric',
            'quantidade_item': 'numeric',
            'unidade_medida': 'text',
            'item_categoria_id': 'text',
            'item_categoria_nome': 'text',
            'criterio_julgamento_id': 'text',
            'situacao_item': 'text',
            'tipo_beneficio': 'text',
            'data_inclusao': 'text',
            'data_atualizacao': 'text',
            'ncm_nbs_codigo': 'text',
            'catalogo': 'text',
            'created_at': 'timestamp with time zone',
        }
    }

def get_simulated_api_data():
    """Dados simulados da API PNCP com estrutura completa"""
    simulated_contract = {
        "numeroControlePNCP": "12345678000100-1-000001/2025",
        "objetoCompra": "Aquisição de equipamentos de informática",
        "valorTotalEstimado": 150000.50,
        "valorTotalHomologado": 145000.00,
        "dataPublicacaoPncp": "2025-08-01",
        "dataAberturaProposta": "2025-08-05",
        "dataEncerramentoProposta": "2025-08-10",
        "dataInclusao": "2025-07-30",
        "dataAtualizacao": "2025-08-01",
        "dataAtualizacaoGlobal": "2025-08-01",
        "numeroCompra": "2025000001",
        "anoCompra": "2025",
        "sequencialCompra": "1",
        "processo": "2025000001-ADM",
        "srp": "N",
        "modalidade": {
            "codigo": 8,
            "nome": "Pregão Eletrônico"
        },
        "modalidadeId": "8",
        "modalidadeNome": "Pregão Eletrônico",
        "situacaoCompra": {
            "codigo": 1,
            "nome": "Homologada"
        },
        "situacaoCompraId": "1",
        "situacaoCompraNome": "Homologada",
        "modoDisputa": {
            "codigo": 1,
            "nome": "Aberto"
        },
        "modoDisputaId": "1",
        "modoDisputaNome": "Aberto",
        "tipoInstrumentoConvocatorio": {
            "codigo": 1,
            "nome": "Edital"
        },
        "tipoInstrumentoConvocatorioCodigo": "1",
        "tipoInstrumentoConvocatorioNome": "Edital",
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
        "orgaoSubRogado": {
            "cnpj": "11111111000100",
            "razaoSocial": "Órgão Sub-rogado Exemplo",
            "poderId": 3,
            "esferaId": 3
        },
        "unidadeSubRogada": {
            "ufNome": "São Paulo",
            "ufSigla": "SP",
            "municipioNome": "Guarulhos",
            "codigoUnidade": "654321",
            "nomeUnidade": "Departamento Sub-rogado",
            "codigoIbge": "3518800"
        },
        "informacaoComplementar": "Processo licitatório para modernização do parque tecnológico",
        "justificativaPresencial": "Não se aplica",
        "linkSistemaOrigem": "http://exemplo.gov.br/licitacao/123",
        "linkProcessoEletronico": "http://exemplo.gov.br/processo/123",
        "usuarioNome": "João da Silva",
        "existeResultado": True,
        "orcamentoSigiloso": {
            "codigo": 0,
            "descricao": "Não"
        },
        "orcamentoSigilosoCodigo": 0,
        "orcamentoSigilosoDescricao": "Não",
        "amparoLegal": {
            "codigo": "1",
            "nome": "Lei 14.133/2021",
            "descricao": "Lei de Licitações e Contratos"
        },
        "fontesOrcamentarias": [
            {"codigo": "1001", "nome": "Recursos Ordinários"},
            {"codigo": "1002", "nome": "Transferências"}
        ]
    }
    
    simulated_item = {
        "numeroItem": 1,
        "descricao": "Computador Desktop",
        "materialOuServico": "M",
        "quantidade": 10,
        "unidadeMedida": "UNIDADE",
        "valorUnitarioEstimado": 2500.00,
        "valorTotal": 25000.00,
        "itemCategoriaId": "CAT001",
        "itemCategoriaNome": "Equipamentos de Informática",
        "criterioJulgamentoId": "1",
        "situacaoCompraItem": "Homologado",
        "tipoBeneficio": "Sustentável",
        "dataInclusao": "2025-07-30",
        "dataAtualizacao": "2025-08-01",
        "ncmNbsCodigo": "84713012",
        "catalogo": "BR0001"
    }
    
    return [simulated_contract], [simulated_item]

def verify_mapping_completeness():
    """Verificar completude do mapeamento"""
    console.print("[blue]🔍 Verificando completude do mapeamento...[/blue]")
    
    real_schema = get_real_schema()
    contracts, items = get_simulated_api_data()
    
    # Teste de transformação
    try:
        transformed_contract = apply_field_transformation(contracts[0], 'contratacao')
        transformed_item = apply_field_transformation(items[0], 'item_contratacao', contracts[0]['numeroControlePNCP'])
        
        console.print(f"[green]✅ Transformação bem-sucedida[/green]")
        console.print(f"   • Contrato: {len(transformed_contract)} campos")
        console.print(f"   • Item: {len(transformed_item)} campos")
        
    except Exception as e:
        console.print(f"[red]❌ Erro na transformação: {str(e)}[/red]")
        return False
    
    # Verificar cobertura para contratacao
    contract_schema = real_schema['contratacao']
    contract_fields = set(contract_schema.keys())
    mapped_contract_fields = set(transformed_contract.keys())
    
    # Excluir campos técnicos da verificação
    technical_fields = {'id_contratacao', 'created_at', 'updated_at', 'cod_cat', 'score'}
    relevant_contract_fields = contract_fields - technical_fields
    
    contract_coverage = len(mapped_contract_fields.intersection(relevant_contract_fields)) / len(relevant_contract_fields) * 100
    
    # Verificar cobertura para item_contratacao
    item_schema = real_schema['item_contratacao']
    item_fields = set(item_schema.keys())
    mapped_item_fields = set(transformed_item.keys())
    
    # Excluir campos técnicos da verificação
    technical_fields_item = {'id_item', 'created_at'}
    relevant_item_fields = item_fields - technical_fields_item
    
    item_coverage = len(mapped_item_fields.intersection(relevant_item_fields)) / len(relevant_item_fields) * 100
    
    return contract_coverage, item_coverage, transformed_contract, transformed_item

def create_detailed_mapping_report():
    """Criar relatório detalhado do mapeamento"""
    console.print(Panel("[bold blue]📋 RELATÓRIO DETALHADO DE MAPEAMENTO[/bold blue]"))
    
    real_schema = get_real_schema()
    
    # Tabela para contratacao
    console.print("\n[bold]🏢 TABELA: CONTRATACAO[/bold]")
    table_contract = Table(title="Mapeamento Contratação")
    table_contract.add_column("Campo DB", style="cyan")
    table_contract.add_column("Tipo", style="yellow")
    table_contract.add_column("Status", style="bold")
    
    mapped_fields = get_table_fields('contratacao')
    
    for field_name, field_type in real_schema['contratacao'].items():
        if field_name in {'id_contratacao', 'created_at', 'updated_at', 'cod_cat', 'score'}:
            status = "🔧 TÉCNICO"
            style = "dim"
        elif field_name in mapped_fields:
            status = "✅ MAPEADO"
            style = "green"
        else:
            status = "❌ FALTANDO"
            style = "red"
        
        table_contract.add_row(field_name, field_type.split()[0], status)
    
    console.print(table_contract)
    
    # Tabela para item_contratacao
    console.print("\n[bold]📦 TABELA: ITEM_CONTRATACAO[/bold]")
    table_item = Table(title="Mapeamento Item Contratação")
    table_item.add_column("Campo DB", style="cyan")
    table_item.add_column("Tipo", style="yellow")
    table_item.add_column("Status", style="bold")
    
    mapped_item_fields = get_table_fields('item_contratacao')
    
    for field_name, field_type in real_schema['item_contratacao'].items():
        if field_name in {'id_item', 'created_at'}:
            status = "🔧 TÉCNICO"
            style = "dim"
        elif field_name in mapped_item_fields:
            status = "✅ MAPEADO"
            style = "green"
        else:
            status = "❌ FALTANDO"
            style = "red"
        
        table_item.add_row(field_name, field_type.split()[0], status)
    
    console.print(table_item)

def test_api_field_extraction():
    """Testar extração de campos da API"""
    console.print("\n[bold]🧪 TESTE DE EXTRAÇÃO DE CAMPOS DA API[/bold]")
    
    contracts, items = get_simulated_api_data()
    
    # Teste com dados reais da transformação
    try:
        transformed_contract = apply_field_transformation(contracts[0], 'contratacao')
        transformed_item = apply_field_transformation(items[0], 'item_contratacao', contracts[0]['numeroControlePNCP'])
        
        # Mostrar alguns campos importantes
        important_contract_fields = [
            'numero_controle_pncp', 'objeto_compra', 'valor_total_estimado', 
            'modalidade_nome', 'orgao_entidade_cnpj', 'data_publicacao_pncp'
        ]
        
        console.print("[cyan]📋 Campos importantes do contrato:[/cyan]")
        for field in important_contract_fields:
            value = transformed_contract.get(field, "❌ AUSENTE")
            if value and value != "❌ AUSENTE":
                console.print(f"   ✅ {field}: {str(value)[:50]}...")
            else:
                console.print(f"   ❌ {field}: AUSENTE")
        
        important_item_fields = [
            'numero_controle_pncp', 'numero_item', 'descricao_item', 
            'valor_unitario_estimado', 'quantidade_item'
        ]
        
        console.print("\n[cyan]📦 Campos importantes do item:[/cyan]")
        for field in important_item_fields:
            value = transformed_item.get(field, "❌ AUSENTE")
            if value and value != "❌ AUSENTE":
                console.print(f"   ✅ {field}: {str(value)[:50]}...")
            else:
                console.print(f"   ❌ {field}: AUSENTE")
                
    except Exception as e:
        console.print(f"[red]❌ Erro no teste: {str(e)}[/red]")

def main():
    console.print(Panel("[bold blue]🔍 VERIFICAÇÃO FINAL - API PNCP ↔ SUPABASE V1[/bold blue]"))
    
    try:
        # 1. Verificar completude do mapeamento
        console.print("\n[bold]1️⃣ VERIFICANDO COMPLETUDE DO MAPEAMENTO[/bold]")
        contract_cov, item_cov, trans_contract, trans_item = verify_mapping_completeness()
        
        overall_coverage = (contract_cov + item_cov) / 2
        console.print(f"[bold]📊 COBERTURA GERAL: {overall_coverage:.1f}%[/bold]")
        console.print(f"   • Contratação: {contract_cov:.1f}%")
        console.print(f"   • Item Contratação: {item_cov:.1f}%")
        
        # 2. Relatório detalhado
        console.print("\n[bold]2️⃣ RELATÓRIO DETALHADO[/bold]")
        create_detailed_mapping_report()
        
        # 3. Teste de extração
        console.print("\n[bold]3️⃣ TESTE DE EXTRAÇÃO[/bold]")
        test_api_field_extraction()
        
        # 4. Resultado final
        console.print("\n[bold]4️⃣ RESULTADO FINAL[/bold]")
        
        if overall_coverage >= 95:
            console.print(Panel("[bold green]🎯 MAPEAMENTO EXCELENTE (≥95%) - PRONTO PARA PRODUÇÃO![/bold green]"))
        elif overall_coverage >= 85:
            console.print(Panel("[bold yellow]⚠️ MAPEAMENTO BOM (≥85%) - PEQUENOS AJUSTES RECOMENDADOS[/bold yellow]"))
        else:
            console.print(Panel("[bold red]❌ MAPEAMENTO PRECISA DE AJUSTES (<85%)[/bold red]"))
        
        # Recomendação
        console.print(f"\n[bold cyan]💡 RECOMENDAÇÃO:[/bold cyan]")
        if overall_coverage >= 90:
            console.print("   ✅ Script 03 está PRONTO para execução!")
            console.print("   ✅ Pode prosseguir para a próxima fase!")
        else:
            console.print("   ⚠️ Revisar campos faltantes antes de prosseguir")
            
    except Exception as e:
        console.print(f"[red]❌ Erro crítico: {str(e)}[/red]")

if __name__ == "__main__":
    main()
