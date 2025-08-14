#!/usr/bin/env python3
"""
Script para atualizar campos faltantes na tabela contratacao do SQLite
Busca dados da API do PNCP usando a URL correta e atualiza apenas os campos extras

VERSÃO 2: Processamento paralelo de batches com workers
"""

import requests
import sqlite3
import json
import time
import re
import threading
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.table import Table

console = Console()

# Configurações
DB_PATH = r"C:\Users\Haroldo Duraes\Desktop\GOvGO\v0\#DATA\PNCP\DB\pncp_v2.db"
MAX_WORKERS = 20  # Workers por batch
BATCH_WORKERS = 4  # Número de batches processados simultaneamente
TIMEOUT = 30  # Timeout para requisições
BATCH_SIZE = 1000  # Tamanho do lote para processamento
TEST_LIMIT = 50000  # Limite para testes

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

def get_total_contracts():
    """Retorna o total de contratos na tabela"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM contratacao WHERE numeroControlePNCP IS NOT NULL")
        total = cursor.fetchone()[0]
        
        conn.close()
        return total
    except Exception as e:
        log_message(f"Erro ao contar contratos: {e}", "error")
        return 0

def get_contracts_to_update(limit=None):
    """Busca contratos que precisam ser atualizados"""
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
        return None, None, None

def fetch_contract_details(numero_controle):
    """Busca detalhes do contrato na API do PNCP"""
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
            return None
            
    except Exception as e:
        return None

def extract_extra_fields(contract_data):
    """Extrai apenas os campos extras que foram adicionados recentemente"""
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
        return None

def update_contracts_batch(contracts_data):
    """Atualiza um lote de contratos na base de dados"""
    try:
        with db_lock:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            updated_count = 0
            
            for contract_id, extra_fields in contracts_data:
                # Montar query UPDATE apenas com campos que têm valor
                set_clauses = []
                values = []
                
                for field, value in extra_fields.items():
                    if value is not None:
                        set_clauses.append(f"{field} = ?")
                        values.append(value)
                
                if set_clauses:
                    query = f"""
                        UPDATE contratacao 
                        SET {', '.join(set_clauses)}
                        WHERE ID_CONTRATACAO = ?
                    """
                    
                    values.append(contract_id)
                    cursor.execute(query, values)
                    updated_count += 1
            
            conn.commit()
            conn.close()
            
            return updated_count
            
    except Exception as e:
        log_message(f"Erro ao atualizar lote: {e}", "error")
        return 0

def process_single_batch(batch_contracts, batch_id):
    """Processa um único batch de contratos"""
    start_time = time.time()
    
    results = {
        'batch_id': batch_id,
        'total': len(batch_contracts),
        'success': 0,
        'api_errors': 0,
        'db_errors': 0,
        'time_taken': 0
    }
    
    # Armazenar dados em memória
    contracts_data = []
    
    # Fase 1: Buscar dados da API em paralelo
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_contract = {
            executor.submit(fetch_contract_details, numero_controle): (numero_controle, contract_id)
            for numero_controle, contract_id in batch_contracts
        }
        
        for future in as_completed(future_to_contract):
            numero_controle, contract_id = future_to_contract[future]
            
            try:
                contract_data = future.result()
                
                if contract_data:
                    extra_fields = extract_extra_fields(contract_data)
                    if extra_fields:
                        contracts_data.append((contract_id, extra_fields))
                else:
                    results['api_errors'] += 1
                    
            except Exception as e:
                results['api_errors'] += 1
    
    # Fase 2: Atualizar base de dados
    if contracts_data:
        updated_count = update_contracts_batch(contracts_data)
        results['success'] = updated_count
        results['db_errors'] = len(contracts_data) - updated_count
    
    results['time_taken'] = time.time() - start_time
    
    return results

def main():
    """Função principal"""
    console.print(Panel("[bold green]🔄 ATUALIZAÇÃO DE CAMPOS FALTANTES - API PNCP V2[/bold green]"))
    log_message("Iniciando atualização de campos faltantes V2", "info")
    
    # Verificar se o banco existe
    if not os.path.exists(DB_PATH):
        console.print(f"[bold red]❌ Banco de dados não encontrado: {DB_PATH}[/bold red]")
        return
    
    # Estatísticas iniciais
    total_contracts_db = get_total_contracts()
    log_message(f"Total de contratos na base: {total_contracts_db:,}", "info")
    
    # Buscar contratos para atualizar
    contracts = get_contracts_to_update(limit=TEST_LIMIT)
    
    if not contracts:
        console.print("[bold green]✅ Todos os contratos já estão atualizados[/bold green]")
        return
    
    # Dividir em batches
    total_contracts = len(contracts)
    batches = [contracts[i:i + BATCH_SIZE] for i in range(0, total_contracts, BATCH_SIZE)]
    
    # Criar tabela de resumo
    summary_table = Table(title="📊 Configuração do Processamento")
    summary_table.add_column("Parâmetro", style="cyan")
    summary_table.add_column("Valor", style="white")
    
    summary_table.add_row("Total na base", f"{total_contracts_db:,}")
    summary_table.add_row("Contratos a atualizar", f"{total_contracts:,}")
    summary_table.add_row("Número de batches", f"{len(batches):,}")
    summary_table.add_row("Tamanho do batch", f"{BATCH_SIZE:,}")
    summary_table.add_row("Workers por batch", f"{MAX_WORKERS}")
    summary_table.add_row("Batches paralelos", f"{BATCH_WORKERS}")
    
    console.print(summary_table)
    
    log_message(f"Processando {total_contracts:,} contratos em {len(batches):,} batches", "info")
    
    # Estatísticas globais
    global_stats = {
        'total_processed': 0,
        'total_success': 0,
        'total_api_errors': 0,
        'total_db_errors': 0,
        'start_time': time.time()
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
        main_task = progress.add_task(f"[bold green]🚀 Processando {len(batches):,} batches", total=len(batches))
        
        # Processar batches em paralelo
        batch_groups = [batches[i:i + BATCH_WORKERS] for i in range(0, len(batches), BATCH_WORKERS)]
        
        for group_idx, batch_group in enumerate(batch_groups, 1):
            log_message(f"Processando grupo {group_idx}/{len(batch_groups)} ({len(batch_group)} batches)", "info")
            
            # Processar grupo de batches em paralelo
            with ThreadPoolExecutor(max_workers=len(batch_group)) as executor:
                future_to_batch = {
                    executor.submit(process_single_batch, batch, batch_idx): batch_idx
                    for batch_idx, batch in enumerate(batch_group, 1)
                }
                
                for future in as_completed(future_to_batch):
                    batch_idx = future_to_batch[future]
                    
                    try:
                        batch_results = future.result()
                        
                        # Atualizar estatísticas globais
                        global_stats['total_processed'] += batch_results['total']
                        global_stats['total_success'] += batch_results['success']
                        global_stats['total_api_errors'] += batch_results['api_errors']
                        global_stats['total_db_errors'] += batch_results['db_errors']
                        
                        # Log do batch
                        log_message(
                            f"Batch {batch_results['batch_id']} concluído: "
                            f"{batch_results['success']}/{batch_results['total']} sucessos "
                            f"({batch_results['time_taken']:.1f}s)",
                            "success"
                        )
                        
                    except Exception as e:
                        log_message(f"Erro no batch {batch_idx}: {e}", "error")
                    
                    # Atualizar progresso
                    progress.update(main_task, advance=1)
    
    # Calcular tempo total
    total_time = time.time() - global_stats['start_time']
    
    # Relatório final
    console.print(Panel("[bold green]📋 RELATÓRIO FINAL[/bold green]"))
    
    final_table = Table(title="📊 Estatísticas Finais")
    final_table.add_column("Métrica", style="cyan")
    final_table.add_column("Quantidade", style="white")
    final_table.add_column("Percentual", style="yellow")
    
    final_table.add_row("Contratos processados", f"{global_stats['total_processed']:,}", "100%")
    final_table.add_row("Atualizações bem-sucedidas", f"{global_stats['total_success']:,}", 
                       f"{(global_stats['total_success']/global_stats['total_processed'])*100:.1f}%")
    final_table.add_row("Erros da API", f"{global_stats['total_api_errors']:,}", 
                       f"{(global_stats['total_api_errors']/global_stats['total_processed'])*100:.1f}%")
    final_table.add_row("Erros do banco", f"{global_stats['total_db_errors']:,}", 
                       f"{(global_stats['total_db_errors']/global_stats['total_processed'])*100:.1f}%")
    
    console.print(final_table)
    
    # Performance
    performance_table = Table(title="⚡ Performance")
    performance_table.add_column("Métrica", style="cyan")
    performance_table.add_column("Valor", style="white")
    
    performance_table.add_row("Tempo total", f"{total_time:.1f}s")
    performance_table.add_row("Contratos/segundo", f"{global_stats['total_processed']/total_time:.1f}")
    performance_table.add_row("Batches processados", f"{len(batches):,}")
    performance_table.add_row("Média/batch", f"{total_time/len(batches):.1f}s")
    
    console.print(performance_table)
    
    success_rate = (global_stats['total_success'] / global_stats['total_processed']) * 100
    
    if success_rate >= 80:
        console.print(f"[bold green]✅ Atualização V2 concluída com sucesso ({success_rate:.1f}%)[/bold green]")
    else:
        console.print(f"[bold yellow]⚠️ Atualização V2 concluída com taxa de sucesso baixa ({success_rate:.1f}%)[/bold yellow]")
    
    log_message("Atualização de campos faltantes V2 concluída", "success")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]⚠️ Operação interrompida pelo usuário[/bold yellow]")
    except Exception as e:
        console.print(f"\n[bold red]❌ Erro: {e}[/bold red]")
        import traceback
        traceback.print_exc()
