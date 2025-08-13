# =======================================================================
# DOWNLOAD DE CONTRATAÇÕES DO PNCP - PIPELINE GOVGO (CAMPOS COMPLETOS)
# =======================================================================
# Este script realiza o download automatizado de dados de contratações do 
# Portal Nacional de Contratações Públicas (PNCP) através da API oficial.
# 
# ATUALIZADO: Inclui TODOS os campos extras identificados nos scripts de update
# 
# Funcionalidades:
# - Download incremental baseado na última data processada
# - Consulta paralela por modalidades para otimizar performance
# - Processamento automático de múltiplos dias
# - Controle de erros e logs estruturados
# - Integração completa com pipeline de dados
# - Captura completa de todos os campos relevantes da API
# - Normalização manual para garantir todos os campos extras
# 
# Resultado: Dados de contratações estruturados e completos.
# =======================================================================

import requests
import pandas as pd
import os
import datetime
import re
import concurrent.futures
import sys
import json
from dotenv import load_dotenv
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn, SpinnerColumn
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Configuração do console Rich
console = Console()

def log_message(message, log_type="info"):
    """Log padronizado para o pipeline"""
    if log_type == "info":
        console.print(f"[white]ℹ️  {message}[/white]")
    elif log_type == "success":
        console.print(f"[green]✅ {message}[/green]")
    elif log_type == "warning":
        console.print(f"[yellow]⚠️  {message}[/yellow]")
    elif log_type == "error":
        console.print(f"[red]❌ {message}[/red]")
    elif log_type == "debug":
        console.print(f"[cyan]🔧 {message}[/cyan]")

# Carregar configurações de caminhos
script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(script_dir, "files.env"))

# Arquivo de controle da última data processada
LAST_DATE_FILE = os.path.join(script_dir, "last_processed_date.log")

# Usar caminhos do arquivo de configuração
PATH = os.getenv("CONTRATACOES_NEW")

# Lista COMPLETA com a ordem esperada das colunas (ATUALIZADA COM CAMPOS EXTRAS)
expected_columns = [
    # Identificação
    "numeroControlePNCP",
    "anoCompra",
    "sequencialCompra",
    "numeroCompra",
    "processo",
    
    # Valores
    "valorTotalEstimado",
    "valorTotalHomologado",
    "orcamentoSigilosoCodigo",
    "orcamentoSigilosoDescricao",
    
    # Modalidade e disputa
    "modalidadeId",
    "modalidadeNome",
    "modoDisputaId",
    "modoDisputaNome",
    "tipoInstrumentoConvocatorioCodigo",
    "tipoInstrumentoConvocatorioNome",
    
    # Amparo legal
    "amparoLegal.codigo",
    "amparoLegal.nome",
    "amparoLegal.descricao",
    
    # Objeto e informações
    "objetoCompra",
    "informacaoComplementar",
    "justificativaPresencial",
    "srp",
    
    # Links
    "linkSistemaOrigem",
    "linkProcessoEletronico",
    
    # Situação
    "situacaoCompraId",
    "situacaoCompraNome",
    "existeResultado",
    
    # Datas
    "dataPublicacaoPncp",
    "dataAberturaProposta",
    "dataEncerramentoProposta",
    "dataInclusao",
    "dataAtualizacao",
    "dataAtualizacaoGlobal",
    
    # Órgão entidade
    "orgaoEntidade.cnpj",
    "orgaoEntidade.razaoSocial",
    "orgaoEntidade.poderId",
    "orgaoEntidade.esferaId",
    
    # Unidade órgão
    "unidadeOrgao.ufNome",
    "unidadeOrgao.ufSigla",
    "unidadeOrgao.municipioNome",
    "unidadeOrgao.codigoUnidade",
    "unidadeOrgao.nomeUnidade",
    "unidadeOrgao.codigoIbge",
    
    # Órgão sub-rogado
    "orgaoSubRogado.cnpj",
    "orgaoSubRogado.razaoSocial",
    "orgaoSubRogado.poderId",
    "orgaoSubRogado.esferaId",
    
    # Unidade sub-rogada
    "unidadeSubRogada.ufNome",
    "unidadeSubRogada.ufSigla",
    "unidadeSubRogada.municipioNome",
    "unidadeSubRogada.codigoUnidade",
    "unidadeSubRogada.nomeUnidade",
    "unidadeSubRogada.codigoIbge",
    
    # Usuário
    "usuarioNome",
    
    # Fontes orçamentárias (JSON)
    "fontesOrcamentarias"
]

def remove_illegal_chars(value):
    if isinstance(value, str):
        return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', value)
    return value

def clean_dataframe(df):
    return df.apply(lambda col: col.map(remove_illegal_chars))

def process_fontes_orcamentarias(fontes):
    """Converte fontes orçamentárias para JSON string"""
    if isinstance(fontes, list) and fontes:
        try:
            return json.dumps(fontes, ensure_ascii=False, separators=(',', ':'))
        except:
            return str(fontes)
    return None

def normalize_contract_data(contracts):
    """Normaliza dados dos contratos para DataFrame com todos os campos extras"""
    normalized_data = []
    
    for contract in contracts:
        # Criar registro normalizado
        record = {}
        
        # Campos simples
        record['numeroControlePNCP'] = contract.get('numeroControlePNCP')
        record['anoCompra'] = contract.get('anoCompra')
        record['sequencialCompra'] = contract.get('sequencialCompra')
        record['numeroCompra'] = contract.get('numeroCompra')
        record['processo'] = contract.get('processo')
        record['valorTotalEstimado'] = contract.get('valorTotalEstimado')
        record['valorTotalHomologado'] = contract.get('valorTotalHomologado')
        record['orcamentoSigilosoCodigo'] = contract.get('orcamentoSigilosoCodigo')
        record['orcamentoSigilosoDescricao'] = contract.get('orcamentoSigilosoDescricao')
        record['modalidadeId'] = contract.get('modalidadeId')
        record['modalidadeNome'] = contract.get('modalidadeNome')
        record['modoDisputaId'] = contract.get('modoDisputaId')
        record['modoDisputaNome'] = contract.get('modoDisputaNome')
        record['tipoInstrumentoConvocatorioCodigo'] = contract.get('tipoInstrumentoConvocatorioCodigo')
        record['tipoInstrumentoConvocatorioNome'] = contract.get('tipoInstrumentoConvocatorioNome')
        record['objetoCompra'] = contract.get('objetoCompra')
        record['informacaoComplementar'] = contract.get('informacaoComplementar')
        record['justificativaPresencial'] = contract.get('justificativaPresencial')
        record['srp'] = contract.get('srp')
        record['linkSistemaOrigem'] = contract.get('linkSistemaOrigem')
        record['linkProcessoEletronico'] = contract.get('linkProcessoEletronico')
        record['situacaoCompraId'] = contract.get('situacaoCompraId')
        record['situacaoCompraNome'] = contract.get('situacaoCompraNome')
        record['existeResultado'] = contract.get('existeResultado')
        record['dataPublicacaoPncp'] = contract.get('dataPublicacaoPncp')
        record['dataAberturaProposta'] = contract.get('dataAberturaProposta')
        record['dataEncerramentoProposta'] = contract.get('dataEncerramentoProposta')
        record['dataInclusao'] = contract.get('dataInclusao')
        record['dataAtualizacao'] = contract.get('dataAtualizacao')
        record['dataAtualizacaoGlobal'] = contract.get('dataAtualizacaoGlobal')
        record['usuarioNome'] = contract.get('usuarioNome')
        
        # Amparo legal (objeto)
        amparo_legal = contract.get('amparoLegal', {})
        record['amparoLegal.codigo'] = amparo_legal.get('codigo') if amparo_legal else None
        record['amparoLegal.nome'] = amparo_legal.get('nome') if amparo_legal else None
        record['amparoLegal.descricao'] = amparo_legal.get('descricao') if amparo_legal else None
        
        # Órgão entidade (objeto)
        orgao_entidade = contract.get('orgaoEntidade', {})
        record['orgaoEntidade.cnpj'] = orgao_entidade.get('cnpj') if orgao_entidade else None
        record['orgaoEntidade.razaoSocial'] = orgao_entidade.get('razaoSocial') if orgao_entidade else None
        record['orgaoEntidade.poderId'] = orgao_entidade.get('poderId') if orgao_entidade else None
        record['orgaoEntidade.esferaId'] = orgao_entidade.get('esferaId') if orgao_entidade else None
        
        # Unidade órgão (objeto)
        unidade_orgao = contract.get('unidadeOrgao', {})
        record['unidadeOrgao.ufNome'] = unidade_orgao.get('ufNome') if unidade_orgao else None
        record['unidadeOrgao.ufSigla'] = unidade_orgao.get('ufSigla') if unidade_orgao else None
        record['unidadeOrgao.municipioNome'] = unidade_orgao.get('municipioNome') if unidade_orgao else None
        record['unidadeOrgao.codigoUnidade'] = unidade_orgao.get('codigoUnidade') if unidade_orgao else None
        record['unidadeOrgao.nomeUnidade'] = unidade_orgao.get('nomeUnidade') if unidade_orgao else None
        record['unidadeOrgao.codigoIbge'] = unidade_orgao.get('codigoIbge') if unidade_orgao else None
        
        # Órgão sub-rogado (objeto)
        orgao_sub_rogado = contract.get('orgaoSubRogado', {})
        record['orgaoSubRogado.cnpj'] = orgao_sub_rogado.get('cnpj') if orgao_sub_rogado else None
        record['orgaoSubRogado.razaoSocial'] = orgao_sub_rogado.get('razaoSocial') if orgao_sub_rogado else None
        record['orgaoSubRogado.poderId'] = orgao_sub_rogado.get('poderId') if orgao_sub_rogado else None
        record['orgaoSubRogado.esferaId'] = orgao_sub_rogado.get('esferaId') if orgao_sub_rogado else None
        
        # Unidade sub-rogada (objeto)
        unidade_sub_rogada = contract.get('unidadeSubRogada', {})
        record['unidadeSubRogada.ufNome'] = unidade_sub_rogada.get('ufNome') if unidade_sub_rogada else None
        record['unidadeSubRogada.ufSigla'] = unidade_sub_rogada.get('ufSigla') if unidade_sub_rogada else None
        record['unidadeSubRogada.municipioNome'] = unidade_sub_rogada.get('municipioNome') if unidade_sub_rogada else None
        record['unidadeSubRogada.codigoUnidade'] = unidade_sub_rogada.get('codigoUnidade') if unidade_sub_rogada else None
        record['unidadeSubRogada.nomeUnidade'] = unidade_sub_rogada.get('nomeUnidade') if unidade_sub_rogada else None
        record['unidadeSubRogada.codigoIbge'] = unidade_sub_rogada.get('codigoIbge') if unidade_sub_rogada else None
        
        # Fontes orçamentárias (array)
        record['fontesOrcamentarias'] = process_fontes_orcamentarias(contract.get('fontesOrcamentarias'))
        
        normalized_data.append(record)
    
    return normalized_data

def fetch_by_code(date_str, codigo, progress):
    """Busca dados para um único dia e código de modalidade específico"""
    base_url = "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"
    all_data = []
    params = {
        "dataInicial": date_str,
        "dataFinal": date_str,  # Mesmo dia para início e fim
        "codigoModalidadeContratacao": codigo,
        "pagina": 1,
        "tamanhoPagina": 50
    }
    
    try:
        # Primeira requisição (página 1)
        response = requests.get(base_url, params=params, timeout=30)
        if response.status_code == 204:
            # 204 No Content - significa que não há dados para este código/data, mas não é erro
            return all_data
        elif response.status_code != 200:
            log_message(f"Erro HTTP {response.status_code} para código {codigo} em {date_str}", "warning")
            return all_data
        
        json_response = response.json()
        all_data.extend(json_response.get("data", []))
        total_paginas = json_response.get("totalPaginas", 1)
        
        if total_paginas > 1:
            task_id = progress.add_task(f"        Código {codigo}", total=total_paginas - 1)
            for page in range(2, total_paginas + 1):
                params["pagina"] = page
                response = requests.get(base_url, params=params, timeout=30)
                if response.status_code == 204:
                    # 204 No Content - não há mais dados
                    break
                elif response.status_code != 200:
                    log_message(f"Erro na página {page} para código {codigo}", "warning")
                    break
                json_response = response.json()
                all_data.extend(json_response.get("data", []))
                progress.update(task_id, advance=1)
            progress.remove_task(task_id)
        
        return all_data
        
    except Exception as e:
        log_message(f"Erro ao buscar código {codigo}: {str(e)}", "error")
        return all_data

def process_day(progress, date_str):
    """Processa os dados para um dia específico"""
    
    all_data = []
    day_task_id = progress.add_task(f"[bold yellow]    Processando {date_str} (códigos)", total=14)
    
    log_message(f"Iniciando download para {date_str} (14 modalidades)", "info")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:  # Reduzido para evitar sobrecarga
        futures = {
            executor.submit(fetch_by_code, date_str, codigo, progress): codigo 
            for codigo in range(1, 15)
        }
        for future in concurrent.futures.as_completed(futures):
            try:
                code_data = future.result()
                all_data.extend(code_data)
            except Exception as e:
                log_message(f"Erro ao processar código: {str(e)}", "error")
            progress.update(day_task_id, advance=1)
    
    progress.remove_task(day_task_id)
    log_message(f"Download concluído: {len(all_data)} contratos encontrados", "success")
    
    if all_data:
        # Normalizar dados dos contratos com todos os campos extras
        normalized_data = normalize_contract_data(all_data)
        df = pd.DataFrame(normalized_data)
        df = clean_dataframe(df)
        
        # Ordenar por modalidade e número de controle
        df.sort_values(by=["modalidadeId", "numeroControlePNCP"], inplace=True)
        
        # Reordenar colunas conforme esperado
        df = df.reindex(columns=expected_columns)
    else:
        df = pd.DataFrame(columns=expected_columns)
    return df

def get_last_processed_date():
    """Retorna a última data processada do arquivo de log"""
    if os.path.exists(LAST_DATE_FILE):
        with open(LAST_DATE_FILE, 'r') as f:
            last_date = f.read().strip()
            # Verificar se a data está no formato correto
            if re.match(r'^20\d{6}$', last_date):
                log_message(f"Última data processada encontrada: {last_date}", "info")
                return last_date
    
    # Se o arquivo não existir ou formato inválido, retorna uma data antiga padrão
    log_message("Arquivo de controle de data não encontrado ou inválido. Usando data padrão.", "warning")
    return "20250101"  # 01/01/2025 como data padrão

def update_last_processed_date(date_str):
    """Atualiza o arquivo de log com a última data processada"""
    with open(LAST_DATE_FILE, 'w') as f:
        f.write(date_str)
    log_message(f"Data de controle atualizada para: {date_str}", "success")

def get_date_range():
    """Retorna o intervalo de datas a processar (da última processada + 1 até hoje)"""
    # Obtém a última data processada
    last_date_str = get_last_processed_date()
    last_date = datetime.datetime.strptime(last_date_str, "%Y%m%d").date()
    
    # Avança um dia (para começar do dia seguinte ao último processado)
    start_date = last_date + datetime.timedelta(days=1)
    
    # Data atual
    today = datetime.date.today()
    
    # Gera o intervalo de datas
    date_range = []
    current_date = start_date
    while current_date <= today:
        date_range.append(current_date.strftime("%Y%m%d"))
        current_date += datetime.timedelta(days=1)
    
    return date_range

def main():
    """Função principal do script de download PNCP"""
    
    console.print(Panel("[bold blue] [1/7] DOWNLOAD DE CONTRATAÇÕES PNCP[/bold blue]"))
    
    # Garantir que o diretório de saída existe
    os.makedirs(PATH, exist_ok=True)
    
    # Obter intervalo de datas a processar
    date_range = get_date_range()
    
    if not date_range:
        log_message("Dados já atualizados", "success")
        return
    
    log_message(f"Processando {len(date_range)} dia(s)")
    
    # Contadores para relatório final
    total_contracts = 0
    processed_days = 0
    failed_days = 0
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[bold blue]{task.description}"),
        BarColumn(),
        "[progress.percentage]{task.percentage:>3.0f}%",
        TimeElapsedColumn(),
        console=console
    ) as progress:
        main_task = progress.add_task("Download de contratações", total=len(date_range))
        
        for date_str in date_range:
            try:
                df = process_day(progress, date_str)
                
                if not df.empty:
                    output_file = os.path.join(PATH, f"CONTRATAÇÕES_PNCP_{date_str}.xlsx")
                    df.to_excel(output_file, sheet_name=date_str, index=False)
                    total_contracts += len(df)
                    log_message(f"{date_str}: {len(df)} contratos", "success")
                    processed_days += 1
                    update_last_processed_date(date_str)
                else:
                    log_message(f"{date_str}: Sem dados", "warning")
                    failed_days += 1
                
                progress.advance(main_task)
                
            except Exception as e:
                log_message(f"{date_str}: Erro - {str(e)}", "error")
                failed_days += 1
                progress.advance(main_task)
    
    # Resultado final
    if failed_days == 0:
        log_message(f"Download concluído: {total_contracts:,} contratos", "success")
    else:
        log_message(f"Download com {failed_days} falha(s)", "warning")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log_message("Processamento interrompido pelo usuário", "warning")
        sys.exit(1)
    except Exception as e:
        log_message(f"Erro crítico no processamento: {str(e)}", "error")
        sys.exit(1)