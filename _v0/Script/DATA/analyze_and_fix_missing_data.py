#!/usr/bin/env python3
"""
Script para verificar e corrigir dados faltantes na DB local
baseado nos contratos do Supabase

Funcionalidades:
1. Analisa quais contratos do Supabase estão com dados incompletos na DB local
2. Gera relatório detalhado dos campos faltantes
3. Processa apenas os contratos que realmente precisam de dados
4. Sistema de retry para erros
5. Logs detalhados em arquivo
"""

import requests
import sqlite3
import json
import time
import re
import threading
import os
import psycopg2
import csv
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.table import Table
from dotenv import load_dotenv

console = Console()

# Carregar configurações
script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(script_dir, "supabase_v0.env"))

# Configurações
DB_PATH = r"C:\Users\Haroldo Duraes\Desktop\GOvGO\v0\#DATA\PNCP\DB\pncp_v2.db"
MAX_WORKERS = 25  # Mais workers
BATCH_WORKERS = 15  # Mais lotes paralelos
TIMEOUT = 30
BATCH_SIZE = 500
MAX_RETRIES = 3  # Tentativas para cada contrato

# Arquivos de log
ERROR_LOG_FILE = os.path.join(script_dir, "update_errors.csv")
SUCCESS_LOG_FILE = os.path.join(script_dir, "update_success.csv")
MISSING_DATA_REPORT = os.path.join(script_dir, "missing_data_report.csv")

# Configurações Supabase
SUPABASE_CONFIG = {
    'host': os.getenv('host'),
    'port': os.getenv('port'),
    'user': os.getenv('user'),
    'password': os.getenv('password'),
    'dbname': os.getenv('dbname')
}

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

def log_error_to_file(numero_controle, error_type, error_message, retry_count=0):
    """Salva erros em arquivo CSV"""
    try:
        with log_lock:
            file_exists = os.path.exists(ERROR_LOG_FILE)
            with open(ERROR_LOG_FILE, 'a', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                if not file_exists:
                    writer.writerow(['timestamp', 'numero_controle', 'error_type', 'error_message', 'retry_count'])
                writer.writerow([datetime.now().isoformat(), numero_controle, error_type, error_message, retry_count])
    except Exception as e:
        log_message(f"Erro ao salvar log: {e}", "error")

def log_success_to_file(numero_controle, fields_updated):
    """Salva sucessos em arquivo CSV"""
    try:
        with log_lock:
            file_exists = os.path.exists(SUCCESS_LOG_FILE)
            with open(SUCCESS_LOG_FILE, 'a', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile)
                if not file_exists:
                    writer.writerow(['timestamp', 'numero_controle', 'fields_updated'])
                writer.writerow([datetime.now().isoformat(), numero_controle, fields_updated])
    except Exception as e:
        log_message(f"Erro ao salvar log de sucesso: {e}", "error")

def analyze_missing_data():
    """Analisa quais dados estão faltando na DB local comparado com Supabase"""
    try:
        # Conectar ao Supabase
        supabase_conn = psycopg2.connect(
            host=SUPABASE_CONFIG['host'],
            port=SUPABASE_CONFIG['port'],
            user=SUPABASE_CONFIG['user'],
            password=SUPABASE_CONFIG['password'],
            database=SUPABASE_CONFIG['dbname']
        )
        
        supabase_cursor = supabase_conn.cursor()
        
        # Buscar todos os numeroControlePNCP do Supabase
        supabase_cursor.execute("""
            SELECT DISTINCT numerocontrolepncp 
            FROM contratacoes 
            WHERE numerocontrolepncp IS NOT NULL
        """)
        
        supabase_contracts = [row[0] for row in supabase_cursor.fetchall()]
        supabase_conn.close()
        
        log_message(f"Encontrados {len(supabase_contracts)} contratos no Supabase", "info")
        
        # Conectar à DB local
        local_conn = sqlite3.connect(DB_PATH)
        local_cursor = local_conn.cursor()
        
        # Verificar quais contratos do Supabase estão na DB local e com quais campos faltantes
        placeholders = ','.join(['?' for _ in supabase_contracts])
        
        query = f"""
            SELECT 
                numeroControlePNCP,
                ID_CONTRATACAO,
                CASE WHEN informacaoComplementar IS NULL THEN 1 ELSE 0 END as missing_informacaoComplementar,
                CASE WHEN modalidadeNome IS NULL THEN 1 ELSE 0 END as missing_modalidadeNome,
                CASE WHEN situacaoCompraNome IS NULL THEN 1 ELSE 0 END as missing_situacaoCompraNome,
                CASE WHEN amparoLegal_nome IS NULL THEN 1 ELSE 0 END as missing_amparoLegal_nome,
                CASE WHEN linkSistemaOrigem IS NULL THEN 1 ELSE 0 END as missing_linkSistemaOrigem,
                CASE WHEN linkProcessoEletronico IS NULL THEN 1 ELSE 0 END as missing_linkProcessoEletronico,
                CASE WHEN usuarioNome IS NULL THEN 1 ELSE 0 END as missing_usuarioNome,
                CASE WHEN modoDisputaNome IS NULL THEN 1 ELSE 0 END as missing_modoDisputaNome,
                CASE WHEN tipoInstrumentoConvocatorioNome IS NULL THEN 1 ELSE 0 END as missing_tipoInstrumentoConvocatorioNome,
                CASE WHEN orgaoEntidade_razaosocial IS NULL THEN 1 ELSE 0 END as missing_orgaoEntidade_razaosocial,
                CASE WHEN unidadeOrgao_ufNome IS NULL THEN 1 ELSE 0 END as missing_unidadeOrgao_ufNome,
                CASE WHEN fontesOrcamentarias IS NULL THEN 1 ELSE 0 END as missing_fontesOrcamentarias,
                CASE WHEN existeResultado IS NULL THEN 1 ELSE 0 END as missing_existeResultado,
                CASE WHEN orcamentoSigilosoCodigo IS NULL THEN 1 ELSE 0 END as missing_orcamentoSigilosoCodigo
            FROM contratacao 
            WHERE numeroControlePNCP IN ({placeholders})
        """
        
        local_cursor.execute(query, supabase_contracts)
        results = local_cursor.fetchall()
        
        # Analisar resultados
        contracts_needing_update = []
        missing_stats = {}
        
        for row in results:
            numero_controle = row[0]
            contract_id = row[1]
            missing_fields = []
            
            # Verificar quais campos estão faltando
            field_names = [
                'informacaoComplementar', 'modalidadeNome', 'situacaoCompraNome', 'amparoLegal_nome',
                'linkSistemaOrigem', 'linkProcessoEletronico', 'usuarioNome', 'modoDisputaNome',
                'tipoInstrumentoConvocatorioNome', 'orgaoEntidade_razaosocial', 'unidadeOrgao_ufNome',
                'fontesOrcamentarias', 'existeResultado', 'orcamentoSigilosoCodigo'
            ]
            
            for i, field in enumerate(field_names):
                if row[i + 2] == 1:  # Campo faltante
                    missing_fields.append(field)
                    missing_stats[field] = missing_stats.get(field, 0) + 1
            
            if missing_fields:
                contracts_needing_update.append({
                    'numero_controle': numero_controle,
                    'contract_id': contract_id,
                    'missing_fields': missing_fields,
                    'missing_count': len(missing_fields)
                })
        
        local_conn.close()
        
        # Gerar relatório
        with open(MISSING_DATA_REPORT, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['numero_controle', 'contract_id', 'missing_fields_count', 'missing_fields'])
            
            for contract in contracts_needing_update:
                writer.writerow([
                    contract['numero_controle'],
                    contract['contract_id'],
                    contract['missing_count'],
                    ';'.join(contract['missing_fields'])
                ])
        
        # Criar tabela de estatísticas
        stats_table = Table(title="📊 Análise de Dados Faltantes")
        stats_table.add_column("Campo", style="cyan")
        stats_table.add_column("Contratos Faltantes", style="white")
        stats_table.add_column("Percentual", style="yellow")
        
        total_contracts = len(results)
        for field, count in sorted(missing_stats.items(), key=lambda x: x[1], reverse=True):
            percentage = (count / total_contracts) * 100
            stats_table.add_row(field, f"{count:,}", f"{percentage:.1f}%")
        
        console.print(stats_table)
        
        log_message(f"Relatório salvo em: {MISSING_DATA_REPORT}", "info")
        log_message(f"Contratos que precisam atualização: {len(contracts_needing_update)}", "info")
        log_message(f"Total de contratos analisados: {total_contracts}", "info")
        
        return [(c['numero_controle'], c['contract_id']) for c in contracts_needing_update]
        
    except Exception as e:
        log_message(f"Erro na análise de dados faltantes: {e}", "error")
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

def fetch_contract_details_with_retry(numero_controle, max_retries=MAX_RETRIES):
    """Busca detalhes do contrato com sistema de retry"""
    for attempt in range(max_retries):
        try:
            cnpj, ano, sequencial = parse_numero_controle(numero_controle)
            
            if not cnpj or not ano or not sequencial:
                error_msg = 'Formato inválido'
                log_error_to_file(numero_controle, 'format_error', error_msg, attempt + 1)
                return {'error': error_msg, 'numero_controle': numero_controle}
                
            url = f"https://pncp.gov.br/api/consulta/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}"
            response = requests.get(url, timeout=TIMEOUT)
            
            if response.status_code == 200:
                return response.json()
            elif response.status_code == 404:
                error_msg = 'Contrato não encontrado'
                log_error_to_file(numero_controle, 'not_found', error_msg, attempt + 1)
                return {'error': error_msg, 'numero_controle': numero_controle}
            elif response.status_code in [500, 502, 503] and attempt < max_retries - 1:
                # Erros do servidor - tentar novamente
                time.sleep(2 ** attempt)  # Backoff exponencial
                continue
            else:
                error_msg = f'HTTP {response.status_code}'
                log_error_to_file(numero_controle, 'http_error', error_msg, attempt + 1)
                return {'error': error_msg, 'numero_controle': numero_controle}
                
        except requests.exceptions.Timeout:
            if attempt < max_retries - 1:
                time.sleep(1)
                continue
            error_msg = 'Timeout'
            log_error_to_file(numero_controle, 'timeout', error_msg, attempt + 1)
            return {'error': error_msg, 'numero_controle': numero_controle}
        except requests.exceptions.ConnectionError:
            if attempt < max_retries - 1:
                time.sleep(2)
                continue
            error_msg = 'Erro de conexão'
            log_error_to_file(numero_controle, 'connection_error', error_msg, attempt + 1)
            return {'error': error_msg, 'numero_controle': numero_controle}
        except Exception as e:
            error_msg = f'Erro inesperado: {str(e)}'
            log_error_to_file(numero_controle, 'unexpected_error', error_msg, attempt + 1)
            return {'error': error_msg, 'numero_controle': numero_controle}
    
    return {'error': 'Max retries exceeded', 'numero_controle': numero_controle}

def extract_extra_fields(contract_data):
    """Extrai TODOS os campos para atualização completa na DB local"""
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
        log_message(f"Erro ao extrair campos: {e}", "error")
        return None

def update_contract_in_db(contract_id, extra_fields):
    """Atualiza um contrato na DB local com os campos extras"""
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

def process_contracts_batch(contracts_batch, progress, batch_task_id):
    """Processa um lote de contratos com workers paralelos e retry"""
    results = {
        'success': 0,
        'api_errors': 0,
        'db_errors': 0,
        'not_found': 0,
        'timeout_errors': 0,
        'format_errors': 0,
        'retry_exceeded': 0
    }
    
    contracts_data = []
    
    # Buscar dados da API com workers paralelos
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_contract = {
            executor.submit(fetch_contract_details_with_retry, numero_controle): (numero_controle, contract_id)
            for numero_controle, contract_id in contracts_batch
        }
        
        for future in as_completed(future_to_contract):
            numero_controle, contract_id = future_to_contract[future]
            
            try:
                contract_data = future.result()
                
                if isinstance(contract_data, dict) and 'error' in contract_data:
                    error_msg = contract_data['error']
                    if 'não encontrado' in error_msg:
                        results['not_found'] += 1
                    elif 'Timeout' in error_msg:
                        results['timeout_errors'] += 1
                    elif 'Formato inválido' in error_msg:
                        results['format_errors'] += 1
                    elif 'Max retries' in error_msg:
                        results['retry_exceeded'] += 1
                    else:
                        results['api_errors'] += 1
                elif contract_data:
                    extra_fields = extract_extra_fields(contract_data)
                    if extra_fields:
                        contracts_data.append((contract_id, extra_fields, numero_controle))
                else:
                    results['api_errors'] += 1
                    
            except Exception as e:
                results['api_errors'] += 1
            
            progress.update(batch_task_id, advance=1)
    
    # Atualizar DB local
    for contract_id, extra_fields, numero_controle in contracts_data:
        if update_contract_in_db(contract_id, extra_fields):
            results['success'] += 1
            log_success_to_file(numero_controle, len(extra_fields))
        else:
            results['db_errors'] += 1
    
    return results

def main():
    """Função principal"""
    console.print(Panel("[bold green]🔍 ANÁLISE E CORREÇÃO DE DADOS FALTANTES[/bold green]"))
    log_message("Iniciando análise e correção de dados faltantes", "info")
    
    # Verificar se as DBs existem
    if not os.path.exists(DB_PATH):
        console.print(f"[bold red]❌ DB local não encontrada: {DB_PATH}[/bold red]")
        return
    
    # Etapa 1: Analisar dados faltantes
    console.print(Panel("[bold cyan]📊 ETAPA 1: ANÁLISE DE DADOS FALTANTES[/bold cyan]"))
    contracts = analyze_missing_data()
    
    if not contracts:
        console.print("[bold green]✅ Todos os contratos do Supabase já estão completos na DB local[/bold green]")
        return
    
    # Etapa 2: Processar contratos com dados faltantes
    console.print(Panel("[bold cyan]🔄 ETAPA 2: PROCESSAMENTO COM RETRY[/bold cyan]"))
    
    total_contracts = len(contracts)
    batches = [contracts[i:i + BATCH_SIZE] for i in range(0, total_contracts, BATCH_SIZE)]
    
    # Configuração
    config_table = Table(title="🔧 Configuração do Processamento")
    config_table.add_column("Parâmetro", style="cyan")
    config_table.add_column("Valor", style="white")
    
    config_table.add_row("Contratos com dados faltantes", f"{total_contracts:,}")
    config_table.add_row("Número de lotes", f"{len(batches):,}")
    config_table.add_row("Tamanho do lote", f"{BATCH_SIZE:,}")
    config_table.add_row("Workers por lote", f"{MAX_WORKERS}")
    config_table.add_row("Lotes paralelos", f"{BATCH_WORKERS}")
    config_table.add_row("Total workers simultâneos", f"{BATCH_WORKERS * MAX_WORKERS}")
    config_table.add_row("Max retries por contrato", f"{MAX_RETRIES}")
    config_table.add_row("Log de erros", ERROR_LOG_FILE)
    config_table.add_row("Log de sucessos", SUCCESS_LOG_FILE)
    
    console.print(config_table)
    
    # Limpar logs anteriores
    for log_file in [ERROR_LOG_FILE, SUCCESS_LOG_FILE]:
        if os.path.exists(log_file):
            os.remove(log_file)
    
    log_message(f"Processando {total_contracts:,} contratos em {len(batches):,} lotes", "info")
    
    # Estatísticas globais
    global_stats = {
        'total_processed': 0,
        'total_success': 0,
        'total_api_errors': 0,
        'total_db_errors': 0,
        'total_not_found': 0,
        'total_timeout_errors': 0,
        'total_format_errors': 0,
        'total_retry_exceeded': 0,
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
        main_task = progress.add_task(f"[bold green]📊 Processando {len(batches):,} lotes", total=len(batches))
        
        # Criar progress bars para todos os lotes
        batch_tasks = {}
        for i, batch in enumerate(batches, 1):
            batch_task_id = progress.add_task(
                f"[bold yellow]  🔄 Lote {i:02d} ({len(batch)} contratos)", 
                total=len(batch)
            )
            batch_tasks[i] = batch_task_id
        
        log_message(f"Iniciando processamento paralelo com retry", "info")
        
        # Processar lotes em paralelo
        with ThreadPoolExecutor(max_workers=BATCH_WORKERS) as batch_executor:
            future_to_batch = {
                batch_executor.submit(process_contracts_batch, batch, progress, batch_tasks[i]): (i, batch)
                for i, batch in enumerate(batches, 1)
            }
            
            for future in as_completed(future_to_batch):
                batch_id, batch = future_to_batch[future]
                
                try:
                    batch_results = future.result()
                    
                    # Atualizar estatísticas globais
                    global_stats['total_processed'] += len(batch)
                    global_stats['total_success'] += batch_results['success']
                    global_stats['total_api_errors'] += batch_results['api_errors']
                    global_stats['total_db_errors'] += batch_results['db_errors']
                    global_stats['total_not_found'] += batch_results['not_found']
                    global_stats['total_timeout_errors'] += batch_results['timeout_errors']
                    global_stats['total_format_errors'] += batch_results['format_errors']
                    global_stats['total_retry_exceeded'] += batch_results['retry_exceeded']
                    
                    # Atualizar progress bar do lote
                    progress.update(batch_tasks[batch_id], completed=len(batch),
                        description=f"[bold green]  ✅ Lote {batch_id:02d} ✓ {batch_results['success']} sucessos")
                    
                    # Log detalhado
                    log_message(
                        f"Lote {batch_id}: {batch_results['success']} sucessos, "
                        f"{batch_results['api_errors']} erros API, "
                        f"{batch_results['not_found']} não encontrados, "
                        f"{batch_results['retry_exceeded']} max retries",
                        "success"
                    )
                    
                except Exception as e:
                    log_message(f"Erro no lote {batch_id}: {e}", "error")
                    progress.update(batch_tasks[batch_id], completed=len(batch),
                        description=f"[bold red]  ❌ Lote {batch_id:02d} - ERRO")
                
                progress.update(main_task, advance=1)
    
    # Tempo total
    total_time = time.time() - global_stats['start_time']
    
    # Relatório final
    console.print(Panel("[bold green]📋 RELATÓRIO FINAL DETALHADO[/bold green]"))
    
    final_table = Table(title="📊 Estatísticas Finais")
    final_table.add_column("Métrica", style="cyan")
    final_table.add_column("Quantidade", style="white")
    final_table.add_column("Percentual", style="yellow")
    
    final_table.add_row("Contratos processados", f"{global_stats['total_processed']:,}", "100%")
    final_table.add_row("Atualizações bem-sucedidas", f"{global_stats['total_success']:,}", 
                       f"{(global_stats['total_success']/global_stats['total_processed'])*100:.1f}%")
    final_table.add_row("Contratos não encontrados", f"{global_stats['total_not_found']:,}", 
                       f"{(global_stats['total_not_found']/global_stats['total_processed'])*100:.1f}%")
    final_table.add_row("Timeouts", f"{global_stats['total_timeout_errors']:,}", 
                       f"{(global_stats['total_timeout_errors']/global_stats['total_processed'])*100:.1f}%")
    final_table.add_row("Formato inválido", f"{global_stats['total_format_errors']:,}", 
                       f"{(global_stats['total_format_errors']/global_stats['total_processed'])*100:.1f}%")
    final_table.add_row("Max retries excedido", f"{global_stats['total_retry_exceeded']:,}", 
                       f"{(global_stats['total_retry_exceeded']/global_stats['total_processed'])*100:.1f}%")
    final_table.add_row("Outros erros API", f"{global_stats['total_api_errors']:,}", 
                       f"{(global_stats['total_api_errors']/global_stats['total_processed'])*100:.1f}%")
    final_table.add_row("Erros do banco local", f"{global_stats['total_db_errors']:,}", 
                       f"{(global_stats['total_db_errors']/global_stats['total_processed'])*100:.1f}%")
    
    console.print(final_table)
    
    # Performance
    performance_table = Table(title="⚡ Performance")
    performance_table.add_column("Métrica", style="cyan")
    performance_table.add_column("Valor", style="white")
    
    performance_table.add_row("Tempo total", f"{total_time:.1f}s")
    performance_table.add_row("Contratos/segundo", f"{global_stats['total_processed']/total_time:.1f}")
    performance_table.add_row("Workers simultâneos", f"{BATCH_WORKERS * MAX_WORKERS}")
    performance_table.add_row("Retries utilizados", f"{MAX_RETRIES}")
    
    console.print(performance_table)
    
    # Arquivos gerados
    files_table = Table(title="📄 Arquivos Gerados")
    files_table.add_column("Arquivo", style="cyan")
    files_table.add_column("Descrição", style="white")
    
    files_table.add_row(MISSING_DATA_REPORT, "Relatório de dados faltantes")
    files_table.add_row(ERROR_LOG_FILE, "Log detalhado de erros")
    files_table.add_row(SUCCESS_LOG_FILE, "Log de sucessos")
    
    console.print(files_table)
    
    success_rate = (global_stats['total_success'] / global_stats['total_processed']) * 100
    
    if success_rate >= 80:
        console.print(f"[bold green]✅ Correção de dados concluída com sucesso ({success_rate:.1f}%)[/bold green]")
    else:
        console.print(f"[bold yellow]⚠️ Correção concluída com taxa de sucesso baixa ({success_rate:.1f}%)[/bold yellow]")
    
    log_message("Análise e correção de dados faltantes concluída", "success")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]⚠️ Operação interrompida pelo usuário[/bold yellow]")
    except Exception as e:
        console.print(f"\n[bold red]❌ Erro: {e}[/bold red]")
        import traceback
        traceback.print_exc()
