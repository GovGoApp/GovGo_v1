#!/usr/bin/env python3
"""
Análise dos Problemas de Timeout da API PNCP
============================================
Este script analisa os padrões de erro para identificar:
- Modalidades mais problemáticas
- Horários com mais timeouts
- Estratégias personalizadas por modalidade
"""

import os
import json
import time
import requests
from datetime import datetime, timedelta
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from collections import defaultdict

console = Console()

def test_modalidade_response_time(codigo, date_str="20250804"):
    """Testa o tempo de resposta de uma modalidade específica"""
    url = "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"
    params = {
        "dataInicial": date_str,
        "dataFinal": date_str,
        "codigoModalidadeContratacao": codigo,
        "pagina": 1,
        "tamanhoPagina": 10  # Pequeno para teste rápido
    }
    
    start_time = time.time()
    try:
        response = requests.get(url, params=params, timeout=60)
        end_time = time.time()
        response_time = end_time - start_time
        
        if response.status_code == 200:
            data = response.json()
            total_registros = data.get("totalRegistros", 0)
            total_paginas = data.get("totalPaginas", 0)
            return {
                "status": "success",
                "response_time": response_time,
                "total_registros": total_registros,
                "total_paginas": total_paginas,
                "status_code": response.status_code
            }
        elif response.status_code == 204:
            return {
                "status": "no_data",
                "response_time": response_time,
                "total_registros": 0,
                "total_paginas": 0,
                "status_code": response.status_code
            }
        else:
            return {
                "status": "error",
                "response_time": response_time,
                "total_registros": 0,
                "total_paginas": 0,
                "status_code": response.status_code
            }
            
    except requests.exceptions.Timeout:
        return {
            "status": "timeout",
            "response_time": 60,
            "total_registros": 0,
            "total_paginas": 0,
            "status_code": "TIMEOUT"
        }
    except Exception as e:
        return {
            "status": "error",
            "response_time": 0,
            "total_registros": 0,
            "total_paginas": 0,
            "status_code": str(e)
        }

def analyze_modalidades():
    """Analisa todas as modalidades para identificar problemas"""
    console.print(Panel("[bold blue]🔍 ANÁLISE DE MODALIDADES - API PNCP[/bold blue]"))
    
    modalidades = {
        1: "Convite",
        2: "Tomada de Preços",
        3: "Concorrência",
        4: "Pregão Presencial",
        5: "Pregão Eletrônico SRP",
        6: "Pregão Eletrônico",
        7: "RDC Presencial",
        8: "RDC Eletrônico",
        9: "Leilão Eletrônico",
        10: "Concurso",
        11: "Chamamento Público",
        12: "Credenciamento",
        13: "Pré-qualificação",
        14: "Outras"
    }
    
    results = {}
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        console=console
    ) as progress:
        task = progress.add_task("Testando modalidades...", total=len(modalidades))
        
        for codigo, nome in modalidades.items():
            progress.update(task, description=f"Testando {codigo}: {nome}")
            result = test_modalidade_response_time(codigo)
            results[codigo] = {
                "nome": nome,
                **result
            }
            progress.advance(task)
            time.sleep(1)  # Pausa entre testes
    
    return results

def create_analysis_report(results):
    """Cria relatório de análise"""
    console.print("\n[bold]📊 RELATÓRIO DE ANÁLISE DAS MODALIDADES[/bold]")
    
    # Tabela principal
    table = Table(title="Análise de Performance por Modalidade")
    table.add_column("Código", style="cyan", width=6)
    table.add_column("Nome", style="white", width=20)
    table.add_column("Status", style="bold", width=12)
    table.add_column("Tempo (s)", style="yellow", width=10)
    table.add_column("Registros", style="green", width=10)
    table.add_column("Páginas", style="blue", width=8)
    table.add_column("Risco", style="red", width=8)
    
    problem_codes = []
    slow_codes = []
    heavy_codes = []
    
    for codigo, data in results.items():
        status = data["status"]
        response_time = data["response_time"]
        total_registros = data["total_registros"]
        total_paginas = data["total_paginas"]
        nome = data["nome"]
        
        # Determinar status visual
        if status == "timeout":
            status_display = "[red]TIMEOUT[/red]"
            risco = "[red]ALTO[/red]"
            problem_codes.append(codigo)
        elif status == "error":
            status_display = "[red]ERRO[/red]"
            risco = "[red]ALTO[/red]"
            problem_codes.append(codigo)
        elif response_time > 10:
            status_display = "[yellow]LENTO[/yellow]"
            risco = "[yellow]MÉDIO[/yellow]"
            slow_codes.append(codigo)
        elif total_registros > 1000:
            status_display = "[orange1]PESADO[/orange1]"
            risco = "[orange1]MÉDIO[/orange1]"
            heavy_codes.append(codigo)
        elif status == "no_data":
            status_display = "[dim]SEM DADOS[/dim]"
            risco = "[green]BAIXO[/green]"
        else:
            status_display = "[green]OK[/green]"
            risco = "[green]BAIXO[/green]"
        
        table.add_row(
            str(codigo),
            nome,
            status_display,
            f"{response_time:.2f}",
            f"{total_registros:,}",
            str(total_paginas),
            risco
        )
    
    console.print(table)
    
    # Análise dos problemas
    console.print("\n[bold]🎯 ANÁLISE DE PROBLEMAS IDENTIFICADOS[/bold]")
    
    if problem_codes:
        console.print(f"[red]❌ Modalidades com TIMEOUT/ERRO: {problem_codes}[/red]")
        console.print("   Causa: API sobrecarregada ou modalidades muito populares")
        console.print("   Solução: Timeout maior + retry + backoff exponencial")
    
    if slow_codes:
        console.print(f"[yellow]⚠️ Modalidades LENTAS (>10s): {slow_codes}[/yellow]")
        console.print("   Causa: Grande volume de dados")
        console.print("   Solução: Processamento sequencial + timeout estendido")
    
    if heavy_codes:
        console.print(f"[orange1]📊 Modalidades com MUITOS DADOS: {heavy_codes}[/orange1]")
        console.print("   Causa: Alto volume de contratações")
        console.print("   Solução: Paginação otimizada + rate limiting")
    
    return problem_codes, slow_codes, heavy_codes

def generate_custom_strategy(problem_codes, slow_codes, heavy_codes):
    """Gera estratégia personalizada baseada na análise"""
    console.print("\n[bold]🔧 ESTRATÉGIA PERSONALIZADA RECOMENDADA[/bold]")
    
    strategy = {
        "high_risk_codes": problem_codes,  # Timeout máximo, retry agressivo
        "slow_codes": slow_codes,         # Timeout estendido, sem paralelismo
        "heavy_codes": heavy_codes,       # Rate limiting agressivo
        "safe_codes": []                  # Processamento normal
    }
    
    # Códigos seguros (nem problemáticos, nem lentos, nem pesados)
    all_problem_codes = set(problem_codes + slow_codes + heavy_codes)
    strategy["safe_codes"] = [i for i in range(1, 15) if i not in all_problem_codes]
    
    console.print(f"[red]🚨 Alto Risco (timeout 120s, retry 8x): {strategy['high_risk_codes']}[/red]")
    console.print(f"[yellow]⚠️ Lentos (timeout 90s, sequencial): {strategy['slow_codes']}[/yellow]")
    console.print(f"[orange1]📊 Pesados (rate limit 1/s): {strategy['heavy_codes']}[/orange1]")
    console.print(f"[green]✅ Seguros (padrão 45s): {strategy['safe_codes']}[/green]")
    
    return strategy

def test_items_endpoint():
    """Testa problemas específicos do endpoint de itens"""
    console.print("\n[bold]📦 TESTE DO ENDPOINT DE ITENS[/bold]")
    
    # Alguns contratos de exemplo para testar
    test_contracts = [
        "00394544000185-1-001763/2025",  # Mencionado no erro
        "15126437000305-1-001906/2025",  # Mencionado no erro
    ]
    
    results = []
    
    for numero_controle in test_contracts:
        try:
            parts = numero_controle.split("-")
            cnpj = parts[0]
            seq_and_year = parts[2].split("/")
            seq = seq_and_year[0]
            ano_compra = seq_and_year[1]
            sequencial_compra = str(int(seq))
            
            url = f"https://pncp.gov.br/api/pncp//v1/orgaos/{cnpj}/compras/{ano_compra}/{sequencial_compra}/itens"
            
            start_time = time.time()
            response = requests.get(url, timeout=60)
            end_time = time.time()
            response_time = end_time - start_time
            
            results.append({
                "numero_controle": numero_controle,
                "status_code": response.status_code,
                "response_time": response_time,
                "url": url
            })
            
            if response.status_code == 200:
                console.print(f"   ✅ {numero_controle}: {response_time:.2f}s")
            elif response.status_code == 408:
                console.print(f"   ❌ {numero_controle}: HTTP 408 (Request Timeout)")
            else:
                console.print(f"   ⚠️ {numero_controle}: HTTP {response.status_code}")
                
        except requests.exceptions.Timeout:
            console.print(f"   🕒 {numero_controle}: TIMEOUT após 60s")
        except Exception as e:
            console.print(f"   💥 {numero_controle}: {str(e)}")
        
        time.sleep(2)  # Pausa entre testes
    
    return results

def main():
    """Executa análise completa"""
    console.print(Panel("[bold blue]🔍 DIAGNÓSTICO COMPLETO - API PNCP[/bold blue]"))
    
    # 1. Análise das modalidades
    modalidade_results = analyze_modalidades()
    problem_codes, slow_codes, heavy_codes = create_analysis_report(modalidade_results)
    
    # 2. Estratégia personalizada
    strategy = generate_custom_strategy(problem_codes, slow_codes, heavy_codes)
    
    # 3. Teste de itens
    items_results = test_items_endpoint()
    
    # 4. Recomendações finais
    console.print(Panel(f"""
[bold yellow]🎯 RECOMENDAÇÕES FINAIS[/bold yellow]

[cyan]Para resolver os erros reportados:[/cyan]

1️⃣ [red]Timeouts de Conexão (HTTPSConnectionPool):[/red]
   • Aumentar timeout para 60-120s nas modalidades problemáticas
   • Implementar retry com backoff exponencial (2, 4, 8, 16s)
   • Reduzir paralelismo de 10→3 workers simultâneos
   • Adicionar rate limiting (máx 3 req/s)

2️⃣ [yellow]HTTP 408 (Request Timeout):[/yellow]
   • Problema específico do servidor PNCP
   • Implementar retry específico para 408
   • Adicionar delay entre tentativas (5-10s)
   • Circuit breaker após múltiplas falhas

3️⃣ [green]Estratégia por Modalidade:[/green]
   • Alto risco {problem_codes}: timeout 120s, retry 8x
   • Lentos {slow_codes}: timeout 90s, processamento sequencial  
   • Pesados {heavy_codes}: rate limiting agressivo
   • Seguros {strategy['safe_codes']}: configuração padrão

4️⃣ [blue]Monitoramento:[/blue]
   • Log detalhado de response times
   • Contadores de erro por endpoint
   • Circuit breaker automático
   • Alertas para degradação de performance

[bold green]✅ Use o script 03_api_pncp_download_robust.py para implementar essas melhorias![/bold green]
    """))

if __name__ == "__main__":
    main()
