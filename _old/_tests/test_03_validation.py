#!/usr/bin/env python3
"""
Script de teste para validar o funcionamento do 03_api_pncp_download.py
"""

import os
import sys
import requests
import psycopg2
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel

console = Console()

# Carregar configurações
script_dir = os.path.dirname(os.path.abspath(__file__))
v1_root = os.path.dirname(script_dir)
load_dotenv(os.path.join(v1_root, ".env"))

# Configurações do banco
DB_CONFIG = {
    'host': os.getenv('SUPABASE_HOST'),
    'port': os.getenv('SUPABASE_PORT'),
    'database': os.getenv('SUPABASE_DBNAME'),
    'user': os.getenv('SUPABASE_USER'),
    'password': os.getenv('SUPABASE_PASSWORD')
}

def test_database_connection():
    """Teste 1: Verificar conexão e última data"""
    console.print("\n[bold blue]🔗 TESTE 1: Conexão e Última Data[/bold blue]")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Verificar se as tabelas existem
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name IN ('contratacao', 'item_contratacao')
            ORDER BY table_name
        """)
        tables = cursor.fetchall()
        console.print(f"✅ Tabelas encontradas: {[t[0] for t in tables]}")
        
        # Contar registros
        cursor.execute("SELECT COUNT(*) FROM contratacao")
        count_contratacoes = cursor.fetchone()[0]
        console.print(f"✅ Contratações na base: {count_contratacoes:,}")
        
        cursor.execute("SELECT COUNT(*) FROM item_contratacao")
        count_itens = cursor.fetchone()[0]
        console.print(f"✅ Itens na base: {count_itens:,}")
        
        # Verificar última data
        cursor.execute("""
            SELECT data_publicacao_pncp 
            FROM contratacao 
            WHERE data_publicacao_pncp IS NOT NULL 
              AND data_publicacao_pncp ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
            ORDER BY data_publicacao_pncp DESC 
            LIMIT 5
        """)
        
        dates = cursor.fetchall()
        if dates:
            console.print("✅ Últimas 5 datas na base:")
            for i, date_row in enumerate(dates, 1):
                console.print(f"   {i}. {date_row[0]}")
            
            latest_date = dates[0][0].replace('-', '')
            console.print(f"✅ Última data (formato YYYYMMDD): {latest_date}")
        else:
            console.print("⚠️ Nenhuma data encontrada")
        
        conn.close()
        return True
        
    except Exception as e:
        console.print(f"❌ Erro: {e}")
        return False

def test_api_endpoints():
    """Teste 2: Verificar endpoints da API PNCP"""
    console.print("\n[bold blue]🌐 TESTE 2: Endpoints da API PNCP[/bold blue]")
    
    # Testar API de contratações
    base_url = "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"
    test_date = "20250103"  # Data recente
    
    console.print(f"🔍 Testando data: {test_date}")
    
    # Testar cada código de modalidade
    for codigo in range(1, 15):
        params = {
            "dataInicial": test_date,
            "dataFinal": test_date,
            "codigoModalidadeContratacao": codigo,
            "pagina": 1,
            "tamanhoPagina": 5  # Reduzido para teste
        }
        
        try:
            response = requests.get(base_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                total_registros = data.get('totalRegistros', 0)
                total_paginas = data.get('totalPaginas', 0)
                registros_retornados = len(data.get('data', []))
                
                console.print(f"✅ Código {codigo:2d}: {total_registros:3d} registros, {total_paginas:2d} páginas")
                
                # Se houver dados, testar API de itens para o primeiro contrato
                if registros_retornados > 0:
                    primeiro_contrato = data['data'][0]
                    numero_controle = primeiro_contrato.get('numeroControlePNCP')
                    if numero_controle:
                        test_items_api(numero_controle)
                        break  # Testar apenas um para economizar tempo
                        
            elif response.status_code == 204:
                console.print(f"⚪ Código {codigo:2d}: Sem dados (204)")
            else:
                console.print(f"⚠️ Código {codigo:2d}: HTTP {response.status_code}")
                
        except requests.exceptions.Timeout:
            console.print(f"⏰ Código {codigo:2d}: Timeout (provavelmente sem dados)")
        except Exception as e:
            console.print(f"❌ Código {codigo:2d}: Erro - {str(e)[:50]}")

def test_items_api(numero_controle_pncp):
    """Teste 3: API de itens"""
    console.print(f"\n[bold blue]📋 TESTE 3: API de Itens para {numero_controle_pncp}[/bold blue]")
    
    try:
        # Extrair informações do número de controle
        parts = numero_controle_pncp.split("-")
        if len(parts) != 3:
            console.print(f"❌ Formato inválido: {numero_controle_pncp}")
            return
        
        cnpj = parts[0]
        seq_and_year = parts[2].split("/")
        if len(seq_and_year) != 2:
            console.print(f"❌ Formato inválido: {numero_controle_pncp}")
            return
        
        seq = seq_and_year[0]
        ano_compra = seq_and_year[1]
        sequencial_compra = str(int(seq))  # Remove zeros à esquerda
        
        # Montar URL da API de itens
        url = f"https://pncp.gov.br/api/pncp//v1/orgaos/{cnpj}/compras/{ano_compra}/{sequencial_compra}/itens"
        console.print(f"🔗 URL: {url}")
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            items = response.json()
            console.print(f"✅ {len(items)} itens encontrados")
            if items:
                primeiro_item = items[0]
                console.print("📄 Campos do primeiro item:")
                for key, value in primeiro_item.items():
                    console.print(f"   {key}: {value}")
        elif response.status_code == 404:
            console.print("⚪ Sem itens (404)")
        else:
            console.print(f"⚠️ HTTP {response.status_code}")
            
    except Exception as e:
        console.print(f"❌ Erro: {e}")

def test_database_constraints():
    """Teste 4: Verificar constraints da base"""
    console.print("\n[bold blue]🔒 TESTE 4: Constraints da Base[/bold blue]")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Verificar constraints em contratacao
        cursor.execute("""
            SELECT constraint_name, constraint_type
            FROM information_schema.table_constraints 
            WHERE table_name = 'contratacao' 
            AND constraint_type IN ('UNIQUE', 'PRIMARY KEY')
        """)
        
        constraints_contratacao = cursor.fetchall()
        console.print("🔐 Constraints em 'contratacao':")
        for constraint_name, constraint_type in constraints_contratacao:
            console.print(f"   {constraint_type}: {constraint_name}")
        
        # Verificar constraints em item_contratacao
        cursor.execute("""
            SELECT constraint_name, constraint_type
            FROM information_schema.table_constraints 
            WHERE table_name = 'item_contratacao' 
            AND constraint_type IN ('UNIQUE', 'PRIMARY KEY')
        """)
        
        constraints_item = cursor.fetchall()
        console.print("🔐 Constraints em 'item_contratacao':")
        for constraint_name, constraint_type in constraints_item:
            console.print(f"   {constraint_type}: {constraint_name}")
        
        # Verificar se existem duplicatas em numero_controle_pncp
        cursor.execute("""
            SELECT numero_controle_pncp, COUNT(*) as count
            FROM contratacao 
            WHERE numero_controle_pncp IS NOT NULL
            GROUP BY numero_controle_pncp 
            HAVING COUNT(*) > 1
            LIMIT 5
        """)
        
        duplicatas = cursor.fetchall()
        if duplicatas:
            console.print("⚠️ Duplicatas encontradas em numero_controle_pncp:")
            for numero, count in duplicatas:
                console.print(f"   {numero}: {count} ocorrências")
        else:
            console.print("✅ Nenhuma duplicata em numero_controle_pncp")
        
        # Verificar tipos de dados
        cursor.execute("""
            SELECT column_name, data_type, character_maximum_length
            FROM information_schema.columns 
            WHERE table_name = 'contratacao' 
            AND column_name = 'numero_controle_pncp'
        """)
        
        column_info = cursor.fetchone()
        if column_info:
            console.print(f"📊 Tipo do campo numero_controle_pncp: {column_info[1]}")
        
        conn.close()
        
    except Exception as e:
        console.print(f"❌ Erro: {e}")

def test_data_mapping():
    """Teste 5: Verificar mapeamento de dados"""
    console.print("\n[bold blue]🗺️ TESTE 5: Mapeamento de Dados[/bold blue]")
    
    try:
        # Adicionar db ao path
        db_dir = os.path.join(v1_root, "db")
        sys.path.insert(0, db_dir)
        
        # Importar funções de mapeamento
        from de_para_pncp_v1 import DE_PARA_PNCP, apply_field_transformation, get_table_fields
        
        console.print("✅ Importação do mapeamento bem-sucedida")
        
        # Verificar se as tabelas estão mapeadas
        console.print("📋 Tabelas mapeadas:")
        for table_name in DE_PARA_PNCP.keys():
            console.print(f"   - {table_name}")
        
        # Testar com dados fictícios
        test_contrato = {
            'numeroControlePNCP': '12345678000100-1-000001/2025',
            'modalidadeNome': 'Pregão Eletrônico',
            'objetoCompra': 'Teste de objeto',
            'valorTotalEstimado': 1000.50
        }
        
        normalized = apply_field_transformation(test_contrato, 'contratacao')
        console.print("✅ Normalização de contrato teste:")
        for key, value in normalized.items():
            console.print(f"   {key}: {value}")
        
    except Exception as e:
        console.print(f"❌ Erro no mapeamento: {e}")

def main():
    """Executar todos os testes"""
    console.print(Panel("[bold green]🧪 TESTES DE VALIDAÇÃO - SCRIPT 03[/bold green]"))
    
    # Executar todos os testes
    test_database_connection()
    test_api_endpoints() 
    test_database_constraints()
    test_data_mapping()
    
    console.print("\n[bold green]✅ Testes concluídos![/bold green]")

if __name__ == "__main__":
    main()
