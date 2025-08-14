# =======================================================================
# [4/7] CARGA DE ITENS DE CONTRATAÇÕES PARA BANCO SQLITE
# =======================================================================
# Este script importa os dados de itens de contratações para o banco
# SQLite, relacionando-os às contratações correspondentes.
# 
# Funcionalidades:
# - Lê os dados de itens processados
# - Insere os itens no banco, mantendo a relação com as contratações
# - Implementa validações e cálculos adicionais se necessário
# 
# Resultado: Banco de dados completo com contratações e seus itens.
# =======================================================================

import os
import glob
import pandas as pd
import sqlite3
import time
import shutil
import gc
import warnings
import datetime
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn, SpinnerColumn
from rich.panel import Panel
from dotenv import load_dotenv

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

# Suprimir avisos específicos sobre formato de data
warnings.filterwarnings("ignore", 
                       message="Could not infer format, so each element will be parsed individually", 
                       category=UserWarning)

# Carregar configurações de caminhos
script_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(script_dir, "files.env"))

# Usar caminhos do arquivo de configuração
DB_FILE = os.getenv("DB_FILE")
PATH_ITENS_NEW = os.getenv("ITENS_NEW")
PATH_ITENS_OLD = os.getenv("ITENS_OLD")

# Criar diretório OLD se não existir
if not os.path.exists(PATH_ITENS_OLD):
    os.makedirs(PATH_ITENS_OLD)

# Dicionário de mapeamento para a tabela item_contratacao
itens_mapping = {
    "numeroControlePNCP": "numeroControlePNCP",
    "numeroItem": "numeroItem",
    "descricao": "descricao",
    "materialOuServico": "materialOuServico",
    "materialOuServicoNome": "materialOuServicoNome",
    "valorUnitarioEstimado": "valorUnitarioEstimado",
    "valorTotal": "valorTotal",
    "quantidade": "quantidade",
    "unidadeMedida": "unidadeMedida",
    "orcamentoSigiloso": "orcamentoSigiloso",
    "itemCategoriaId": "itemCategoriaId",
    "itemCategoriaNome": "itemCategoriaNome",
    "patrimonio": "patrimonio",
    "codigoRegistroImobiliario": "codigoRegistroImobiliario",
    "criterioJulgamentoId": "criterioJulgamentoId",
    "criterioJulgamentoNome": "criterioJulgamentoNome",
    "situacaoCompraItem": "situacaoCompraItem",
    "situacaoCompraItemNome": "situacaoCompraItemNome",
    "tipoBeneficio": "tipoBeneficio",
    "tipoBeneficioNome": "tipoBeneficioNome",
    "incentivoProdutivoBasico": "incentivoProdutivoBasico",
    "dataInclusao": "dataInclusao",
    "dataAtualizacao": "dataAtualizacao",
    "temResultado": "temResultado",
    "imagem": "imagem",
    "aplicabilidadeMargemPreferenciaNormal": "aplicabilidadeMargemPreferenciaNormal",
    "aplicabilidadeMargemPreferenciaAdicional": "aplicabilidadeMargemPreferenciaAdicional",
    "percentualMargemPreferenciaNormal": "percentualMargemPreferenciaNormal",
    "percentualMargemPreferenciaAdicional": "percentualMargemPreferenciaAdicional",
    "ncmNbsCodigo": "ncmNbsCodigo",
    "ncmNbsDescricao": "ncmNbsDescricao",
    "catalogo": "catalogo",
    "categoriaItemCatalogo": "categoriaItemCatalogo",
    "catalogoCodigoItem": "catalogoCodigoItem",
    "informacaoComplementar": "informacaoComplementar"
}

def connect_to_db(db_file, max_attempts=3, retry_delay=5):
    """Conecta ao banco de dados com tentativas múltiplas"""
    attempt = 1
    while attempt <= max_attempts:
        try:
            conn = sqlite3.connect(db_file, timeout=60)  # Aumentar timeout para 60 segundos
            return conn
        except sqlite3.Error as e:
            console.print(f"[bold red]Erro ao conectar ao banco (tentativa {attempt}/{max_attempts}): {e}[/bold red]")
            if attempt < max_attempts:
                console.print(f"Aguardando {retry_delay} segundos antes de tentar novamente...")
                time.sleep(retry_delay)
                attempt += 1
            else:
                console.print("[bold red]Falha ao conectar ao banco após múltiplas tentativas.[/bold red]")
                raise

def safe_move_file(source, destination, max_attempts=3):
    """Tenta mover um arquivo com várias tentativas"""
    for attempt in range(max_attempts):
        try:
            # Forçar coleta de lixo para liberar quaisquer referências
            gc.collect()
            # Pequena pausa para garantir que o sistema libere o arquivo
            time.sleep(1)
            
            # Tentar mover o arquivo
            shutil.move(source, destination)
            return True
        except PermissionError:
            if attempt < max_attempts - 1:
                console.print(f"[yellow]Arquivo em uso, tentativa {attempt+1}/{max_attempts}...[/yellow]")
                time.sleep(2 * (attempt + 1))  # Espera progressivamente mais tempo
            else:
                # Se falhar após todas as tentativas, tenta copiar
                try:
                    console.print(f"[yellow]Tentando copiar o arquivo em vez de movê-lo...[/yellow]")
                    shutil.copy2(source, destination)
                    console.print(f"[yellow]Arquivo copiado para OLD. O original será removido em execução futura.[/yellow]")
                    return True
                except Exception as e:
                    console.print(f"[red]Não foi possível copiar o arquivo: {e}[/red]")
                    return False
        except Exception as e:
            console.print(f"[red]Erro ao mover arquivo: {e}[/red]")
            return False
    return False

def process_excel_file(file_path, conn, existing_items, colunas_tabela, progress=None, sheet_task=None):
    """Processa um arquivo Excel de itens de contratação"""
    arquivo_processado_ok = True
    registros_processados = 0
    registros_ignorados = 0
    registros_adicionados = 0
    
    try:
        # Usar context manager para garantir que o arquivo seja fechado
        with pd.ExcelFile(file_path, engine="openpyxl") as excel:
            sheets = excel.sheet_names
            
            for sheet in sheets:
                try:
                    console.print(f"  [bold blue]Aba:[/bold blue] {sheet}")
                    df = excel.parse(sheet)
                    df = df.loc[:, ~df.columns.str.contains("^Unnamed")]
                    
                    if df.empty:
                        if progress and sheet_task:
                            progress.advance(sheet_task)
                        continue
                    
                    # Contagem de registros antes do processamento
                    registros_processados += len(df)
                    
                    # Preparar os dados
                    df.columns = df.columns.str.strip()
                    df.rename(columns=itens_mapping, inplace=True)
                    
                    # Tratamento para datas - USANDO A ABORDAGEM SIMPLES DA VERSÃO V2
                    colunas_data = [col for col in df.columns if "data" in col.lower() and col in df.columns]
                    if colunas_data:
                        console.print(f"    Processando {len(colunas_data)} colunas de data...")
                        
                    for col in colunas_data:
                        try:
                            # Abordagem simples que funciona bem
                            df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d")
                        except Exception as e:
                            console.print(f"    [yellow]Aviso ao processar coluna {col}: {e}[/yellow]")
                    
                    # Verificar e remover registros duplicados
                    if "numeroControlePNCP" in df.columns and "numeroItem" in df.columns and existing_items:
                        # Converter para string para garantir a comparação correta
                        df["numeroControlePNCP"] = df["numeroControlePNCP"].astype(str)
                        df["numeroItem"] = df["numeroItem"].astype(str)
                        
                        # Filtrar apenas os registros que não existem no banco de dados
                        df["is_new"] = df.apply(
                            lambda row: (row["numeroControlePNCP"], row["numeroItem"]) not in existing_items, 
                            axis=1
                        )
                        registros_novos = df[df["is_new"]].drop(columns=["is_new"])
                        ignorados_na_aba = len(df) - len(registros_novos)
                        
                        registros_ignorados += ignorados_na_aba
                        
                        # Manter apenas colunas que existem na tabela do banco
                        colunas_existentes = [col for col in registros_novos.columns if col in colunas_tabela]
                        registros_filtrados = registros_novos[colunas_existentes]
                        
                        # Atualizar estatísticas
                        registros_adicionados += len(registros_filtrados)
                        
                        # Atualizar o conjunto de IDs existentes e inserir no banco
                        if not registros_filtrados.empty:
                            # Adicionar novos itens ao conjunto de existentes
                            novos_pares = set(zip(registros_filtrados["numeroControlePNCP"], registros_filtrados["numeroItem"]))
                            existing_items.update(novos_pares)
                            
                            # Inserir registros filtrados no banco (em lotes para melhor performance)
                            batch_size = 500
                            for i in range(0, len(registros_filtrados), batch_size):
                                batch = registros_filtrados.iloc[i:i+batch_size]
                                batch.to_sql("item_contratacao", conn, if_exists="append", index=False)
                                # Commit parcial para reduzir tamanho da transação
                                conn.commit()
                            
                            console.print(f"    Registros: {len(df)} total, {ignorados_na_aba} ignorados, {len(registros_filtrados)} adicionados")
                            console.print(f"    Colunas inseridas: {len(colunas_existentes)}")
                        else:
                            console.print(f"    Todos os {len(df)} registros já existiam na base. Nenhum adicionado.")
                    else:
                        # Se não tiver as colunas chave ou não conseguiu verificar registros existentes
                        console.print(f"    [bold yellow]AVISO: Não foi possível verificar duplicatas.[/bold yellow]")
                        
                        # Manter apenas colunas que existem na tabela
                        colunas_existentes = [col for col in df.columns if col in colunas_tabela]
                        registros_filtrados = df[colunas_existentes]
                        
                        # Atualizar estatísticas
                        registros_adicionados += len(registros_filtrados)
                        
                        # Inserir registros filtrados no banco (em lotes para melhor performance)
                        if not registros_filtrados.empty:
                            batch_size = 500
                            for i in range(0, len(registros_filtrados), batch_size):
                                batch = registros_filtrados.iloc[i:i+batch_size]
                                batch.to_sql("item_contratacao", conn, if_exists="append", index=False)
                                # Commit parcial para reduzir tamanho da transação
                                conn.commit()
                            
                            console.print(f"    [bold yellow]Todos os {len(registros_filtrados)} registros serão adicionados.[/bold yellow]")
                            console.print(f"    Colunas inseridas: {len(colunas_existentes)}")
                
                except Exception as e:
                    console.print(f"  [bold red]Erro ao processar aba {sheet}: {e}[/bold red]")
                    arquivo_processado_ok = False
                
                if progress and sheet_task:
                    progress.advance(sheet_task)
                    
        # Commit após processar todas as abas
        conn.commit()
    
    except Exception as e:
        console.print(f"[bold red]Erro ao processar arquivo: {e}[/bold red]")
        arquivo_processado_ok = False
    
    return arquivo_processado_ok, registros_processados, registros_ignorados, registros_adicionados

def write_processing_log(registros_adicionados):
    """Escreve no arquivo de log o número de registros adicionados"""
    try:
        # Criar diretório de log se não existir
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "LOGS")
        os.makedirs(log_dir, exist_ok=True)
        
        # Nome do arquivo de log
        log_file = os.path.join(log_dir, "processamento.log")
        
        # Escrever no arquivo
        with open(log_file, "a") as f:
            data_atual = datetime.datetime.now().strftime("%Y-%m-%d")
            f.write(f"{data_atual} - SCRIPT04: {registros_adicionados} itens adicionados\n")
    except Exception as e:
        log_message(f"Erro ao escrever no log: {str(e)}", "error")

def main():
    console.print(Panel("[bold blue] [4/7] CARGA DE ITENS SQLITE[/bold blue]"))
    
    try:
        # Conectar ao banco de dados
        conn = connect_to_db(DB_FILE)
        
        # Verificar se a tabela existe
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='item_contratacao'")
        if not cursor.fetchone():
            log_message("Tabela 'item_contratacao' não encontrada", "error")
            console.print(Panel("[bold red]❌ TABELA NÃO ENCONTRADA[/bold red]"))
            return
        
        # Obter colunas da tabela
        colunas_tabela = [row[1] for row in conn.execute("PRAGMA table_info(item_contratacao)").fetchall()]
        
        # Obter registros existentes
        existing_items = set()
        try:
            existing_items_df = pd.read_sql(
                "SELECT numeroControlePNCP, numeroItem FROM item_contratacao WHERE numeroControlePNCP IS NOT NULL", 
                conn
            )
            if not existing_items_df.empty:
                existing_items_df['numeroControlePNCP'] = existing_items_df['numeroControlePNCP'].astype(str)
                existing_items_df['numeroItem'] = existing_items_df['numeroItem'].astype(str)
                existing_items = set(zip(existing_items_df['numeroControlePNCP'], existing_items_df['numeroItem']))
                log_message(f"Itens existentes: {len(existing_items):,}")
        except Exception as e:
            log_message("Erro ao verificar duplicatas", "warning")
        
        # Buscar arquivos para processar
        files = glob.glob(os.path.join(PATH_ITENS_NEW, "*.xlsx"))
        
        if not files:
            log_message("Nenhum arquivo encontrado", "success")
            return
        
        log_message(f"Processando {len(files)} arquivo(s)")
        
        # Contadores
        total_arquivos_processados = 0
        total_registros_adicionados = 0
        
        # Processar arquivos
        with Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
            TimeElapsedColumn(),
            console=console
        ) as progress:
            task = progress.add_task("Carga de itens", total=len(files))
            
            for file in files:
                file_name = os.path.basename(file)
                
                # Processar arquivo
                arquivo_ok, registros, ignorados, adicionados = process_excel_file(
                    file, conn, existing_items, colunas_tabela
                )
                
                if arquivo_ok:
                    total_registros_adicionados += adicionados
                    
                    # Mover arquivo
                    destino = os.path.join(PATH_ITENS_OLD, file_name)
                    if safe_move_file(file, destino):
                        total_arquivos_processados += 1
                        if adicionados > 0:
                            log_message(f"{file_name}: {adicionados} novos itens", "success")
                        else:
                            log_message(f"{file_name}: Sem novos itens", "warning")
                    else:
                        log_message(f"{file_name}: Erro ao mover arquivo", "warning")
                        total_arquivos_processados += 1
                else:
                    log_message(f"{file_name}: Erro no processamento", "error")
                
                progress.advance(task)
        
        # Finalizar
        conn.commit()
        conn.close()
        
        # Resultado final
        if total_registros_adicionados > 0:
            log_message(f"Carga concluída: {total_registros_adicionados:,} novos itens", "success")
            write_processing_log(total_registros_adicionados)  # Registrar no log
            console.print(Panel("[bold green]✅ CARGA CONCLUÍDA[/bold green]"))
        else:
            log_message("Carga concluída: Sem novos itens", "success")
            write_processing_log(0)  # Registrar zero no log
            console.print(Panel("[bold green]✅ SEM NOVOS DADOS[/bold green]"))
    
    except Exception as e:
        log_message(f"Erro na carga: {str(e)}", "error")
        console.print(Panel(f"[bold red]❌ ERRO NA CARGA: {str(e)}[/bold red]"))

if __name__ == "__main__":
    main()