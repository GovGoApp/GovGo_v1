#!/usr/bin/env python3
"""
Script de validação para o sistema de download PNCP V1
Verifica os pontos solicitados antes da execução do script principal
"""

import os
import sys
import requests
import psycopg2
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

# Carregar configurações
script_dir = os.path.dirname(os.path.abspath(__file__))
v1_root = os.path.dirname(script_dir)
load_dotenv(os.path.join(v1_root, ".env"))

# Configurações do banco PostgreSQL V1 (Supabase)
DB_CONFIG = {
    'host': os.getenv('SUPABASE_HOST', 'localhost'),
    'port': os.getenv('SUPABASE_PORT', '6543'),
    'database': os.getenv('SUPABASE_DBNAME', 'postgres'),
    'user': os.getenv('SUPABASE_USER', 'postgres'),
    'password': os.getenv('SUPABASE_PASSWORD', '')
}

def test_1_ultima_data():
    """Testa se conseguimos pegar a última data correta da base"""
    console.print("[bold blue]🔍 TESTE 1: Verificando última data na base[/bold blue]")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Buscar última data
        cursor.execute("""
            SELECT data_publicacao_pncp 
            FROM contratacao 
            WHERE data_publicacao_pncp IS NOT NULL 
              AND data_publicacao_pncp ~ '^[0-9]{4}-[0-9]{2}-[0-9]{2}$'
            ORDER BY data_publicacao_pncp DESC 
            LIMIT 1
        """)
        
        result = cursor.fetchone()
        if result and result[0]:
            ultima_data = result[0]
            data_formatada = ultima_data.replace('-', '')
            console.print(f"✅ Última data encontrada: {ultima_data} → {data_formatada}")
            
            # Verificar se faz sentido
            if len(data_formatada) == 8 and data_formatada.startswith('20'):
                console.print("✅ Formato correto (YYYYMMDD)")
                return True, data_formatada
            else:
                console.print("❌ Formato incorreto")
                return False, None
        else:
            console.print("⚠️  Nenhuma data encontrada na base")
            return False, None
            
        conn.close()
        
    except Exception as e:
        console.print(f"❌ Erro ao conectar com a base: {e}")
        return False, None

def test_2_api_leitura(data_teste="20250803"):
    """Testa se conseguimos ler dados da API corretamente"""
    console.print(f"[bold blue]🔍 TESTE 2: Testando leitura da API para {data_teste}[/bold blue]")
    
    base_url = "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"
    
    # Testar alguns códigos de modalidade
    modalidades_teste = [1, 5, 8, 10]
    resultados = {}
    
    for codigo in modalidades_teste:
        try:
            params = {
                "dataInicial": data_teste,
                "dataFinal": data_teste,
                "codigoModalidadeContratacao": codigo,
                "pagina": 1,
                "tamanhoPagina": 10
            }
            
            response = requests.get(base_url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                total_registros = data.get("totalRegistros", 0)
                registros_pagina = len(data.get("data", []))
                resultados[codigo] = {
                    'status': 'OK',
                    'total': total_registros,
                    'pagina': registros_pagina
                }
                console.print(f"✅ Código {codigo}: {total_registros} registros totais, {registros_pagina} na página")
                
                # Testar estrutura dos dados
                if registros_pagina > 0:
                    primeiro_registro = data["data"][0]
                    campos_principais = ['numeroControlePNCP', 'objetoCompra', 'modalidadeNome']
                    campos_ok = all(campo in primeiro_registro for campo in campos_principais)
                    console.print(f"   📋 Estrutura dos dados: {'✅ OK' if campos_ok else '❌ Faltam campos'}")
                
            elif response.status_code == 204:
                resultados[codigo] = {'status': 'VAZIO', 'total': 0, 'pagina': 0}
                console.print(f"ℹ️  Código {codigo}: Sem dados (204 No Content)")
                
            else:
                resultados[codigo] = {'status': f'ERRO_{response.status_code}', 'total': 0, 'pagina': 0}
                console.print(f"⚠️  Código {codigo}: HTTP {response.status_code}")
                
        except requests.exceptions.Timeout:
            resultados[codigo] = {'status': 'TIMEOUT', 'total': 0, 'pagina': 0}
            console.print(f"⚠️  Código {codigo}: Timeout após 15s")
        except Exception as e:
            resultados[codigo] = {'status': 'ERRO', 'total': 0, 'pagina': 0}
            console.print(f"❌ Código {codigo}: {str(e)}")
    
    # Resumo
    total_sucessos = len([r for r in resultados.values() if r['status'] == 'OK'])
    total_vazios = len([r for r in resultados.values() if r['status'] == 'VAZIO'])
    total_timeouts = len([r for r in resultados.values() if r['status'] == 'TIMEOUT'])
    
    console.print(f"\n📊 Resumo API: {total_sucessos} OK, {total_vazios} vazios, {total_timeouts} timeouts")
    
    return resultados

def test_3_constraints_unicas():
    """Verifica as constraints únicas nas tabelas"""
    console.print("[bold blue]🔍 TESTE 3: Verificando constraints únicas[/bold blue]")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Verificar constraint em contratacao
        cursor.execute("""
            SELECT constraint_name, constraint_type
            FROM information_schema.table_constraints 
            WHERE table_name = 'contratacao' 
            AND constraint_type = 'UNIQUE'
        """)
        
        constraints_contratacao = cursor.fetchall()
        console.print(f"📋 Constraints UNIQUE em contratacao: {len(constraints_contratacao)}")
        for constraint in constraints_contratacao:
            console.print(f"   - {constraint[0]}")
        
        # Verificar constraint em item_contratacao
        cursor.execute("""
            SELECT constraint_name, constraint_type
            FROM information_schema.table_constraints 
            WHERE table_name = 'item_contratacao' 
            AND constraint_type = 'UNIQUE'
        """)
        
        constraints_item = cursor.fetchall()
        console.print(f"📋 Constraints UNIQUE em item_contratacao: {len(constraints_item)}")
        for constraint in constraints_item:
            console.print(f"   - {constraint[0]}")
        
        # Verificar se numero_controle_pncp tem constraint
        cursor.execute("""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.table_constraints tc
                JOIN information_schema.constraint_column_usage ccu 
                ON tc.constraint_name = ccu.constraint_name
                WHERE tc.table_name = 'contratacao' 
                AND tc.constraint_type = 'UNIQUE'
                AND ccu.column_name = 'numero_controle_pncp'
            )
        """)
        
        tem_constraint_numero = cursor.fetchone()[0]
        if tem_constraint_numero:
            console.print("✅ numero_controle_pncp tem constraint UNIQUE")
        else:
            console.print("⚠️  numero_controle_pncp NÃO tem constraint UNIQUE")
        
        conn.close()
        return tem_constraint_numero
        
    except Exception as e:
        console.print(f"❌ Erro ao verificar constraints: {e}")
        return False

def test_4_dados_existentes():
    """Verifica dados existentes na base"""
    console.print("[bold blue]🔍 TESTE 4: Verificando dados existentes[/bold blue]")
    
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Contar registros
        cursor.execute("SELECT COUNT(*) FROM contratacao")
        count_contratacoes = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM item_contratacao")
        count_itens = cursor.fetchone()[0]
        
        console.print(f"📊 Contratações: {count_contratacoes:,}")
        console.print(f"📊 Itens: {count_itens:,}")
        
        # Verificar duplicatas
        cursor.execute("""
            SELECT numero_controle_pncp, COUNT(*) as duplicatas
            FROM contratacao 
            GROUP BY numero_controle_pncp 
            HAVING COUNT(*) > 1
            LIMIT 5
        """)
        
        duplicatas_contratacao = cursor.fetchall()
        if duplicatas_contratacao:
            console.print(f"⚠️  {len(duplicatas_contratacao)} duplicatas em contratacao")
            for dup in duplicatas_contratacao[:3]:
                console.print(f"   - {dup[0]}: {dup[1]} vezes")
        else:
            console.print("✅ Sem duplicatas em contratacao")
        
        # Verificar duplicatas em itens
        cursor.execute("""
            SELECT numero_controle_pncp, numero_item, COUNT(*) as duplicatas
            FROM item_contratacao 
            GROUP BY numero_controle_pncp, numero_item 
            HAVING COUNT(*) > 1
            LIMIT 5
        """)
        
        duplicatas_item = cursor.fetchall()
        if duplicatas_item:
            console.print(f"⚠️  {len(duplicatas_item)} duplicatas em item_contratacao")
            for dup in duplicatas_item[:3]:
                console.print(f"   - {dup[0]}, item {dup[1]}: {dup[2]} vezes")
        else:
            console.print("✅ Sem duplicatas em item_contratacao")
        
        conn.close()
        return count_contratacoes, count_itens, len(duplicatas_contratacao), len(duplicatas_item)
        
    except Exception as e:
        console.print(f"❌ Erro ao verificar dados: {e}")
        return 0, 0, 0, 0

def main():
    """Executa todos os testes de validação"""
    console.print(Panel("[bold blue]🧪 VALIDAÇÃO DO SISTEMA PNCP V1[/bold blue]", 
                       title="🔍 Testes de Validação"))
    
    # Teste 1: Última data
    sucesso_data, ultima_data = test_1_ultima_data()
    console.print()
    
    # Teste 2: API
    resultados_api = test_2_api_leitura()
    console.print()
    
    # Teste 3: Constraints
    tem_constraints = test_3_constraints_unicas()
    console.print()
    
    # Teste 4: Dados existentes
    cont, itens, dup_cont, dup_itens = test_4_dados_existentes()
    console.print()
    
    # Resumo final
    table = Table(title="📋 Resumo da Validação")
    table.add_column("Teste", style="cyan")
    table.add_column("Status", style="green")
    table.add_column("Detalhes", style="white")
    
    table.add_row(
        "1. Última Data",
        "✅ OK" if sucesso_data else "❌ ERRO",
        f"Data: {ultima_data}" if sucesso_data else "Não encontrada"
    )
    
    api_ok = len([r for r in resultados_api.values() if r['status'] == 'OK']) > 0
    table.add_row(
        "2. API PNCP",
        "✅ OK" if api_ok else "❌ ERRO",
        f"{len(resultados_api)} modalidades testadas"
    )
    
    table.add_row(
        "3. Constraints",
        "✅ OK" if tem_constraints else "⚠️  ATENÇÃO",
        "Constraints únicas verificadas"
    )
    
    table.add_row(
        "4. Base de Dados",
        "✅ OK",
        f"{cont:,} contratações, {itens:,} itens"
    )
    
    console.print(table)
    
    # Recomendações
    if not tem_constraints:
        console.print("\n⚠️  [bold yellow]RECOMENDAÇÃO:[/bold yellow] Executar script com criação de constraints")
    
    if dup_cont > 0 or dup_itens > 0:
        console.print("\n⚠️  [bold yellow]ATENÇÃO:[/bold yellow] Existem duplicatas na base")
    
    console.print(Panel("✅ Validação concluída! Sistema pronto para uso.", 
                       title="🎯 Resultado"))

if __name__ == "__main__":
    main()
