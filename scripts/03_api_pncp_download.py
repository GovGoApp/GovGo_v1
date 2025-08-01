# =======================================================================
# [3/7] DOWNLOAD E CARGA DIRETA DA API PNCP PARA POSTGRESQL
# =======================================================================
# Este script realiza o download automatizado de dados de contratações e 
# itens do Portal Nacional de Contratações Públicas (PNCP) através da API 
# oficial e insere diretamente no banco PostgreSQL V1.
# 
# Funcionalidades:
# - Download incremental baseado na última data processada
# - Consulta paralela por modalidades para otimizar performance
# - Processamento automático de múltiplos dias
# - Download e inserção de contratações e itens em um único processo
# - Mapeamento automático dos campos da API para o schema V1
# - Controle de erros e logs estruturados
# - Inserção direta no PostgreSQL com tratamento de duplicatas
# 
# Resultado: Dados de contratações e itens inseridos diretamente no BD V1.
# =======================================================================

import requests
import pandas as pd
import os
import datetime
import re
import concurrent.futures
import sys
import json
import time
import psycopg2
from psycopg2.extras import execute_values, RealDictCursor
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
v1_root = os.path.dirname(script_dir)
db_dir = os.path.join(v1_root, "db")

# Adicionar db ao path para importar o mapeamento
sys.path.insert(0, db_dir)

load_dotenv(os.path.join(v1_root, ".env"))

# Importar mapeamento PNCP
from de_para_pncp_v1 import DE_PARA_PNCP, apply_field_transformation, get_table_fields

# Configurações do banco PostgreSQL V1 (Supabase)
DB_CONFIG = {
    'host': os.getenv('SUPABASE_HOST', 'localhost'),
    'port': os.getenv('SUPABASE_PORT', '6543'),
    'database': os.getenv('SUPABASE_DBNAME', 'postgres'),
    'user': os.getenv('SUPABASE_USER', 'postgres'),
    'password': os.getenv('SUPABASE_PASSWORD', '')
}

# Arquivo de controle da última data processada
LAST_DATE_FILE = os.path.join(script_dir, "last_pncp_download_date.log")

def connect_to_db(max_attempts=3, retry_delay=5):
    """Conecta ao banco PostgreSQL V1 com tentativas múltiplas"""
    attempt = 1
    while attempt <= max_attempts:
        try:
            conn = psycopg2.connect(**DB_CONFIG)
            conn.set_session(autocommit=False)
            return conn
        except psycopg2.Error as e:
            console.print(f"[bold red]Erro ao conectar ao banco (tentativa {attempt}/{max_attempts}): {e}[/bold red]")
            if attempt < max_attempts:
                console.print(f"Aguardando {retry_delay} segundos antes de tentar novamente...")
                time.sleep(retry_delay)
                attempt += 1
            else:
                console.print("[bold red]Falha ao conectar ao banco após múltiplas tentativas.[/bold red]")
                raise

def remove_illegal_chars(value):
    """Remove caracteres ilegais de strings"""
    if isinstance(value, str):
        return re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f]', '', value)
    return value

def clean_data(data):
    """Limpa dados removendo caracteres ilegais"""
    if isinstance(data, dict):
        return {k: clean_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [clean_data(item) for item in data]
    else:
        return remove_illegal_chars(data)

def normalize_contratacao_data(contract):
    """Normaliza dados de contratação da API para o schema V1"""
    return apply_field_transformation(contract, 'contratacao')

def normalize_item_data(item, numero_controle_pncp):
    """Normaliza dados de item da API para o schema V1"""
    return apply_field_transformation(item, 'item_contratacao', numero_controle_pncp)

def fetch_by_code(date_str, codigo, progress):
    """Busca dados para um único dia e código de modalidade específico"""
    base_url = "https://pncp.gov.br/api/consulta/v1/contratacoes/publicacao"
    all_data = []
    params = {
        "dataInicial": date_str,
        "dataFinal": date_str,
        "codigoModalidadeContratacao": codigo,
        "pagina": 1,
        "tamanhoPagina": 50
    }
    
    try:
        # Primeira requisição (página 1)
        response = requests.get(base_url, params=params, timeout=30)
        if response.status_code == 204:
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

def fetch_items_for_contract(numero_controle_pncp):
    """Busca itens para uma contratação específica"""
    try:
        # Extrair informações do número de controle
        if not re.match(r'^\d+-\d+-\d+/\d+$', numero_controle_pncp):
            return []
            
        parts = numero_controle_pncp.split("-")
        if len(parts) != 3:
            return []
        
        cnpj = parts[0]
        seq_and_year = parts[2].split("/")
        if len(seq_and_year) != 2:
            return []
        
        seq = seq_and_year[0]
        ano_compra = seq_and_year[1]
        sequencial_compra = str(int(seq))  # Remove zeros à esquerda
        
        # Montar URL da API de itens
        url = f"https://pncp.gov.br/api/pncp//v1/orgaos/{cnpj}/compras/{ano_compra}/{sequencial_compra}/itens"
        
        response = requests.get(url, timeout=30)
        if response.status_code == 200:
            return response.json()
        elif response.status_code == 404:
            return []  # Sem itens disponíveis
        else:
            log_message(f"Erro ao buscar itens para {numero_controle_pncp}: HTTP {response.status_code}", "warning")
            return []
            
    except Exception as e:
        log_message(f"Erro ao processar itens para {numero_controle_pncp}: {str(e)}", "warning")
        return []

def check_existing_data(conn):
    """Verifica quantos registros já existem nas tabelas"""
    try:
        cursor = conn.cursor()
        
        # Contar contratações
        cursor.execute("SELECT COUNT(*) FROM contratacao")
        count_contratacoes = cursor.fetchone()[0]
        
        # Contar itens
        cursor.execute("SELECT COUNT(*) FROM item_contratacao")
        count_itens = cursor.fetchone()[0]
        
        # Verificar data mais recente em contratacao
        cursor.execute("""
            SELECT data_publicacao_pncp 
            FROM contratacao 
            WHERE data_publicacao_pncp IS NOT NULL 
            ORDER BY data_publicacao_pncp DESC 
            LIMIT 1
        """)
        
        latest_date_result = cursor.fetchone()
        latest_date = latest_date_result[0] if latest_date_result else "N/A"
        
        log_message(f"Base atual: {count_contratacoes:,} contratações, {count_itens:,} itens", "info")
        log_message(f"Data mais recente na base: {latest_date}", "info")
        
        return count_contratacoes, count_itens, latest_date
        
    except Exception as e:
        log_message(f"Erro ao verificar dados existentes: {str(e)}", "warning")
        return 0, 0, "N/A"

def verify_tables_exist(conn):
    """Verifica se as tabelas necessárias existem"""
    try:
        cursor = conn.cursor()
        
        required_tables = ['contratacao', 'item_contratacao']
        for table in required_tables:
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = %s
                )
            """, (table,))
            
            exists = cursor.fetchone()[0]
            if not exists:
                raise Exception(f"Tabela '{table}' não encontrada no banco de dados")
        
        log_message("Todas as tabelas necessárias foram encontradas", "success")
        
    except Exception as e:
        log_message(f"Erro na verificação de tabelas: {str(e)}", "error")
        raise

def ensure_table_constraints(conn):
    """Verifica e cria constraints necessárias nas tabelas"""
    try:
        cursor = conn.cursor()
        
        # Verificar se existe constraint única em contratacao
        cursor.execute("""
            SELECT constraint_name 
            FROM information_schema.table_constraints 
            WHERE table_name = 'contratacao' 
            AND constraint_type = 'UNIQUE' 
            AND constraint_name LIKE '%numero_controle_pncp%'
        """)
        
        if not cursor.fetchone():
            log_message("Criando constraint única em contratacao.numero_controle_pncp", "info")
            cursor.execute("""
                ALTER TABLE contratacao 
                ADD CONSTRAINT uk_contratacao_numero_controle_pncp 
                UNIQUE (numero_controle_pncp)
            """)
        
        # Verificar se existe constraint única em item_contratacao
        cursor.execute("""
            SELECT constraint_name 
            FROM information_schema.table_constraints 
            WHERE table_name = 'item_contratacao' 
            AND constraint_type = 'UNIQUE' 
            AND constraint_name LIKE '%numero_controle_pncp%'
        """)
        
        if not cursor.fetchone():
            log_message("Criando constraint única em item_contratacao", "info")
            cursor.execute("""
                ALTER TABLE item_contratacao 
                ADD CONSTRAINT uk_item_contratacao_numero_controle_pncp_numero_item 
                UNIQUE (numero_controle_pncp, numero_item)
            """)
        
        conn.commit()
        log_message("Constraints verificadas/criadas com sucesso", "success")
        
    except Exception as e:
        conn.rollback()
        log_message(f"Erro ao verificar/criar constraints: {str(e)}", "warning")
        # Continuar mesmo com erro nas constraints

def insert_contratacoes(conn, contratacoes_data):
    """Insere contratações no banco de dados"""
    if not contratacoes_data:
        return 0
    
    try:
        cursor = conn.cursor()
        
        # Obter colunas da tabela
        fields = list(contratacoes_data[0].keys())
        placeholders = ', '.join(['%s'] * len(fields))
        
        # Tentar inserção com ON CONFLICT primeiro
        try:
            query = f"""
                INSERT INTO contratacao ({', '.join(fields)})
                VALUES %s
                ON CONFLICT (numero_controle_pncp) DO NOTHING
            """
            
            # Preparar dados para inserção
            values = []
            for record in contratacoes_data:
                values.append(tuple(record[field] for field in fields))
            
            # Executar inserção
            execute_values(cursor, query, values, template=f"({placeholders})")
            conn.commit()
            return cursor.rowcount
            
        except psycopg2.Error:
            # Se falhar (sem constraint), usar abordagem manual
            conn.rollback()
            log_message("Constraint não encontrada, usando verificação manual", "warning")
            
            inserted_count = 0
            for record in contratacoes_data:
                # Verificar se já existe
                cursor.execute(
                    "SELECT COUNT(*) FROM contratacao WHERE numero_controle_pncp = %s",
                    (record['numero_controle_pncp'],)
                )
                
                if cursor.fetchone()[0] == 0:
                    # Não existe, inserir
                    insert_query = f"""
                        INSERT INTO contratacao ({', '.join(fields)})
                        VALUES ({placeholders})
                    """
                    cursor.execute(insert_query, tuple(record[field] for field in fields))
                    inserted_count += 1
            
            conn.commit()
            return inserted_count
        
    except Exception as e:
        conn.rollback()
        log_message(f"Erro ao inserir contratações: {str(e)}", "error")
        raise

def insert_itens(conn, itens_data):
    """Insere itens no banco de dados"""
    if not itens_data:
        return 0
    
    try:
        cursor = conn.cursor()
        
        # Obter colunas da tabela
        fields = list(itens_data[0].keys())
        placeholders = ', '.join(['%s'] * len(fields))
        
        # Tentar inserção com ON CONFLICT primeiro
        try:
            query = f"""
                INSERT INTO item_contratacao ({', '.join(fields)})
                VALUES %s
                ON CONFLICT (numero_controle_pncp, numero_item) DO NOTHING
            """
            
            # Preparar dados para inserção
            values = []
            for record in itens_data:
                values.append(tuple(record[field] for field in fields))
            
            # Executar inserção
            execute_values(cursor, query, values, template=f"({placeholders})")
            conn.commit()
            return cursor.rowcount
            
        except psycopg2.Error:
            # Se falhar (sem constraint), usar abordagem manual
            conn.rollback()
            log_message("Constraint não encontrada, usando verificação manual para itens", "warning")
            
            inserted_count = 0
            for record in itens_data:
                # Verificar se já existe
                cursor.execute(
                    "SELECT COUNT(*) FROM item_contratacao WHERE numero_controle_pncp = %s AND numero_item = %s",
                    (record['numero_controle_pncp'], record['numero_item'])
                )
                
                if cursor.fetchone()[0] == 0:
                    # Não existe, inserir
                    insert_query = f"""
                        INSERT INTO item_contratacao ({', '.join(fields)})
                        VALUES ({placeholders})
                    """
                    cursor.execute(insert_query, tuple(record[field] for field in fields))
                    inserted_count += 1
            
            conn.commit()
            return inserted_count
        
    except Exception as e:
        conn.rollback()
        log_message(f"Erro ao inserir itens: {str(e)}", "error")
        raise

def process_day(progress, date_str, conn):
    """Processa os dados para um dia específico"""
    
    all_contracts = []
    day_task_id = progress.add_task(f"[bold yellow]    Processando {date_str} (códigos)", total=14)
    
    log_message(f"Iniciando download para {date_str} (14 modalidades)", "info")
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = {
            executor.submit(fetch_by_code, date_str, codigo, progress): codigo 
            for codigo in range(1, 15)
        }
        for future in concurrent.futures.as_completed(futures):
            try:
                code_data = future.result()
                all_contracts.extend(code_data)
            except Exception as e:
                log_message(f"Erro ao processar código: {str(e)}", "error")
            progress.update(day_task_id, advance=1)
    
    progress.remove_task(day_task_id)
    log_message(f"Download concluído: {len(all_contracts)} contratos encontrados", "success")
    
    if not all_contracts:
        return 0, 0
    
    # Limpar dados
    all_contracts = clean_data(all_contracts)
    
    # Normalizar dados de contratações
    contratacoes_data = []
    for contract in all_contracts:
        normalized = normalize_contratacao_data(contract)
        contratacoes_data.append(normalized)
    
    # Inserir contratações
    inserted_contratacoes = insert_contratacoes(conn, contratacoes_data)
    
    # Processar itens para cada contratação
    all_items = []
    items_task_id = progress.add_task(f"[bold cyan]    Baixando itens", total=len(all_contracts))
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        futures = {}
        for contract in all_contracts:
            numero_controle = contract.get('numeroControlePNCP')
            if numero_controle:
                future = executor.submit(fetch_items_for_contract, numero_controle)
                futures[future] = numero_controle
        
        for future in concurrent.futures.as_completed(futures):
            numero_controle = futures[future]
            try:
                items_data = future.result()
                if items_data:
                    for item in items_data:
                        normalized_item = normalize_item_data(item, numero_controle)
                        all_items.append(normalized_item)
            except Exception as e:
                log_message(f"Erro ao processar itens para {numero_controle}: {str(e)}", "warning")
            
            progress.update(items_task_id, advance=1)
    
    progress.remove_task(items_task_id)
    
    # Inserir itens
    inserted_itens = 0
    if all_items:
        inserted_itens = insert_itens(conn, all_items)
    
    log_message(f"Inseridos: {inserted_contratacoes} contratações, {inserted_itens} itens", "success")
    
    return inserted_contratacoes, inserted_itens

def get_last_processed_date():
    """Retorna a última data processada do arquivo de log"""
    if os.path.exists(LAST_DATE_FILE):
        with open(LAST_DATE_FILE, 'r') as f:
            last_date = f.read().strip()
            if re.match(r'^20\d{6}$', last_date):
                log_message(f"Última data processada encontrada: {last_date}", "info")
                return last_date
    
    # Se o arquivo não existir ou formato inválido, usar data mais recente como padrão
    # para evitar baixar dados históricos desnecessariamente
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    default_date = yesterday.strftime("%Y%m%d")
    
    log_message(f"Arquivo de controle não encontrado. Usando data padrão: {default_date}", "warning")
    return default_date

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
    
    console.print(Panel("[bold blue] [3/7] DOWNLOAD E CARGA DIRETA DA API PNCP[/bold blue]"))
    
    # Verificar se é modo teste (argumento da linha de comando)
    test_mode = len(sys.argv) > 1 and sys.argv[1] == "--test"
    test_date = sys.argv[2] if len(sys.argv) > 2 else datetime.date.today().strftime("%Y%m%d")
    
    if test_mode:
        console.print(Panel(f"[bold yellow]🧪 MODO TESTE - Processando apenas {test_date}[/bold yellow]"))
    
    try:
        # Conectar ao banco PostgreSQL V1
        conn = connect_to_db()
        log_message("Conectado ao banco PostgreSQL V1", "success")
        
        # Verificar se as tabelas existem
        verify_tables_exist(conn)
        
        # Verificar dados existentes
        initial_contratacoes, initial_itens, latest_date = check_existing_data(conn)
        
        # Verificar e criar constraints necessárias
        ensure_table_constraints(conn)
        
        # Obter intervalo de datas a processar
        if test_mode:
            date_range = [test_date]
            log_message(f"Modo teste: processando apenas {test_date}", "info")
        else:
            date_range = get_date_range()
        
        if not date_range:
            log_message("Dados já atualizados", "success")
            conn.close()
            return
        
        log_message(f"Processando {len(date_range)} dia(s)")
        
        # Contadores para relatório final
        total_contratacoes = 0
        total_itens = 0
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
            main_task = progress.add_task("Download e carga PNCP", total=len(date_range))
            
            for date_str in date_range:
                try:
                    inserted_contratacoes, inserted_itens = process_day(progress, date_str, conn)
                    
                    if inserted_contratacoes > 0 or inserted_itens > 0:
                        total_contratacoes += inserted_contratacoes
                        total_itens += inserted_itens
                        log_message(f"{date_str}: {inserted_contratacoes} contratações, {inserted_itens} itens", "success")
                        processed_days += 1
                        update_last_processed_date(date_str)
                    else:
                        log_message(f"{date_str}: Sem dados novos", "warning")
                        update_last_processed_date(date_str)  # Atualizar mesmo sem dados
                    
                    progress.advance(main_task)
                    
                except Exception as e:
                    log_message(f"{date_str}: Erro - {str(e)}", "error")
                    failed_days += 1
                    progress.advance(main_task)
        
        # Fechar conexão
        conn.close()
        
        # Resultado final
        if failed_days == 0:
            log_message(f"Download concluído: {total_contratacoes:,} contratações, {total_itens:,} itens", "success")
            console.print(Panel("[bold green]✅ DOWNLOAD E CARGA CONCLUÍDOS[/bold green]"))
        else:
            log_message(f"Download com {failed_days} falha(s)", "warning")
            console.print(Panel(f"[bold yellow]⚠️ DOWNLOAD COM {failed_days} FALHA(S)[/bold yellow]"))
    
    except Exception as e:
        log_message(f"Erro crítico: {str(e)}", "error")
        console.print(Panel(f"[bold red]❌ ERRO CRÍTICO: {str(e)}[/bold red]"))

if __name__ == "__main__":
    try:
        # Verificar argumentos de ajuda
        if len(sys.argv) > 1 and sys.argv[1] in ['--help', '-h']:
            console.print(Panel("""
[bold blue]📋 USO DO SCRIPT 03 - DOWNLOAD PNCP[/bold blue]

[bold green]Modo Normal:[/bold green]
python 03_api_pncp_download.py

[bold green]Modo Teste (um dia específico):[/bold green]
python 03_api_pncp_download.py --test [YYYYMMDD]

[bold green]Exemplos:[/bold green]
python 03_api_pncp_download.py --test 20250801
python 03_api_pncp_download.py --test

[bold green]Funcionalidades:[/bold green]
• Download incremental baseado na última data processada
• Inserção direta no PostgreSQL V1 (Supabase)
• Mapeamento automático de campos da API PNCP
• Tratamento de duplicatas automático
• Logs estruturados e barra de progresso
            """, title="📖 Ajuda"))
            sys.exit(0)
        
        main()
    except KeyboardInterrupt:
        log_message("Processamento interrompido pelo usuário", "warning")
        sys.exit(1)
    except Exception as e:
        log_message(f"Erro crítico no processamento: {str(e)}", "error")
        sys.exit(1)
