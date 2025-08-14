#!/usr/bin/env python3
"""
Teste da API PNCP com a última data real da base
"""

import requests
from rich.console import Console

console = Console()

def test_api_with_real_date():
    """Testar API com data que sabemos ter dados"""
    console.print("[bold blue]🌐 Testando API com data real (2025-07-03)[/bold blue]")
    
    base_url = "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"
    test_date = "20250703"  # Data que sabemos ter dados na base
    
    console.print(f"🔍 Testando data: {test_date}")
    
    # Testar apenas alguns códigos para verificar se a API funciona
    test_codes = [1, 5, 8, 12]  # Códigos representativos
    
    for codigo in test_codes:
        params = {
            "dataInicial": test_date,
            "dataFinal": test_date,
            "codigoModalidadeContratacao": codigo,
            "pagina": 1,
            "tamanhoPagina": 10
        }
        
        try:
            console.print(f"⏳ Testando código {codigo}...")
            response = requests.get(base_url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                total_registros = data.get('totalRegistros', 0)
                total_paginas = data.get('totalPaginas', 0)
                registros_retornados = len(data.get('data', []))
                
                console.print(f"✅ Código {codigo}: {total_registros} registros, {total_paginas} páginas, {registros_retornados} retornados")
                
                # Mostrar primeiro contrato se existir
                if registros_retornados > 0:
                    primeiro = data['data'][0]
                    console.print(f"   📄 Primeiro contrato: {primeiro.get('numeroControlePNCP', 'N/A')}")
                    console.print(f"   📄 Modalidade: {primeiro.get('modalidadeNome', 'N/A')}")
                    console.print(f"   📄 Objeto: {primeiro.get('objetoCompra', 'N/A')[:50]}...")
                    
            elif response.status_code == 204:
                console.print(f"⚪ Código {codigo}: Sem dados (204)")
            elif response.status_code == 400:
                console.print(f"❌ Código {codigo}: Bad Request (400) - Parâmetros inválidos")
                console.print(f"   URL: {response.url}")
            else:
                console.print(f"⚠️ Código {codigo}: HTTP {response.status_code}")
                
        except requests.exceptions.Timeout:
            console.print(f"⏰ Código {codigo}: Timeout")
        except Exception as e:
            console.print(f"❌ Código {codigo}: {str(e)}")

def test_different_dates():
    """Testar com diferentes datas"""
    console.print("\n[bold blue]📅 Testando diferentes datas[/bold blue]")
    
    dates_to_test = [
        "20250703",  # Última data da base
        "20250702",  # Dia anterior
        "20250701",  # 1º de julho
        "20250630",  # 30 de junho
    ]
    
    base_url = "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"
    
    for test_date in dates_to_test:
        console.print(f"\n🔍 Data: {test_date}")
        
        params = {
            "dataInicial": test_date,
            "dataFinal": test_date,
            "codigoModalidadeContratacao": 5,  # Pregão eletrônico (mais comum)
            "pagina": 1,
            "tamanhoPagina": 5
        }
        
        try:
            response = requests.get(base_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                total = data.get('totalRegistros', 0)
                console.print(f"✅ {total} registros encontrados")
            elif response.status_code == 204:
                console.print("⚪ Sem dados")
            else:
                console.print(f"❌ HTTP {response.status_code}")
                
        except Exception as e:
            console.print(f"❌ Erro: {str(e)}")

if __name__ == "__main__":
    test_api_with_real_date()
    test_different_dates()
