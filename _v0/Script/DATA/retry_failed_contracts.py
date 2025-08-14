#!/usr/bin/env python3
"""
Script para reprocessar erros do update_errors.csv
Foca especificamente nos contratos que deram erro, com retry mais agressivo
"""

import requests
import sqlite3
import json
import time
import re
import threading
import os
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.table import Table

console = Console()

# Configurações
script_dir = os.path.dirname(os.path.abspath(__file__))
DB_PATH = r"C:\Users\Haroldo Duraes\Desktop\GOvGO\v0\#DATA\PNCP\DB\pncp_v2.db"
MAX_WORKERS = 30  # Mais workers para retry
TIMEOUT = 45  # Timeout maior
BATCH_SIZE = 200  # Lotes menores para melhor controle
MAX_RETRIES = 5  # Mais tentativas
RETRY_DELAY = [1, 2, 4, 8, 16]  # Backoff exponencial

# Arquivos
ERROR_LOG_FILE = os.path.join(script_dir, "update_errors.csv")
RETRY_SUCCESS_LOG = os.path.join(script_dir, "retry_success.csv")
RETRY_FAILED_LOG = os.path.join(script_dir, "retry_failed.csv")

# Lock para operações thread-safe
db_lock = threading.Lock()
log_lock = threading.Lock()

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

def log_retry_result(numero_controle, status, error_type=None, fields_updated=None):
    """Salva resultado do retry"""
    try:
        with log_lock:
            if status == 'success':
                file_exists = os.path.exists(RETRY_SUCCESS_LOG)
                with open(RETRY_SUCCESS_LOG, 'a', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    if not file_exists:
                        writer.writerow(['timestamp', 'numero_controle', 'fields_updated'])
                    writer.writerow([datetime.now().isoformat(), numero_controle, fields_updated])
            else:
                file_exists = os.path.exists(RETRY_FAILED_LOG)
                with open(RETRY_FAILED_LOG, 'a', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    if not file_exists:
                        writer.writerow(['timestamp', 'numero_controle', 'error_type', 'final_error'])
                    writer.writerow([datetime.now().isoformat(), numero_controle, error_type, status])
    except Exception as e:
        log_message(f"Erro ao salvar log de retry: {e}", "error")

def read_error_log():
    """Lê o arquivo de erros e retorna lista de contratos para retry"""
    if not os.path.exists(ERROR_LOG_FILE):
        log_message("Arquivo de erros não encontrado", "error")
        return []
    
    try:
        contracts_to_retry = set()
        
        with open(ERROR_LOG_FILE, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                numero_controle = row['numero_controle']
                error_type = row['error_type']
                
                # Focar em erros que podem ser problemas de conexão/temporários
                if error_type in ['timeout', 'connection_error', 'http_error', 'unexpected_error']:
                    contracts_to_retry.add(numero_controle)
        
        log_message(f"Encontrados {len(contracts_to_retry)} contratos para retry", "info")
        return list(contracts_to_retry)
        
    except Exception as e:
        log_message(f"Erro ao ler arquivo de erros: {e}", "error")
        return []

def get_contract_ids_from_db(numero_controles):
    """Busca os IDs dos contratos na DB local"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Criar placeholders para a consulta IN
        placeholders = ','.join(['?' for _ in numero_controles])
        
        query = f"""
            SELECT numeroControlePNCP, ID_CONTRATACAO 
            FROM contratacao 
            WHERE numeroControlePNCP IN ({placeholders})
        """
        
        cursor.execute(query, numero_controles)
        results = cursor.fetchall()
        
        conn.close()
        
        log_message(f"Encontrados {len(results)} contratos na DB local para retry", "info")
        return results
        
    except Exception as e:
        log_message(f"Erro ao buscar IDs na DB: {e}", "error")
        return []

def parse_numero_controle(numero_controle):
    """Extrai CNPJ, ano e sequencial do numeroControlePNCP"""
    try:
        if not numero_controle or not isinstance(numero_controle, str):
            return None, None, None
            
        if not re.match(r'^\d+-\d+-\d+/\d+$', numero_controle):
            return None, None, None
            
        parts = numero_controle.split('-')
        if len(parts) != 3:
            return None, None, None
            
        cnpj = parts[0]
        seq_and_year = parts[2].split('/')
        
        if len(seq_and_year) != 2:
            return None, None, None
            
        sequencial_str = seq_and_year[0]
        ano = seq_and_year[1]
        sequencial = str(int(sequencial_str))
        
        return cnpj, ano, sequencial
        
    except Exception as e:
        return None, None, None

def fetch_contract_with_aggressive_retry(numero_controle):
    """Busca contrato com retry mais agressivo para casos de erro"""
    
    for attempt in range(MAX_RETRIES):
        try:
            cnpj, ano, sequencial = parse_numero_controle(numero_controle)
            
            if not cnpj or not ano or not sequencial:
                return {'error': 'Formato inválido', 'numero_controle': numero_controle}
                
            url = f"https://pncp.gov.br/api/consulta/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}"
            
            # Headers para melhorar a compatibilidade
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive'
            }
            
            # Fazer requisição com retry personalizado
            response = requests.get(url, timeout=TIMEOUT, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                return data
            elif response.status_code == 404:
                return {'error': 'Contrato não encontrado (404)', 'numero_controle': numero_controle}
            elif response.status_code in [429, 500, 502, 503, 504]:
                # Rate limit ou erro do servidor - tentar novamente com delay maior
                if attempt < MAX_RETRIES - 1:
                    delay = RETRY_DELAY[min(attempt, len(RETRY_DELAY) - 1)]
                    time.sleep(delay)
                    continue
                else:
                    return {'error': f'HTTP {response.status_code} após {MAX_RETRIES} tentativas', 'numero_controle': numero_controle}
            else:
                return {'error': f'HTTP {response.status_code}', 'numero_controle': numero_controle}
                
        except requests.exceptions.Timeout:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY[min(attempt, len(RETRY_DELAY) - 1)])
                continue
            return {'error': f'Timeout após {MAX_RETRIES} tentativas', 'numero_controle': numero_controle}
            
        except requests.exceptions.ConnectionError:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY[min(attempt, len(RETRY_DELAY) - 1)] * 2)  # Delay maior para conexão
                continue
            return {'error': f'Erro de conexão após {MAX_RETRIES} tentativas', 'numero_controle': numero_controle}
            
        except requests.exceptions.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                time.sleep(RETRY_DELAY[min(attempt, len(RETRY_DELAY) - 1)])
                continue
            return {'error': f'Erro de requisição: {str(e)}', 'numero_controle': numero_controle}
            
        except Exception as e:
            return {'error': f'Erro inesperado: {str(e)}', 'numero_controle': numero_controle}
    
    return {'error': f'Falhou após {MAX_RETRIES} tentativas', 'numero_controle': numero_controle}

def extract_extra_fields(contract_data):
    """Extrai todos os campos para atualização na DB local"""
    if not contract_data:
        return None
        
    try:
        extra_fields = {}
        
        # Campos básicos
        extra_fields['numeroControlePNCP'] = contract_data.get('numeroControlePNCP')
        extra_fields['modoDisputaId'] = contract_data.get('modoDisputaId')
        extra_fields['dataAberturaProposta'] = contract_data.get('dataAberturaProposta')
        extra_fields['dataEncerramentoProposta'] = contract_data.get('dataEncerramentoProposta')
        extra_fields['srp'] = contract_data.get('srp')
        extra_fields['anoCompra'] = contract_data.get('anoCompra')
        extra_fields['sequencialCompra'] = contract_data.get('sequencialCompra')
        extra_fields['processo'] = contract_data.get('processo')
        extra_fields['objetoCompra'] = contract_data.get('objetoCompra')
        extra_fields['valorTotalHomologado'] = contract_data.get('valorTotalHomologado')
        extra_fields['dataInclusao'] = contract_data.get('dataInclusao')
        extra_fields['dataPublicacaoPncp'] = contract_data.get('dataPublicacaoPncp')
        extra_fields['dataAtualizacao'] = contract_data.get('dataAtualizacao')
        extra_fields['numeroCompra'] = contract_data.get('numeroCompra')
        extra_fields['modalidadeId'] = contract_data.get('modalidadeId')
        extra_fields['dataAtualizacaoGlobal'] = contract_data.get('dataAtualizacaoGlobal')
        extra_fields['tipoInstrumentoConvocatorioCodigo'] = contract_data.get('tipoInstrumentoConvocatorioCodigo')
        extra_fields['valorTotalEstimado'] = contract_data.get('valorTotalEstimado')
        extra_fields['situacaoCompraId'] = contract_data.get('situacaoCompraId')
        
        # Campos novos
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
            extra_fields['amparoLegal_codigo'] = amparo_legal.get('codigo')
            extra_fields['amparoLegal_nome'] = amparo_legal.get('nome')
            extra_fields['amparoLegal_descricao'] = amparo_legal.get('descricao')
        
        # Órgão entidade
        orgao_entidade = contract_data.get('orgaoEntidade', {})
        if orgao_entidade:
            extra_fields['orgaoEntidade_cnpj'] = orgao_entidade.get('cnpj')
            extra_fields['orgaoEntidade_razaosocial'] = orgao_entidade.get('razaoSocial')
            extra_fields['orgaoEntidade_poderId'] = orgao_entidade.get('poderId')
            extra_fields['orgaoEntidade_esferaId'] = orgao_entidade.get('esferaId')
        
        # Unidade órgão
        unidade_orgao = contract_data.get('unidadeOrgao', {})
        if unidade_orgao:
            extra_fields['unidadeOrgao_ufNome'] = unidade_orgao.get('ufNome')
            extra_fields['unidadeOrgao_ufSigla'] = unidade_orgao.get('ufSigla')
            extra_fields['unidadeOrgao_municipioNome'] = unidade_orgao.get('municipioNome')
            extra_fields['unidadeOrgao_codigoUnidade'] = unidade_orgao.get('codigoUnidade')
            extra_fields['unidadeOrgao_nomeUnidade'] = unidade_orgao.get('nomeUnidade')
            extra_fields['unidadeOrgao_codigoIbge'] = unidade_orgao.get('codigoIbge')
        
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
        
        # Fontes orçamentárias
        fontes_orcamentarias = contract_data.get('fontesOrcamentarias', [])
        if fontes_orcamentarias:
            extra_fields['fontesOrcamentarias'] = json.dumps(fontes_orcamentarias, ensure_ascii=False)
        
        return extra_fields
        
    except Exception as e:
        return None

def update_contract_in_db(contract_id, extra_fields):
    """Atualiza um contrato na DB local"""
    try:
        with db_lock:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
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

def process_retry_batch(contracts_batch, progress, batch_task_id):
    """Processa um lote de contratos com retry agressivo"""
    results = {
        'success': 0,
        'not_found': 0,
        'connection_errors': 0,
        'timeout_errors': 0,
        'http_errors': 0,
        'format_errors': 0,
        'other_errors': 0,
        'db_errors': 0
    }
    
    contracts_data = []
    
    # Buscar dados da API com retry agressivo
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_contract = {
            executor.submit(fetch_contract_with_aggressive_retry, numero_controle): (numero_controle, contract_id)
            for numero_controle, contract_id in contracts_batch
        }
        
        for future in as_completed(future_to_contract):
            numero_controle, contract_id = future_to_contract[future]
            
            try:
                contract_data = future.result()
                
                if isinstance(contract_data, dict) and 'error' in contract_data:
                    error_msg = contract_data['error']
                    
                    if 'não encontrado' in error_msg or '404' in error_msg:
                        results['not_found'] += 1
                        log_retry_result(numero_controle, 'not_found', 'not_found')
                    elif 'Timeout' in error_msg:
                        results['timeout_errors'] += 1
                        log_retry_result(numero_controle, 'timeout_error', 'timeout')
                    elif 'conexão' in error_msg:
                        results['connection_errors'] += 1
                        log_retry_result(numero_controle, 'connection_error', 'connection')
                    elif 'HTTP' in error_msg:
                        results['http_errors'] += 1
                        log_retry_result(numero_controle, 'http_error', 'http')
                    elif 'Formato inválido' in error_msg:
                        results['format_errors'] += 1
                        log_retry_result(numero_controle, 'format_error', 'format')
                    else:
                        results['other_errors'] += 1
                        log_retry_result(numero_controle, 'other_error', 'other')
                        
                elif contract_data:
                    extra_fields = extract_extra_fields(contract_data)
                    if extra_fields:
                        contracts_data.append((contract_id, extra_fields, numero_controle))
                else:
                    results['other_errors'] += 1
                    log_retry_result(numero_controle, 'no_data_error', 'no_data')
                    
            except Exception as e:
                results['other_errors'] += 1
                log_retry_result(numero_controle, f'exception: {str(e)}', 'exception')
            
            progress.update(batch_task_id, advance=1)
    
    # Atualizar DB local
    for contract_id, extra_fields, numero_controle in contracts_data:
        if update_contract_in_db(contract_id, extra_fields):
            results['success'] += 1
            log_retry_result(numero_controle, 'success', fields_updated=len(extra_fields))
        else:
            results['db_errors'] += 1
            log_retry_result(numero_controle, 'db_error', 'db_update')
    
    return results

def main():
    """Função principal"""
    console.print(Panel("[bold green]🔄 RETRY DE ERROS - CONTRATOS FALTANTES[/bold green]"))
    log_message("Iniciando retry dos contratos que deram erro", "info")
    
    # Verificar se DB existe
    if not os.path.exists(DB_PATH):
        console.print(f"[bold red]❌ DB local não encontrada: {DB_PATH}[/bold red]")
        return
    
    # Ler contratos que deram erro
    error_contracts = read_error_log()
    
    if not error_contracts:
        console.print("[bold green]✅ Nenhum contrato para retry encontrado[/bold green]")
        return
    
    # Buscar IDs na DB local
    contracts_data = get_contract_ids_from_db(error_contracts)
    
    if not contracts_data:
        console.print("[bold red]❌ Nenhum contrato encontrado na DB local[/bold red]")
        return
    
    # Configuração
    total_contracts = len(contracts_data)
    batches = [contracts_data[i:i + BATCH_SIZE] for i in range(0, total_contracts, BATCH_SIZE)]
    
    config_table = Table(title="🔧 Configuração do Retry")
    config_table.add_column("Parâmetro", style="cyan")
    config_table.add_column("Valor", style="white")
    
    config_table.add_row("Contratos para retry", f"{total_contracts:,}")
    config_table.add_row("Número de lotes", f"{len(batches):,}")
    config_table.add_row("Tamanho do lote", f"{BATCH_SIZE:,}")
    config_table.add_row("Workers simultâneos", f"{MAX_WORKERS}")
    config_table.add_row("Max retries por contrato", f"{MAX_RETRIES}")
    config_table.add_row("Timeout", f"{TIMEOUT}s")
    config_table.add_row("Backoff delays", str(RETRY_DELAY))
    
    console.print(config_table)
    
    # Limpar logs de retry
    for log_file in [RETRY_SUCCESS_LOG, RETRY_FAILED_LOG]:
        if os.path.exists(log_file):
            os.remove(log_file)
    
    log_message(f"Processando {total_contracts:,} contratos em {len(batches):,} lotes", "info")
    
    # Estatísticas globais
    global_stats = {
        'total_processed': 0,
        'total_success': 0,
        'total_not_found': 0,
        'total_connection_errors': 0,
        'total_timeout_errors': 0,
        'total_http_errors': 0,
        'total_format_errors': 0,
        'total_other_errors': 0,
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
        main_task = progress.add_task(f"[bold green]🔄 Processando {len(batches):,} lotes de retry", total=len(batches))
        
        # Criar progress bars para todos os lotes
        batch_tasks = {}
        for i, batch in enumerate(batches, 1):
            batch_task_id = progress.add_task(
                f"[bold yellow]  🔄 Retry Lote {i:02d} ({len(batch)} contratos)", 
                total=len(batch)
            )
            batch_tasks[i] = batch_task_id
        
        log_message(f"Iniciando retry com {MAX_WORKERS} workers e {MAX_RETRIES} tentativas por contrato", "info")
        
        # Processar lotes sequencialmente para melhor controle
        for i, batch in enumerate(batches, 1):
            try:
                log_message(f"Processando lote {i}/{len(batches)} ({len(batch)} contratos)", "info")
                
                batch_results = process_retry_batch(batch, progress, batch_tasks[i])
                
                # Atualizar estatísticas globais
                global_stats['total_processed'] += len(batch)
                global_stats['total_success'] += batch_results['success']
                global_stats['total_not_found'] += batch_results['not_found']
                global_stats['total_connection_errors'] += batch_results['connection_errors']
                global_stats['total_timeout_errors'] += batch_results['timeout_errors']
                global_stats['total_http_errors'] += batch_results['http_errors']
                global_stats['total_format_errors'] += batch_results['format_errors']
                global_stats['total_other_errors'] += batch_results['other_errors']
                global_stats['total_db_errors'] += batch_results['db_errors']
                
                # Atualizar progress bar do lote
                progress.update(batch_tasks[i], completed=len(batch),
                    description=f"[bold green]  ✅ Retry Lote {i:02d} ✓ {batch_results['success']} sucessos")
                
                # Log detalhado
                log_message(
                    f"Retry Lote {i}: {batch_results['success']} sucessos, "
                    f"{batch_results['connection_errors']} conexão, "
                    f"{batch_results['timeout_errors']} timeout, "
                    f"{batch_results['not_found']} não encontrados",
                    "success"
                )
                
                # Pequeno delay entre lotes para não sobrecarregar
                time.sleep(1)
                
            except Exception as e:
                log_message(f"Erro no lote {i}: {e}", "error")
                progress.update(batch_tasks[i], completed=len(batch),
                    description=f"[bold red]  ❌ Retry Lote {i:02d} - ERRO")
            
            progress.update(main_task, advance=1)
    
    # Tempo total
    total_time = time.time() - global_stats['start_time']
    
    # Relatório final
    console.print(Panel("[bold green]📋 RELATÓRIO FINAL DO RETRY[/bold green]"))
    
    final_table = Table(title="📊 Estatísticas do Retry")
    final_table.add_column("Métrica", style="cyan")
    final_table.add_column("Quantidade", style="white")
    final_table.add_column("Percentual", style="yellow")
    
    final_table.add_row("Contratos reprocessados", f"{global_stats['total_processed']:,}", "100%")
    final_table.add_row("🎉 Sucessos no retry", f"{global_stats['total_success']:,}", 
                       f"{(global_stats['total_success']/global_stats['total_processed'])*100:.1f}%")
    final_table.add_row("❌ Não encontrados", f"{global_stats['total_not_found']:,}", 
                       f"{(global_stats['total_not_found']/global_stats['total_processed'])*100:.1f}%")
    final_table.add_row("🔌 Erros de conexão", f"{global_stats['total_connection_errors']:,}", 
                       f"{(global_stats['total_connection_errors']/global_stats['total_processed'])*100:.1f}%")
    final_table.add_row("⏱️ Timeouts", f"{global_stats['total_timeout_errors']:,}", 
                       f"{(global_stats['total_timeout_errors']/global_stats['total_processed'])*100:.1f}%")
    final_table.add_row("🌐 Erros HTTP", f"{global_stats['total_http_errors']:,}", 
                       f"{(global_stats['total_http_errors']/global_stats['total_processed'])*100:.1f}%")
    final_table.add_row("📝 Formato inválido", f"{global_stats['total_format_errors']:,}", 
                       f"{(global_stats['total_format_errors']/global_stats['total_processed'])*100:.1f}%")
    final_table.add_row("🗃️ Erros do banco", f"{global_stats['total_db_errors']:,}", 
                       f"{(global_stats['total_db_errors']/global_stats['total_processed'])*100:.1f}%")
    final_table.add_row("⚠️ Outros erros", f"{global_stats['total_other_errors']:,}", 
                       f"{(global_stats['total_other_errors']/global_stats['total_processed'])*100:.1f}%")
    
    console.print(final_table)
    
    # Performance
    performance_table = Table(title="⚡ Performance do Retry")
    performance_table.add_column("Métrica", style="cyan")
    performance_table.add_column("Valor", style="white")
    
    performance_table.add_row("Tempo total", f"{total_time:.1f}s")
    performance_table.add_row("Contratos/segundo", f"{global_stats['total_processed']/total_time:.1f}")
    performance_table.add_row("Workers utilizados", f"{MAX_WORKERS}")
    performance_table.add_row("Tentativas por contrato", f"{MAX_RETRIES}")
    
    console.print(performance_table)
    
    # Arquivos gerados
    files_table = Table(title="📄 Logs do Retry")
    files_table.add_column("Arquivo", style="cyan")
    files_table.add_column("Descrição", style="white")
    
    files_table.add_row(RETRY_SUCCESS_LOG, "Contratos que tiveram sucesso no retry")
    files_table.add_row(RETRY_FAILED_LOG, "Contratos que falharam no retry")
    
    console.print(files_table)
    
    success_rate = (global_stats['total_success'] / global_stats['total_processed']) * 100
    
    if success_rate >= 50:
        console.print(f"[bold green]✅ Retry concluído com boa taxa de sucesso ({success_rate:.1f}%)[/bold green]")
    else:
        console.print(f"[bold yellow]⚠️ Retry concluído com taxa de sucesso baixa ({success_rate:.1f}%)[/bold yellow]")
    
    log_message("Retry de contratos com erro concluído", "success")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]⚠️ Retry interrompido pelo usuário[/bold yellow]")
    except Exception as e:
        console.print(f"\n[bold red]❌ Erro no retry: {e}[/bold red]")
        import traceback
        traceback.print_exc()
