#!/usr/bin/env python3
"""
Script para atualizar campos faltantes na tabela contratacao do SQLite
Busca dados da API do PNCP usando a URL correta e atualiza apenas os campos extras
"""

import requests
import sqlite3
import json
import time
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.table import Table

console = Console()

# Configurações
DB_PATH = r"C:\Users\Haroldo Duraes\Desktop\GOvGO\v0\#DATA\PNCP\DB\pncp_v2.db"
MAX_WORKERS = 15  # Número de workers para paralelização
TIMEOUT = 30  # Timeout para requisições
BATCH_SIZE = 5000  # Tamanho do lote para processamento

# Lock para operações thread-safe no banco
db_lock = threading.Lock()

def log_message(message, log_type="info"):
    """Log padronizado"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_colors = {
        "info": "white",
        "success": "green", 
        "warning": "yellow",
        "error": "red",
        "debug": "cyan"
    }
    color = log_colors.get(log_type, "white")
    console.print(f"[{color}]{timestamp} - {message}[/{color}]")

def parse_numero_controle(numero_controle):
    """
    Extrai CNPJ, ano e sequencial do numeroControlePNCP
    Formato: {cnpj}-1-{sequencialCompra}/{anocompra}
    Exemplo: 00394452000103-1-000191/2021
    """
    try:
        if not numero_controle or not isinstance(numero_controle, str):
            return None, None, None
            
        # Validar formato
        if not re.match(r'^\d+-\d+-\d+/\d+$', numero_controle):
            return None, None, None
            
        # Dividir por '-'
        parts = numero_controle.split('-')
        if len(parts) != 3:
            return None, None, None
            
        cnpj = parts[0]
        # parts[1] é sempre '1', ignoramos
        seq_and_year = parts[2].split('/')
        
        if len(seq_and_year) != 2:
            return None, None, None
            
        sequencial_str = seq_and_year[0]
        ano = seq_and_year[1]
        
        # Remover zeros à esquerda do sequencial
        sequencial = str(int(sequencial_str))
        
        return cnpj, ano, sequencial
        
    except Exception as e:
        log_message(f"Erro ao fazer parse de {numero_controle}: {e}", "error")
        return None, None, None

def fetch_contract_details(numero_controle):
    """
    Busca detalhes do contrato na API do PNCP
    """
    try:
        cnpj, ano, sequencial = parse_numero_controle(numero_controle)
        
        if not cnpj or not ano or not sequencial:
            return None
            
        # Montar URL da API
        url = f"https://pncp.gov.br/api/consulta/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}"
        
        # Fazer requisição
        response = requests.get(url, timeout=TIMEOUT)
        
        if response.status_code == 200:
            return response.json()
        else:
            log_message(f"Erro HTTP {response.status_code} para {numero_controle}", "warning")
            return None
            
    except requests.exceptions.Timeout:
        log_message(f"Timeout para {numero_controle}", "warning")
        return None
    except Exception as e:
        log_message(f"Erro ao buscar {numero_controle}: {e}", "error")
        return None

def extract_extra_fields(contract_data):
    """
    Extrai apenas os campos extras que foram adicionados recentemente
    """
    if not contract_data:
        return None
        
    try:
        # Extrair campos extras
        extra_fields = {}
        
        # Campos simples
        extra_fields['informacaoComplementar'] = contract_data.get('informacaoComplementar')
        extra_fields['justificativaPresencial'] = contract_data.get('justificativaPresencial')
        extra_fields['linkSistemaOrigem'] = contract_data.get('linkSistemaOrigem')
        extra_fields['linkProcessoEletronico'] = contract_data.get('linkProcessoEletronico')
        extra_fields['modalidadeNome'] = contract_data.get('modalidadeNome')
        extra_fields['modoDisputaNome'] = contract_data.get('modoDisputaNome')
        extra_fields['tipoInstrumentoConvocatorioNome'] = contract_data.get('tipoInstrumentoConvocatorioNome')
        extra_fields['situacaoCompraNome'] = contract_data.get('situacaoCompraNome')
        extra_fields['existeResultado'] = contract_data.get('existeResultado')
        extra_fields['orcamentoSigilosoCodigo'] = contract_data.get('orcamentoSigilosoCodigo')
        extra_fields['orcamentoSigilosoDescricao'] = contract_data.get('orcamentoSigilosoDescricao')
        extra_fields['usuarioNome'] = contract_data.get('usuarioNome')
        
        # Amparo legal
        amparo_legal = contract_data.get('amparoLegal', {})
        if amparo_legal:
            extra_fields['amparoLegal_nome'] = amparo_legal.get('nome')
            extra_fields['amparoLegal_descricao'] = amparo_legal.get('descricao')
        
        # Órgão sub-rogado
        orgao_sub_rogado = contract_data.get('orgaoSubRogado', {})
        if orgao_sub_rogado:
            extra_fields['orgaoSubRogado_cnpj'] = orgao_sub_rogado.get('cnpj')
            extra_fields['orgaoSubRogado_razaoSocial'] = orgao_sub_rogado.get('razaoSocial')
            extra_fields['orgaoSubRogado_poderId'] = orgao_sub_rogado.get('poderId')
            extra_fields['orgaoSubRogado_esferaId'] = orgao_sub_rogado.get('esferaId')
        
        # Unidade sub-rogada
        unidade_sub_rogada = contract_data.get('unidadeSubRogada', {})
        if unidade_sub_rogada:
            extra_fields['unidadeSubRogada_ufNome'] = unidade_sub_rogada.get('ufNome')
            extra_fields['unidadeSubRogada_ufSigla'] = unidade_sub_rogada.get('ufSigla')
            extra_fields['unidadeSubRogada_municipioNome'] = unidade_sub_rogada.get('municipioNome')
            extra_fields['unidadeSubRogada_codigoUnidade'] = unidade_sub_rogada.get('codigoUnidade')
            extra_fields['unidadeSubRogada_nomeUnidade'] = unidade_sub_rogada.get('nomeUnidade')
            extra_fields['unidadeSubRogada_codigoIbge'] = unidade_sub_rogada.get('codigoIbge')
        
        # Fontes orçamentárias (converter para JSON)
        fontes_orcamentarias = contract_data.get('fontesOrcamentarias', [])
        if fontes_orcamentarias:
            extra_fields['fontesOrcamentarias'] = json.dumps(fontes_orcamentarias, ensure_ascii=False)
        
        return extra_fields
        
    except Exception as e:
        log_message(f"Erro ao extrair campos extras: {e}", "error")
        return None

def get_contracts_to_update(limit=None):
    """
    Busca contratos que precisam ser atualizados
    """
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Buscar contratos com campos extras vazios
        query = """
            SELECT numeroControlePNCP, ID_CONTRATACAO 
            FROM contratacao 
            WHERE numeroControlePNCP IS NOT NULL 
            AND (
                informacaoComplementar IS NULL OR
                modalidadeNome IS NULL OR
                situacaoCompraNome IS NULL OR
                amparoLegal_nome IS NULL
            )
        """
        
        if limit:
            query += f" LIMIT {limit}"
            
        cursor.execute(query)
        contracts = cursor.fetchall()
        
        conn.close()
        
        log_message(f"Encontrados {len(contracts)} contratos para atualizar", "info")
        return contracts
        
    except Exception as e:
        log_message(f"Erro ao buscar contratos: {e}", "error")
        return []

def update_contract_in_db(contract_id, extra_fields):
    """
    Atualiza um contrato na base de dados com os campos extras
    """
    try:
        with db_lock:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Montar query UPDATE apenas com campos que têm valor
            set_clauses = []
            values = []
            
            for field, value in extra_fields.items():
                if value is not None:
                    set_clauses.append(f"{field} = ?")
                    values.append(value)
            
            if not set_clauses:
                conn.close()
                return False
                
            query = f"""
                UPDATE contratacao 
                SET {', '.join(set_clauses)}
                WHERE ID_CONTRATACAO = ?
            """
            
            values.append(contract_id)
            cursor.execute(query, values)
            conn.commit()
            conn.close()
            
            return True
            
    except Exception as e:
        log_message(f"Erro ao atualizar contrato ID {contract_id}: {e}", "error")
        return False

def process_contract_batch(contracts_batch, progress, batch_task_id):
    """
    Processa um lote de contratos
    """
    results = {
        'success': 0,
        'failed': 0,
        'api_errors': 0,
        'db_errors': 0
    }
    
    # Armazenar dados em memória para processamento em lote
    contracts_data = []
    
    # Fase 1: Buscar dados da API
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submeter todas as tarefas
        future_to_contract = {
            executor.submit(fetch_contract_details, numero_controle): (numero_controle, contract_id)
            for numero_controle, contract_id in contracts_batch
        }
        
        # Processar resultados conforme chegam
        for future in as_completed(future_to_contract):
            numero_controle, contract_id = future_to_contract[future]
            
            try:
                contract_data = future.result()
                
                if contract_data:
                    extra_fields = extract_extra_fields(contract_data)
                    if extra_fields:
                        contracts_data.append((contract_id, extra_fields))
                    else:
                        results['failed'] += 1
                else:
                    results['api_errors'] += 1
                    
            except Exception as e:
                log_message(f"Erro ao processar {numero_controle}: {e}", "error")
                results['failed'] += 1
            
            # Atualizar progresso
            progress.update(batch_task_id, advance=1)
    
    # Fase 2: Atualizar base de dados
    for contract_id, extra_fields in contracts_data:
        if update_contract_in_db(contract_id, extra_fields):
            results['success'] += 1
        else:
            results['db_errors'] += 1
    
    return results

def main():
    """
    Função principal
    """
    console.print(Panel("[bold green]🔄 ATUALIZAÇÃO DE CAMPOS FALTANTES - API PNCP[/bold green]"))
    log_message("Iniciando atualização de campos faltantes", "info")
    
    # Verificar se o banco existe
    if not os.path.exists(DB_PATH):
        console.print(f"[bold red]❌ Banco de dados não encontrado: {DB_PATH}[/bold red]")
        return
    
    # Buscar contratos para atualizar (limitado para teste)
    contracts = get_contracts_to_update(limit=10000)  # Processar 10k por vez
    
    if not contracts:
        console.print("[bold green]✅ Todos os contratos já estão atualizados[/bold green]")
        return
    
    # Dividir em lotes
    total_contracts = len(contracts)
    batches = [contracts[i:i + BATCH_SIZE] for i in range(0, total_contracts, BATCH_SIZE)]
    
    log_message(f"Processando {total_contracts} contratos em {len(batches)} lotes", "info")
    
    # Estatísticas
    total_stats = {
        'success': 0,
        'failed': 0,
        'api_errors': 0,
        'db_errors': 0
    }
    
    # Progress bar
    progress = Progress(
        TextColumn("[bold white]{task.description}"),
        BarColumn(complete_style="green", finished_style="bright_green"),
        "[progress.percentage]{task.percentage:>3.0f}%",
        "•",
        TimeElapsedColumn(),
        "•",
        TimeRemainingColumn(),
        console=console
    )
    
    with progress:
        main_task = progress.add_task(f"[bold green]📊 Processando {len(batches)} lotes", total=len(batches))
        
        for i, batch in enumerate(batches, 1):
            log_message(f"Processando lote {i}/{len(batches)} ({len(batch)} contratos)", "info")
            
            batch_task = progress.add_task(f"[bold yellow]  Lote {i} ({len(batch)} contratos)", total=len(batch))
            
            # Processar lote
            batch_results = process_contract_batch(batch, progress, batch_task)
            
            # Atualizar estatísticas
            for key in total_stats:
                total_stats[key] += batch_results[key]
            
            # Remover task do lote
            progress.remove_task(batch_task)
            
            # Log do lote
            log_message(f"Lote {i} concluído: {batch_results['success']} sucessos, {batch_results['failed']} falhas", "info")
            
            # Atualizar progresso principal
            progress.update(main_task, advance=1)
    
    # Relatório final
    console.print(Panel("[bold green]📋 RELATÓRIO FINAL[/bold green]"))
    
    final_table = Table(title="📊 Estatísticas de Atualização")
    final_table.add_column("Métrica", style="cyan")
    final_table.add_column("Quantidade", style="white")
    final_table.add_column("Percentual", style="yellow")
    
    final_table.add_row("Contratos processados", str(total_contracts), "100%")
    final_table.add_row("Atualizações bem-sucedidas", str(total_stats['success']), f"{(total_stats['success']/total_contracts)*100:.1f}%")
    final_table.add_row("Erros da API", str(total_stats['api_errors']), f"{(total_stats['api_errors']/total_contracts)*100:.1f}%")
    final_table.add_row("Erros do banco", str(total_stats['db_errors']), f"{(total_stats['db_errors']/total_contracts)*100:.1f}%")
    final_table.add_row("Outras falhas", str(total_stats['failed']), f"{(total_stats['failed']/total_contracts)*100:.1f}%")
    
    console.print(final_table)
    
    success_rate = (total_stats['success'] / total_contracts) * 100
    
    if success_rate >= 80:
        console.print(f"[bold green]✅ Atualização concluída com sucesso ({success_rate:.1f}%)[/bold green]")
    else:
        console.print(f"[bold yellow]⚠️ Atualização concluída com taxa de sucesso baixa ({success_rate:.1f}%)[/bold yellow]")
    
    log_message("Atualização de campos faltantes concluída", "success")

if __name__ == "__main__":
    try:
        import os
        main()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]⚠️ Operação interrompida pelo usuário[/bold yellow]")
    except Exception as e:
        console.print(f"\n[bold red]❌ Erro: {e}[/bold red]")
        import traceback
        traceback.print_exc()
