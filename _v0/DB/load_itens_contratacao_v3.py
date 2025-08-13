import os
import glob
import pandas as pd
import sqlite3
import time
import shutil
import gc
import warnings
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn

console = Console()

# Suprimir avisos específicos sobre formato de data
warnings.filterwarnings("ignore", 
                       message="Could not infer format, so each element will be parsed individually", 
                       category=UserWarning)

# Base paths
BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\DB\\"
DB_FILE = BASE_PATH + "pncp_v2.db"
PATH_ITENS_NEW = BASE_PATH + "ITENS\\NEW\\"
PATH_ITENS_OLD = BASE_PATH + "ITENS\\OLD\\"

# Criar diretório OLD se não existir
if not os.path.exists(PATH_ITENS_OLD):
    os.makedirs(PATH_ITENS_OLD)
    console.log(f"Diretório criado: {PATH_ITENS_OLD}")

console.log("Iniciando o carregamento dos dados da tabela Item_Contratação...")

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

def main():
    try:
        # Conectar ao banco de dados
        conn = connect_to_db(DB_FILE)
        
        # Verificar se a tabela existe
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='item_contratacao'")
        if not cursor.fetchone():
            console.print("[bold red]Tabela 'item_contratacao' não encontrada no banco de dados![/bold red]")
            raise Exception("Tabela não existe")
        
        # Obter as colunas reais da tabela
        colunas_tabela = [row[1] for row in conn.execute("PRAGMA table_info(item_contratacao)").fetchall()]
        console.log(f"Colunas disponíveis na tabela: {len(colunas_tabela)}")
        
        # Tentar obter registros existentes, com tratamento de erro
        existing_items = set()
        try:
            console.log("Buscando registros existentes na base de dados...")
            existing_items_df = pd.read_sql(
                "SELECT numeroControlePNCP, numeroItem FROM item_contratacao WHERE numeroControlePNCP IS NOT NULL AND numeroItem IS NOT NULL", 
                conn
            )
            
            # Criar conjunto de tuplas para verificação rápida
            if not existing_items_df.empty:
                existing_items_df['numeroControlePNCP'] = existing_items_df['numeroControlePNCP'].astype(str)
                existing_items_df['numeroItem'] = existing_items_df['numeroItem'].astype(str)
                existing_items = set(zip(existing_items_df['numeroControlePNCP'], existing_items_df['numeroItem']))
                console.log(f"{len(existing_items)} itens únicos já existentes na base de dados.")
            else:
                console.log("Nenhum item encontrado na base de dados.")
        except Exception as e:
            console.print(f"[bold yellow]Erro ao obter registros existentes: {e}[/bold yellow]")
            console.print("[bold yellow]Continuando sem verificação de duplicatas. Todos os registros serão inseridos.[/bold yellow]")
        
        # Obter lista de arquivos para processar
        files = glob.glob(os.path.join(PATH_ITENS_NEW, "*.xlsx"))
        console.log(f"{len(files)} arquivos encontrados em ITENS/NEW.")
        
        # Contadores para estatísticas
        total_registros_processados = 0
        total_registros_ignorados = 0
        total_registros_adicionados = 0
        total_arquivos_processados = 0
        
        # Iniciar processamento com barra de progresso
        with Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TimeElapsedColumn(),
            console=console
        ) as progress:
            file_task = progress.add_task("Processando arquivos...", total=len(files))
            
            for file in files:
                file_name = os.path.basename(file)
                console.print(f"[bold green]File:[/bold green] {file_name}")
                
                # Criar tarefa para as abas deste arquivo
                with pd.ExcelFile(file, engine="openpyxl") as temp_excel:
                    sheet_count = len(temp_excel.sheet_names)
                sheet_task = progress.add_task(f"Aba(s) de {file_name}", total=sheet_count)
                
                # Processar o arquivo
                resultado = process_excel_file(
                    file, conn, existing_items, colunas_tabela, 
                    progress=progress, sheet_task=sheet_task
                )
                
                arquivo_processado_ok, registros, ignorados, adicionados = resultado
                
                # Atualizar contadores
                total_registros_processados += registros
                total_registros_ignorados += ignorados
                total_registros_adicionados += adicionados

                # MOVER OS ARQUIVOS de NEW para OLD após processamento bem-sucedido
                if arquivo_processado_ok:
                    destino = os.path.join(PATH_ITENS_OLD, file_name)
                    if safe_move_file(file, destino):
                        total_arquivos_processados += 1
                        console.print(f"[bold green]Arquivo processado e movido para: {destino}[/bold green]")
                    else:
                        console.print(f"[bold yellow]Arquivo processado com sucesso, mas não foi possível movê-lo para OLD.[/bold yellow]")
                        total_arquivos_processados += 1  # Contabilizar mesmo se não conseguiu mover
                else:
                    console.print(f"[bold yellow]Arquivo mantido em NEW devido a erros no processamento.[/bold yellow]")

                # Avançar a barra de progresso do arquivo
                progress.advance(file_task)
        
        # Finalizar conexão com o banco
        conn.commit()
        conn.close()
        
        # Exibir estatísticas finais
        console.log(f"""
        Carregamento da tabela Item_Contratação concluído!
        -----------------------------------------------
        Registros processados: {total_registros_processados}
        Registros ignorados (duplicados): {total_registros_ignorados}
        Registros adicionados: {total_registros_adicionados}
        Arquivos processados com sucesso: {total_arquivos_processados}/{len(files)}
        -----------------------------------------------
        """)
    
    except Exception as e:
        console.print(f"[bold red]Erro crítico: {e}[/bold red]")

if __name__ == "__main__":
    main()