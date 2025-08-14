#!/usr/bin/env python3
"""
Script para atualizar campos faltantes na DB local SQLite
baseado nos contratos que estão no Supabase

Fluxo:
1. Consulta Supabase para pegar numeroControlePNCP
2. API paralela do PNCP com 10 workers
3. Atualização dos campos extras na DB local SQLite
"""

import requests
import sqlite3
import json
import time
import re
import threading
import os
import psycopg2
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
MAX_WORKERS = 20  # Workers para API PNCP por lote
BATCH_WORKERS = 10  # Lotes processados simultaneamente  
TIMEOUT = 30  # Timeout para requisições
BATCH_SIZE = 500  # Tamanho do lote reduzido para mais paralelismo

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

def get_contracts_from_supabase():
    """Busca numeroControlePNCP dos contratos no Supabase"""
    try:
        # Conectar ao Supabase
        conn = psycopg2.connect(
            host=SUPABASE_CONFIG['host'],
            port=SUPABASE_CONFIG['port'],
            user=SUPABASE_CONFIG['user'],
            password=SUPABASE_CONFIG['password'],
            database=SUPABASE_CONFIG['dbname']
        )
        
        cursor = conn.cursor()
        
        # Buscar todos os numeroControlePNCP do Supabase
        query = """
            SELECT DISTINCT numerocontrolepncp 
            FROM contratacoes 
            WHERE numerocontrolepncp IS NOT NULL
        """
        
        cursor.execute(query)
        contracts = [row[0] for row in cursor.fetchall()]
        
        conn.close()
        
        log_message(f"Encontrados {len(contracts)} contratos no Supabase", "info")
        return contracts
        
    except Exception as e:
        log_message(f"Erro ao buscar contratos do Supabase: {e}", "error")
        return []

def get_contracts_to_update_from_supabase():
    """Busca contratos do Supabase que precisam ser atualizados na DB local"""
    try:
        # Pegar contratos do Supabase
        supabase_contracts = get_contracts_from_supabase()
        
        if not supabase_contracts:
            return []
        
        # Conectar à DB local
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Criar placeholders para a consulta IN
        placeholders = ','.join(['?' for _ in supabase_contracts])
        
        # Buscar contratos que estão no Supabase mas precisam ser atualizados localmente
        query = f"""
            SELECT numeroControlePNCP, ID_CONTRATACAO 
            FROM contratacao 
            WHERE numeroControlePNCP IN ({placeholders})
            AND (
                informacaoComplementar IS NULL OR
                modalidadeNome IS NULL OR
                situacaoCompraNome IS NULL OR
                amparoLegal_nome IS NULL OR
                linkSistemaOrigem IS NULL OR
                linkProcessoEletronico IS NULL OR
                usuarioNome IS NULL OR
                modoDisputaNome IS NULL OR
                tipoInstrumentoConvocatorioNome IS NULL OR
                orgaoEntidade_razaosocial IS NULL OR
                unidadeOrgao_ufNome IS NULL OR
                fontesOrcamentarias IS NULL
            )
        """
        
        cursor.execute(query, supabase_contracts)
        contracts = cursor.fetchall()
        
        conn.close()
        
        log_message(f"Encontrados {len(contracts)} contratos para atualizar na DB local", "info")
        return contracts
        
    except Exception as e:
        log_message(f"Erro ao buscar contratos para atualizar: {e}", "error")
        return []

def parse_numero_controle(numero_controle):
    """
    Extrai CNPJ, ano e sequencial do numeroControlePNCP
    Formato: {cnpj}-1-{sequencialCompra}/{anocompra}
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
    """Busca detalhes completos do contrato na API do PNCP"""
    try:
        cnpj, ano, sequencial = parse_numero_controle(numero_controle)
        
        if not cnpj or not ano or not sequencial:
            return {'error': 'Formato inválido', 'numero_controle': numero_controle}
            
        # Montar URL da API
        url = f"https://pncp.gov.br/api/consulta/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}"
        
        # Fazer requisição
        response = requests.get(url, timeout=TIMEOUT)
        
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return {'error': 'Contrato não encontrado', 'numero_controle': numero_controle}
        elif response.status_code == 403:
            return {'error': 'Acesso negado', 'numero_controle': numero_controle}
        elif response.status_code == 500:
            return {'error': 'Erro interno do servidor', 'numero_controle': numero_controle}
        else:
            return {'error': f'HTTP {response.status_code}', 'numero_controle': numero_controle}
            
    except requests.exceptions.Timeout:
        return {'error': 'Timeout', 'numero_controle': numero_controle}
    except requests.exceptions.ConnectionError:
        return {'error': 'Erro de conexão', 'numero_controle': numero_controle}
    except Exception as e:
        return {'error': f'Erro inesperado: {str(e)}', 'numero_controle': numero_controle}

def extract_extra_fields(contract_data):
    """Extrai TODOS os campos para atualização completa na DB local"""
    if not contract_data:
        return None
        
    try:
        extra_fields = {}
        
        # CAMPOS BÁSICOS - todos os campos que podem estar vazios
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
        
        # CAMPOS NOVOS - campos extras adicionados
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
        
        # AMPARO LEGAL
        amparo_legal = contract_data.get('amparoLegal', {})
        if amparo_legal:
            extra_fields['amparoLegal_codigo'] = amparo_legal.get('codigo')
            extra_fields['amparoLegal_nome'] = amparo_legal.get('nome')
            extra_fields['amparoLegal_descricao'] = amparo_legal.get('descricao')
        
        # ÓRGÃO ENTIDADE
        orgao_entidade = contract_data.get('orgaoEntidade', {})
        if orgao_entidade:
            extra_fields['orgaoEntidade_cnpj'] = orgao_entidade.get('cnpj')
            extra_fields['orgaoEntidade_razaosocial'] = orgao_entidade.get('razaoSocial')
            extra_fields['orgaoEntidade_poderId'] = orgao_entidade.get('poderId')
            extra_fields['orgaoEntidade_esferaId'] = orgao_entidade.get('esferaId')
        
        # UNIDADE ÓRGÃO
        unidade_orgao = contract_data.get('unidadeOrgao', {})
        if unidade_orgao:
            extra_fields['unidadeOrgao_ufNome'] = unidade_orgao.get('ufNome')
            extra_fields['unidadeOrgao_ufSigla'] = unidade_orgao.get('ufSigla')
            extra_fields['unidadeOrgao_municipioNome'] = unidade_orgao.get('municipioNome')
            extra_fields['unidadeOrgao_codigoUnidade'] = unidade_orgao.get('codigoUnidade')
            extra_fields['unidadeOrgao_nomeUnidade'] = unidade_orgao.get('nomeUnidade')
            extra_fields['unidadeOrgao_codigoIbge'] = unidade_orgao.get('codigoIbge')
        
        # ÓRGÃO SUB-ROGADO
        orgao_sub_rogado = contract_data.get('orgaoSubRogado', {})
        if orgao_sub_rogado:
            extra_fields['orgaoSubRogado_cnpj'] = orgao_sub_rogado.get('cnpj')
            extra_fields['orgaoSubRogado_razaoSocial'] = orgao_sub_rogado.get('razaoSocial')
            extra_fields['orgaoSubRogado_poderId'] = orgao_sub_rogado.get('poderId')
            extra_fields['orgaoSubRogado_esferaId'] = orgao_sub_rogado.get('esferaId')
        
        # UNIDADE SUB-ROGADA
        unidade_sub_rogada = contract_data.get('unidadeSubRogada', {})
        if unidade_sub_rogada:
            extra_fields['unidadeSubRogada_ufNome'] = unidade_sub_rogada.get('ufNome')
            extra_fields['unidadeSubRogada_ufSigla'] = unidade_sub_rogada.get('ufSigla')
            extra_fields['unidadeSubRogada_municipioNome'] = unidade_sub_rogada.get('municipioNome')
            extra_fields['unidadeSubRogada_codigoUnidade'] = unidade_sub_rogada.get('codigoUnidade')
            extra_fields['unidadeSubRogada_nomeUnidade'] = unidade_sub_rogada.get('nomeUnidade')
            extra_fields['unidadeSubRogada_codigoIbge'] = unidade_sub_rogada.get('codigoIbge')
        
        # FONTES ORÇAMENTÁRIAS (JSON)
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

def process_contracts_batch(contracts_batch, progress, batch_task_id):
    """Processa um lote de contratos com workers paralelos"""
    results = {
        'success': 0,
        'api_errors': 0,
        'db_errors': 0,
        'no_data': 0,
        'format_errors': 0,
        'not_found': 0,
        'timeout_errors': 0,
        'connection_errors': 0
    }
    
    # Armazenar dados em memória
    contracts_data = []
    
    # Fase 1: Buscar dados da API com workers paralelos
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_contract = {
            executor.submit(fetch_contract_details, numero_controle): (numero_controle, contract_id)
            for numero_controle, contract_id in contracts_batch
        }
        
        for future in as_completed(future_to_contract):
            numero_controle, contract_id = future_to_contract[future]
            
            try:
                contract_data = future.result()
                
                if isinstance(contract_data, dict) and 'error' in contract_data:
                    # Classificar tipos de erro
                    error_msg = contract_data['error']
                    if 'Formato inválido' in error_msg:
                        results['format_errors'] += 1
                    elif 'não encontrado' in error_msg:
                        results['not_found'] += 1
                    elif 'Timeout' in error_msg:
                        results['timeout_errors'] += 1
                    elif 'conexão' in error_msg:
                        results['connection_errors'] += 1
                    else:
                        results['api_errors'] += 1
                elif contract_data:
                    extra_fields = extract_extra_fields(contract_data)
                    if extra_fields:
                        contracts_data.append((contract_id, extra_fields))
                    else:
                        results['no_data'] += 1
                else:
                    results['api_errors'] += 1
                    
            except Exception as e:
                results['api_errors'] += 1
            
            # Atualizar progress bar do lote
            progress.update(batch_task_id, advance=1)
    
    # Fase 2: Atualizar DB local
    for contract_id, extra_fields in contracts_data:
        if update_contract_in_db(contract_id, extra_fields):
            results['success'] += 1
        else:
            results['db_errors'] += 1
    
    return results

def main():
    """Função principal"""
    console.print(Panel("[bold green]🔄 ATUALIZAÇÃO DE CAMPOS BASEADA NO SUPABASE[/bold green]"))
    log_message("Iniciando atualização baseada nos contratos do Supabase", "info")
    
    # Verificar se as DBs existem
    if not os.path.exists(DB_PATH):
        console.print(f"[bold red]❌ DB local não encontrada: {DB_PATH}[/bold red]")
        return
    
    # Buscar contratos do Supabase que precisam ser atualizados
    contracts = get_contracts_to_update_from_supabase()
    
    if not contracts:
        console.print("[bold green]✅ Todos os contratos do Supabase já estão atualizados na DB local[/bold green]")
        return
    
    # Dividir em lotes
    total_contracts = len(contracts)
    batches = [contracts[i:i + BATCH_SIZE] for i in range(0, total_contracts, BATCH_SIZE)]
    
    # Tabela de configuração
    config_table = Table(title="🔧 Configuração do Processamento")
    config_table.add_column("Parâmetro", style="cyan")
    config_table.add_column("Valor", style="white")
    
    config_table.add_row("Contratos a processar", f"{total_contracts:,}")
    config_table.add_row("Número de lotes", f"{len(batches):,}")
    config_table.add_row("Tamanho do lote", f"{BATCH_SIZE:,}")
    config_table.add_row("Workers por lote", f"{MAX_WORKERS}")
    config_table.add_row("Lotes paralelos", f"{BATCH_WORKERS}")
    config_table.add_row("Total workers simultâneos", f"{BATCH_WORKERS * MAX_WORKERS}")
    config_table.add_row("Fonte", "Supabase")
    config_table.add_row("Destino", "SQLite Local")
    
    console.print(config_table)
    
    log_message(f"Processando {total_contracts:,} contratos em {len(batches):,} lotes", "info")
    
    # Estatísticas globais
    global_stats = {
        'total_processed': 0,
        'total_success': 0,
        'total_api_errors': 0,
        'total_db_errors': 0,
        'total_no_data': 0,
        'total_format_errors': 0,
        'total_not_found': 0,
        'total_timeout_errors': 0,
        'total_connection_errors': 0,
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
        
        log_message(f"Iniciando processamento paralelo de {len(batches)} lotes com {BATCH_WORKERS} lotes simultâneos", "info")
        
        # Processar todos os lotes em paralelo com ThreadPoolExecutor
        with ThreadPoolExecutor(max_workers=BATCH_WORKERS) as batch_executor:  # Usar BATCH_WORKERS
            # Submeter todos os lotes para processamento paralelo
            future_to_batch = {
                batch_executor.submit(process_contracts_batch, batch, progress, batch_tasks[i]): (i, batch)
                for i, batch in enumerate(batches, 1)
            }
            
            # Processar resultados conforme os lotes são concluídos
            for future in as_completed(future_to_batch):
                batch_id, batch = future_to_batch[future]
                
                try:
                    batch_results = future.result()
                    
                    # Atualizar estatísticas globais
                    global_stats['total_processed'] += len(batch)
                    global_stats['total_success'] += batch_results['success']
                    global_stats['total_api_errors'] += batch_results['api_errors']
                    global_stats['total_db_errors'] += batch_results['db_errors']
                    global_stats['total_no_data'] += batch_results['no_data']
                    global_stats['total_format_errors'] += batch_results['format_errors']
                    global_stats['total_not_found'] += batch_results['not_found']
                    global_stats['total_timeout_errors'] += batch_results['timeout_errors']
                    global_stats['total_connection_errors'] += batch_results['connection_errors']
                    
                    # Atualizar progress bar do lote para mostrar conclusão
                    progress.update(batch_tasks[batch_id], completed=len(batch),
                        description=f"[bold green]  ✅ Lote {batch_id:02d} ✓ {batch_results['success']} sucessos")
                    
                    # Log do lote com mais detalhes
                    log_message(
                        f"Lote {batch_id} concluído: {batch_results['success']} sucessos, "
                        f"{batch_results['api_errors']} erros API, "
                        f"{batch_results['db_errors']} erros DB, "
                        f"{batch_results['not_found']} não encontrados, "
                        f"{batch_results['timeout_errors']} timeouts",
                        "success"
                    )
                    
                except Exception as e:
                    log_message(f"Erro no lote {batch_id}: {e}", "error")
                    # Marcar o lote como com erro
                    progress.update(batch_tasks[batch_id], completed=len(batch),
                        description=f"[bold red]  ❌ Lote {batch_id:02d} - ERRO")
                
                # Atualizar progresso principal
                progress.update(main_task, advance=1)
    
    # Tempo total
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
    final_table.add_row("Erros do banco local", f"{global_stats['total_db_errors']:,}", 
                       f"{(global_stats['total_db_errors']/global_stats['total_processed'])*100:.1f}%")
    final_table.add_row("Contratos não encontrados", f"{global_stats['total_not_found']:,}", 
                       f"{(global_stats['total_not_found']/global_stats['total_processed'])*100:.1f}%")
    final_table.add_row("Timeouts", f"{global_stats['total_timeout_errors']:,}", 
                       f"{(global_stats['total_timeout_errors']/global_stats['total_processed'])*100:.1f}%")
    final_table.add_row("Erros de conexão", f"{global_stats['total_connection_errors']:,}", 
                       f"{(global_stats['total_connection_errors']/global_stats['total_processed'])*100:.1f}%")
    final_table.add_row("Formato inválido", f"{global_stats['total_format_errors']:,}", 
                       f"{(global_stats['total_format_errors']/global_stats['total_processed'])*100:.1f}%")
    final_table.add_row("Sem dados", f"{global_stats['total_no_data']:,}", 
                       f"{(global_stats['total_no_data']/global_stats['total_processed'])*100:.1f}%")
    
    console.print(final_table)
    
    # Performance
    performance_table = Table(title="⚡ Performance")
    performance_table.add_column("Métrica", style="cyan")
    performance_table.add_column("Valor", style="white")
    
    performance_table.add_row("Tempo total", f"{total_time:.1f}s")
    performance_table.add_row("Contratos/segundo", f"{global_stats['total_processed']/total_time:.1f}")
    performance_table.add_row("Workers simultâneos", f"{BATCH_WORKERS * MAX_WORKERS}")
    performance_table.add_row("Lotes paralelos", f"{BATCH_WORKERS}")
    performance_table.add_row("Workers por lote", f"{MAX_WORKERS}")
    
    console.print(performance_table)
    
    success_rate = (global_stats['total_success'] / global_stats['total_processed']) * 100
    
    if success_rate >= 80:
        console.print(f"[bold green]✅ Atualização baseada no Supabase concluída com sucesso ({success_rate:.1f}%)[/bold green]")
    else:
        console.print(f"[bold yellow]⚠️ Atualização concluída com taxa de sucesso baixa ({success_rate:.1f}%)[/bold yellow]")
    
    log_message("Atualização baseada no Supabase concluída", "success")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]⚠️ Operação interrompida pelo usuário[/bold yellow]")
    except Exception as e:
        console.print(f"\n[bold red]❌ Erro: {e}[/bold red]")
        import traceback
        traceback.print_exc()
