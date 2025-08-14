#!/usr/bin/env python3
"""
Script para atualizar campos faltantes na tabela contratacao do SQLite
Busca dados da API do PNCP para preencher os novos campos adicionados
"""

import requests
import sqlite3
import json
import time
import sys
import os
from datetime import datetime
from rich.console import Console
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.panel import Panel
from rich.table import Table
import concurrent.futures
import threading

console = Console()

# Configurações
DB_PATH = r"C:\Users\Haroldo Duraes\Desktop\GOvGO\v0\#DATA\PNCP\DB\pncp_v2.db"
BATCH_SIZE = 100  # Aumentado para melhor performance
MAX_WORKERS = 10  # Mais workers para paralelização
API_BASE_URL = "https://pncp.gov.br/api/pncp/v1/orgaos"
TIMEOUT = 30  # Timeout para requisições

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
    """Busca contratos que precisam ser atualizados (campos faltantes)"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Primeiro, vamos ver quantos contratos existem
        cursor.execute("SELECT COUNT(*) FROM contratacao WHERE numeroControlePNCP IS NOT NULL")
        total_contracts = cursor.fetchone()[0]
        log_message(f"Total de contratos na base: {total_contracts}", "info")
        
        # Verificar quais campos estão vazios
        cursor.execute("""
            SELECT 
                SUM(CASE WHEN informacaoComplementar IS NULL THEN 1 ELSE 0 END) as missing_info,
                SUM(CASE WHEN justificativaPresencial IS NULL THEN 1 ELSE 0 END) as missing_justificativa,
                SUM(CASE WHEN linkSistemaOrigem IS NULL THEN 1 ELSE 0 END) as missing_link,
                SUM(CASE WHEN modalidadeNome IS NULL THEN 1 ELSE 0 END) as missing_modalidade,
                SUM(CASE WHEN situacaoCompraNome IS NULL THEN 1 ELSE 0 END) as missing_situacao,
                SUM(CASE WHEN amparoLegal_nome IS NULL THEN 1 ELSE 0 END) as missing_amparo
            FROM contratacao 
            WHERE numeroControlePNCP IS NOT NULL
        """)
        
        missing_stats = cursor.fetchone()
        log_message(f"Campos faltantes - Info: {missing_stats[0]}, Justificativa: {missing_stats[1]}, Link: {missing_stats[2]}", "debug")
        log_message(f"Modalidade: {missing_stats[3]}, Situação: {missing_stats[4]}, Amparo: {missing_stats[5]}", "debug")
        
        # Buscar contratos que precisam ser atualizados (pelo menos um campo faltante)
        query = """
        SELECT numeroControlePNCP, anoCompra, sequencialCompra, orgaoEntidade_cnpj, modalidadeId
        FROM contratacao 
        WHERE numeroControlePNCP IS NOT NULL 
        AND numeroControlePNCP != ''
        AND (
            informacaoComplementar IS NULL OR
            justificativaPresencial IS NULL OR
            linkSistemaOrigem IS NULL OR
            modalidadeNome IS NULL OR
            situacaoCompraNome IS NULL OR
            amparoLegal_nome IS NULL OR
            modoDisputaNome IS NULL OR
            tipoInstrumentoConvocatorioNome IS NULL OR
            existeResultado IS NULL
        )
        ORDER BY dataPublicacaoPncp DESC
        LIMIT 50000
        """
        
        cursor.execute(query)
        contracts = cursor.fetchall()
        
        conn.close()
        
        log_message(f"Encontrados {len(contracts)} contratos para atualizar", "info")
        return contracts
        
    except Exception as e:
        log_message(f"Erro ao buscar contratos: {e}", "error")
        return []

def fetch_contract_details(numero_controle):
    """Busca detalhes completos de um contrato na API do PNCP"""
    try:
        # Parse do número de controle: CNPJ-X-SEQUENCIAL/ANO
        if not numero_controle or not isinstance(numero_controle, str):
            return None
            
        # Limpar espaços e caracteres especiais
        numero_controle = numero_controle.strip()
        
        # Validar formato básico
        if not numero_controle or '-' not in numero_controle or '/' not in numero_controle:
            log_message(f"Formato inválido de número de controle: {numero_controle}", "warning")
            return None
            
        parts = numero_controle.split("-")
        if len(parts) != 3:
            log_message(f"Formato inválido (partes): {numero_controle}", "warning")
            return None
            
        cnpj = parts[0]
        seq_and_year = parts[2].split("/")
        if len(seq_and_year) != 2:
            log_message(f"Formato inválido (seq/ano): {numero_controle}", "warning")
            return None
            
        seq = seq_and_year[0]
        ano = seq_and_year[1]
        
        # Validar se são números
        try:
            sequencial = str(int(seq))  # Remove zeros à esquerda
            int(ano)  # Valida se é número
            int(cnpj)  # Valida se é número
        except ValueError:
            log_message(f"Valores não numéricos em: {numero_controle}", "warning")
            return None
        
        # Construir URL da API
        url = f"{API_BASE_URL}/{cnpj}/compras/{ano}/{sequencial}"
        
        # Fazer requisição com timeout
        response = requests.get(url, timeout=TIMEOUT)
        
        if response.status_code == 200:
            data = response.json()
            
            # Extrair campos necessários
            result = {
                'numeroControlePNCP': numero_controle,
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
                'usuarioNome': data.get('usuarioNome')
            }
            
            # Processar amparo legal (objeto aninhado)
            amparo_legal = data.get('amparoLegal', {})
            if amparo_legal:
                result['amparoLegal_nome'] = amparo_legal.get('nome')
                result['amparoLegal_descricao'] = amparo_legal.get('descricao')
            
            # Processar órgão sub-rogado (objeto aninhado)
            orgao_sub_rogado = data.get('orgaoSubRogado', {})
            if orgao_sub_rogado:
                result['orgaoSubRogado_cnpj'] = orgao_sub_rogado.get('cnpj')
                result['orgaoSubRogado_razaoSocial'] = orgao_sub_rogado.get('razaoSocial')
                result['orgaoSubRogado_poderId'] = orgao_sub_rogado.get('poderId')
                result['orgaoSubRogado_esferaId'] = orgao_sub_rogado.get('esferaId')
            
            # Processar unidade sub-rogada (objeto aninhado)
            unidade_sub_rogada = data.get('unidadeSubRogada', {})
            if unidade_sub_rogada:
                result['unidadeSubRogada_ufNome'] = unidade_sub_rogada.get('ufNome')
                result['unidadeSubRogada_ufSigla'] = unidade_sub_rogada.get('ufSigla')
                result['unidadeSubRogada_municipioNome'] = unidade_sub_rogada.get('municipioNome')
                result['unidadeSubRogada_codigoUnidade'] = unidade_sub_rogada.get('codigoUnidade')
                result['unidadeSubRogada_nomeUnidade'] = unidade_sub_rogada.get('nomeUnidade')
                result['unidadeSubRogada_codigoIbge'] = unidade_sub_rogada.get('codigoIbge')
            
            # Processar fontes orçamentárias (array)
            fontes_orcamentarias = data.get('fontesOrcamentarias', [])
            if fontes_orcamentarias:
                result['fontesOrcamentarias'] = json.dumps(fontes_orcamentarias, ensure_ascii=False)
            
            return result
            
        elif response.status_code == 404:
            log_message(f"Contrato não encontrado na API: {numero_controle}", "debug")
            return None
        else:
            log_message(f"API retornou status {response.status_code} para {numero_controle}", "warning")
            return None
            
    except requests.exceptions.Timeout:
        log_message(f"Timeout na requisição para {numero_controle}", "warning")
        return None
    except requests.exceptions.RequestException as e:
        log_message(f"Erro de conexão para {numero_controle}: {e}", "warning")
        return None
    except Exception as e:
        log_message(f"Erro ao buscar dados da API para {numero_controle}: {e}", "error")
        return None

def update_contract_in_db(contract_data):
    """Atualiza um contrato no banco de dados"""
    try:
        with db_lock:
            conn = sqlite3.connect(DB_PATH)
            cursor = conn.cursor()
            
            # Construir query de UPDATE dinamicamente
            update_fields = []
            params = []
            
            for field, value in contract_data.items():
                if field != 'numeroControlePNCP' and value is not None:
                    update_fields.append(f"{field} = ?")
                    params.append(value)
            
            if not update_fields:
                conn.close()
                return False
            
            # Adicionar condição WHERE
            params.append(contract_data['numeroControlePNCP'])
            
            query = f"""
            UPDATE contratacao 
            SET {', '.join(update_fields)}
            WHERE numeroControlePNCP = ?
            """
            
            cursor.execute(query, params)
            conn.commit()
            conn.close()
            
            return True
            
    except Exception as e:
        log_message(f"Erro ao atualizar contrato {contract_data.get('numeroControlePNCP', 'N/A')}: {e}", "error")
        return False

def process_contract_batch(contracts_batch, progress, task_id):
    """Processa um lote de contratos usando ThreadPoolExecutor"""
    updated_count = 0
    failed_count = 0
    
    def process_single_contract(contract):
        """Processa um único contrato"""
        numero_controle = contract[0]
        
        try:
            # Buscar dados da API
            contract_data = fetch_contract_details(numero_controle)
            
            if contract_data:
                # Atualizar no banco
                if update_contract_in_db(contract_data):
                    return "updated"
                else:
                    return "failed_db"
            else:
                return "failed_api"
                
        except Exception as e:
            log_message(f"Erro ao processar contrato {numero_controle}: {e}", "error")
            return "failed_exception"
    
    # Usar ThreadPoolExecutor para processar contratos em paralelo
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Submeter todas as tarefas
        future_to_contract = {executor.submit(process_single_contract, contract): contract for contract in contracts_batch}
        
        # Processar resultados conforme ficam prontos
        for future in concurrent.futures.as_completed(future_to_contract):
            contract = future_to_contract[future]
            try:
                result = future.result()
                if result == "updated":
                    updated_count += 1
                else:
                    failed_count += 1
                    if result == "failed_api":
                        log_message(f"Falha na API para {contract[0]}", "debug")
                    elif result == "failed_db":
                        log_message(f"Falha no banco para {contract[0]}", "warning")
            except Exception as e:
                log_message(f"Erro inesperado para {contract[0]}: {e}", "error")
                failed_count += 1
            
            # Atualizar progresso
            progress.update(task_id, advance=1)
            
            # Pequena pausa para não sobrecarregar
            time.sleep(0.05)
    
    return updated_count, failed_count

def main():
    """Função principal"""
    console.print(Panel("[bold cyan]🔄 ATUALIZAÇÃO DE CAMPOS FALTANTES NO SQLITE[/bold cyan]"))
    
    # Verificar se o banco existe
    if not os.path.exists(DB_PATH):
        log_message(f"Banco de dados não encontrado: {DB_PATH}", "error")
        return
    
    # Buscar contratos para atualizar
    contracts = get_contracts_to_update()
    
    if not contracts:
        log_message("Nenhum contrato precisa ser atualizado", "success")
        console.print(Panel("[bold green]✅ TODOS OS CONTRATOS JÁ ESTÃO ATUALIZADOS[/bold green]"))
        return
    
    # Criar tabela de resumo
    summary_table = Table(title="📊 Resumo da Atualização")
    summary_table.add_column("Parâmetro", style="cyan")
    summary_table.add_column("Valor", style="white")
    
    summary_table.add_row("Contratos para atualizar", str(len(contracts)))
    summary_table.add_row("Tamanho do lote", str(BATCH_SIZE))
    summary_table.add_row("Workers por lote", str(MAX_WORKERS))
    summary_table.add_row("Timeout API", f"{TIMEOUT}s")
    summary_table.add_row("Banco de dados", os.path.basename(DB_PATH))
    
    console.print(summary_table)
    
    # Confirmar operação
    if len(contracts) > 1000:
        console.print(f"\n[bold yellow]⚠️ Atenção: Serão processados {len(contracts)} contratos![/bold yellow]")
        console.print("[yellow]Isso pode levar várias horas dependendo da API.[/yellow]")
    
    confirm = input("\nDeseja continuar com a atualização? (s/N): ").strip().lower()
    if confirm not in ['s', 'sim', 'y', 'yes']:
        log_message("Operação cancelada pelo usuário", "warning")
        return
    
    # Dividir contratos em lotes
    batches = [contracts[i:i + BATCH_SIZE] for i in range(0, len(contracts), BATCH_SIZE)]
    
    log_message(f"Processando {len(contracts)} contratos em {len(batches)} lotes", "info")
    
    # Contadores
    total_updated = 0
    total_failed = 0
    
    # Processar com barra de progresso
    with Progress(
        TextColumn("[bold white]{task.description}"),
        BarColumn(complete_style="green", finished_style="bright_green"),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeElapsedColumn(),
        TimeRemainingColumn(),
        console=console
    ) as progress:
        
        main_task = progress.add_task("[bold green]🔄 Atualizando contratos", total=len(contracts))
        
        # Processar lotes sequencialmente (mas com threads dentro de cada lote)
        for i, batch in enumerate(batches, 1):
            log_message(f"Processando lote {i}/{len(batches)} ({len(batch)} contratos)", "info")
            
            # Processar o lote atual com threads
            updated, failed = process_contract_batch(batch, progress, main_task)
            
            total_updated += updated
            total_failed += failed
            
            success_rate = (updated / len(batch)) * 100 if batch else 0
            log_message(f"Lote {i} concluído: {updated} atualizados, {failed} falhas ({success_rate:.1f}% sucesso)", "info")
            
            # Pausa entre lotes para não sobrecarregar a API
            if i < len(batches):
                time.sleep(2)
    
    # Relatório final
    final_table = Table(title="📈 Relatório Final")
    final_table.add_column("Métrica", style="cyan")
    final_table.add_column("Quantidade", style="white")
    final_table.add_column("Percentual", style="yellow")
    
    final_table.add_row("Contratos processados", str(len(contracts)), "100%")
    final_table.add_row("Contratos atualizados", str(total_updated), 
                       f"{(total_updated/len(contracts)*100):.1f}%" if contracts else "0%")
    final_table.add_row("Contratos com falha", str(total_failed), 
                       f"{(total_failed/len(contracts)*100):.1f}%" if contracts else "0%")
    
    console.print(final_table)
    
    if total_failed == 0:
        log_message("Atualização concluída com sucesso!", "success")
        console.print(Panel("[bold green]✅ ATUALIZAÇÃO CONCLUÍDA COM SUCESSO![/bold green]"))
    else:
        log_message(f"Atualização concluída com {total_failed} falhas", "warning")
        console.print(Panel(f"[bold yellow]⚠️ ATUALIZAÇÃO CONCLUÍDA COM {total_failed} FALHAS[/bold yellow]"))

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log_message("Atualização interrompida pelo usuário", "warning")
        console.print(Panel("[bold yellow]⚠️ ATUALIZAÇÃO INTERROMPIDA[/bold yellow]"))
        sys.exit(1)
    except Exception as e:
        log_message(f"Erro crítico: {e}", "error")
        console.print(Panel(f"[bold red]❌ ERRO CRÍTICO: {e}[/bold red]"))
        import traceback
        traceback.print_exc()
        sys.exit(1)
