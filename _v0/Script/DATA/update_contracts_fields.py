#!/usr/bin/env python3
"""
Script para atualizar campos faltantes nos contratos existentes na base SQLite
Busca dados específicos de cada contrato na API do PNCP usando workers paralelos
"""

import requests
import sqlite3
import json
import time
import sys
import os
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.table import Table

console = Console()

# Configurações
DB_PATH = r"C:\Users\Haroldo Duraes\Desktop\GOvGO\v0\#DATA\PNCP\DB\pncp_v2.db"
BATCH_SIZE = 100  # Processar em lotes de 100
MAX_WORKERS = 15  # Mais workers para paralelização
API_BASE_URL = "https://pncp.gov.br/api/pncp/v1/orgaos"
TIMEOUT = 30  # Timeout para requisições
TEST_MODE = True  # Modo de teste - processar apenas uma amostra
TEST_LIMIT = 500  # Limite para teste

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

def get_contracts_to_update():
    """Busca contratos que precisam ser atualizados"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Buscar contratos que precisam atualização (campo informacaoComplementar é NULL)
        query = """
            SELECT 
                ID_CONTRATACAO,
                numeroControlePNCP,
                anoCompra,
                sequencialCompra,
                orgaoEntidade_cnpj
            FROM contratacao 
            WHERE numeroControlePNCP IS NOT NULL 
            AND informacaoComplementar IS NULL
        """
        
        if TEST_MODE:
            query += f" LIMIT {TEST_LIMIT}"
        
        cursor.execute(query)
        contracts = cursor.fetchall()
        
        log_message(f"Encontrados {len(contracts)} contratos para atualizar", "info")
        
        # Converter para lista de dicionários
        contracts_list = []
        for contract in contracts:
            contracts_list.append({
                'id_contratacao': contract[0],
                'numero_controle': contract[1],
                'ano_compra': contract[2],
                'sequencial_compra': contract[3],
                'cnpj': contract[4]
            })
        
        conn.close()
        return contracts_list
        
    except Exception as e:
        log_message(f"Erro ao buscar contratos: {e}", "error")
        return []

def fetch_contract_details(contract_info):
    """Busca detalhes de um contrato específico na API do PNCP"""
    try:
        cnpj = contract_info['cnpj']
        ano = contract_info['ano_compra']
        sequencial = contract_info['sequencial_compra']
        
        # Remover zeros à esquerda do sequencial se necessário
        if sequencial:
            sequencial = str(int(sequencial))
        
        # Montar URL da API
        url = f"{API_BASE_URL}/{cnpj}/compras/{ano}/{sequencial}"
        
        # Fazer requisição
        response = requests.get(url, timeout=TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extrair campos que precisamos
            extracted_data = {
                'id_contratacao': contract_info['id_contratacao'],
                'informacaoComplementar': data.get('informacaoComplementar'),
                'justificativaPresencial': data.get('justificativaPresencial'),
                'linkSistemaOrigem': data.get('linkSistemaOrigem'),
                'linkProcessoEletronico': data.get('linkProcessoEletronico'),
                'modalidadeNome': data.get('modalidadeNome'),
                'modoDisputaNome': data.get('modoDisputaNome'),
                'tipoInstrumentoConvocatorioNome': data.get('tipoInstrumentoConvocatorioNome'),
                'situacaoCompraNome': data.get('situacaoCompraNome'),
                'existeResultado': data.get('existeResultado'),
                'orcamentoSigilosoCodigo': data.get('orcamentoSigilosoCodigo'),
                'orcamentoSigilosoDescricao': data.get('orcamentoSigilosoDescricao'),
                'usuarioNome': data.get('usuarioNome'),
                'fontesOrcamentarias': json.dumps(data.get('fontesOrcamentarias', []), ensure_ascii=False) if data.get('fontesOrcamentarias') else None
            }
            
            # Amparo legal
            amparo_legal = data.get('amparoLegal', {})
            if amparo_legal:
                extracted_data['amparoLegal_nome'] = amparo_legal.get('nome')
                extracted_data['amparoLegal_descricao'] = amparo_legal.get('descricao')
            
            # Órgão sub-rogado
            orgao_sub_rogado = data.get('orgaoSubRogado', {})
            if orgao_sub_rogado:
                extracted_data['orgaoSubRogado_cnpj'] = orgao_sub_rogado.get('cnpj')
                extracted_data['orgaoSubRogado_razaoSocial'] = orgao_sub_rogado.get('razaoSocial')
                extracted_data['orgaoSubRogado_poderId'] = orgao_sub_rogado.get('poderId')
                extracted_data['orgaoSubRogado_esferaId'] = orgao_sub_rogado.get('esferaId')
            
            # Unidade sub-rogada
            unidade_sub_rogada = data.get('unidadeSubRogada', {})
            if unidade_sub_rogada:
                extracted_data['unidadeSubRogada_ufNome'] = unidade_sub_rogada.get('ufNome')
                extracted_data['unidadeSubRogada_ufSigla'] = unidade_sub_rogada.get('ufSigla')
                extracted_data['unidadeSubRogada_municipioNome'] = unidade_sub_rogada.get('municipioNome')
                extracted_data['unidadeSubRogada_codigoUnidade'] = unidade_sub_rogada.get('codigoUnidade')
                extracted_data['unidadeSubRogada_nomeUnidade'] = unidade_sub_rogada.get('nomeUnidade')
                extracted_data['unidadeSubRogada_codigoIbge'] = unidade_sub_rogada.get('codigoIbge')
            
            return extracted_data
        
        elif response.status_code == 404:
            # Contrato não encontrado - normal para alguns casos
            return None
        else:
            log_message(f"Erro HTTP {response.status_code} para contrato {contract_info['numero_controle']}", "warning")
            return None
            
    except requests.exceptions.Timeout:
        log_message(f"Timeout para contrato {contract_info['numero_controle']}", "warning")
        return None
    except Exception as e:
        log_message(f"Erro ao buscar contrato {contract_info['numero_controle']}: {e}", "error")
        return None

def update_contract_in_db(contract_data):
    """Atualiza um contrato no banco de dados"""
    try:
        with db_lock:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Montar query UPDATE
            set_clauses = []
            params = []
            
            for field, value in contract_data.items():
                if field != 'id_contratacao' and value is not None:
                    set_clauses.append(f"{field} = ?")
                    params.append(value)
            
            if set_clauses:
                query = f"""
                    UPDATE contratacao 
                    SET {', '.join(set_clauses)}
                    WHERE ID_CONTRATACAO = ?
                """
                params.append(contract_data['id_contratacao'])
                
                cursor.execute(query, params)
                conn.commit()
                
                return cursor.rowcount > 0
            
            conn.close()
            return False
            
    except Exception as e:
        log_message(f"Erro ao atualizar contrato {contract_data['id_contratacao']}: {e}", "error")
        return False

def process_contracts_batch(contracts_batch, progress, batch_id):
    """Processa um lote de contratos"""
    
    successful_updates = 0
    failed_updates = 0
    
    # Criar um task para este lote
    batch_task = progress.add_task(f"[bold yellow]Lote {batch_id}", total=len(contracts_batch))
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submeter todas as requisições
        future_to_contract = {
            executor.submit(fetch_contract_details, contract): contract 
            for contract in contracts_batch
        }
        
        # Processar resultados conforme chegam
        for future in as_completed(future_to_contract):
            contract_info = future_to_contract[future]
            try:
                contract_data = future.result()
                
                if contract_data:
                    # Atualizar no banco
                    if update_contract_in_db(contract_data):
                        successful_updates += 1
                    else:
                        failed_updates += 1
                else:
                    failed_updates += 1
                    
            except Exception as e:
                log_message(f"Erro no processamento: {e}", "error")
                failed_updates += 1
            
            # Atualizar progresso
            progress.update(batch_task, advance=1)
    
    progress.remove_task(batch_task)
    
    return successful_updates, failed_updates

def main():
    """Função principal"""
    console.print(Panel("[bold green]🔄 ATUALIZAÇÃO DE CAMPOS FALTANTES - CONTRATOS PNCP[/bold green]"))
    
    if TEST_MODE:
        console.print(Panel(f"[bold yellow]⚠️ MODO DE TESTE ATIVO - Processando apenas {TEST_LIMIT} contratos[/bold yellow]"))
    
    # Verificar se banco existe
    if not os.path.exists(DB_PATH):
        console.print(f"[bold red]❌ Banco de dados não encontrado: {DB_PATH}[/bold red]")
        return
    
    # Buscar contratos para atualizar
    log_message("Buscando contratos que precisam ser atualizados...", "info")
    contracts = get_contracts_to_update()
    
    if not contracts:
        console.print("[bold green]✅ Nenhum contrato precisa ser atualizado![/bold green]")
        return
    
    # Criar tabela de resumo
    summary_table = Table(title="📊 Resumo da Atualização")
    summary_table.add_column("Parâmetro", style="cyan")
    summary_table.add_column("Valor", style="white")
    
    summary_table.add_row("Contratos a atualizar", str(len(contracts)))
    summary_table.add_row("Tamanho do lote", str(BATCH_SIZE))
    summary_table.add_row("Workers por lote", str(MAX_WORKERS))
    summary_table.add_row("Modo", "TESTE" if TEST_MODE else "PRODUÇÃO")
    
    console.print(summary_table)
    
    # Dividir em lotes
    batches = [contracts[i:i + BATCH_SIZE] for i in range(0, len(contracts), BATCH_SIZE)]
    
    log_message(f"Processando {len(contracts)} contratos em {len(batches)} lotes", "info")
    
    # Configurar progresso
    progress = Progress(
        TextColumn("[bold white]{task.description}"),
        BarColumn(complete_style="green", finished_style="bright_green"),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console
    )
    
    # Contadores
    total_successful = 0
    total_failed = 0
    
    with progress:
        main_task = progress.add_task("[bold white]📊 Processando lotes", total=len(batches))
        
        for batch_id, batch in enumerate(batches, 1):
            log_message(f"Processando lote {batch_id}/{len(batches)} ({len(batch)} contratos)", "info")
            
            # Processar o lote
            successful, failed = process_contracts_batch(batch, progress, batch_id)
            
            total_successful += successful
            total_failed += failed
            
            log_message(f"Lote {batch_id} concluído: {successful} sucessos, {failed} falhas", "success")
            
            # Atualizar progresso principal
            progress.update(main_task, advance=1)
            
            # Pequena pausa entre lotes para não sobrecarregar a API
            time.sleep(1)
    
    # Relatório final
    console.print(Panel("[bold green]📋 RELATÓRIO FINAL[/bold green]"))
    
    final_table = Table(title="🎯 Resultado da Atualização")
    final_table.add_column("Métrica", style="cyan")
    final_table.add_column("Quantidade", style="white")
    final_table.add_column("Percentual", style="yellow")
    
    total_processed = total_successful + total_failed
    success_rate = (total_successful / total_processed * 100) if total_processed > 0 else 0
    
    final_table.add_row("Contratos processados", str(total_processed), "100%")
    final_table.add_row("Atualizações bem-sucedidas", str(total_successful), f"{success_rate:.1f}%")
    final_table.add_row("Falhas", str(total_failed), f"{100-success_rate:.1f}%")
    
    console.print(final_table)
    
    if success_rate >= 80:
        console.print(Panel("[bold green]✅ ATUALIZAÇÃO CONCLUÍDA COM SUCESSO![/bold green]"))
    else:
        console.print(Panel("[bold yellow]⚠️ ATUALIZAÇÃO CONCLUÍDA COM ALGUMAS FALHAS[/bold yellow]"))

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[bold yellow]⚠️ Atualização interrompida pelo usuário[/bold yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[bold red]❌ Erro crítico: {e}[/bold red]")
        import traceback
        traceback.print_exc()
        sys.exit(1)
