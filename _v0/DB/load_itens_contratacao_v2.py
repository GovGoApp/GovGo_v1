import os
import glob
import pandas as pd
import sqlite3
import time
import shutil  # Para mover arquivos
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn

console = Console()

#BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\DB\\"
#DB_PATH = "I:\\Meu Drive\\#GOvGO\\v0\\#DATA\\PNCP\\DB\\"
#DB_FILE = DB_PATH + "pncp_v2.db" #pncp.db era a base anterior com todos os campos

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

# Função para conectar ao banco com tratamento de erro e retentativas
def connect_to_db(db_file, max_attempts=3, retry_delay=5):
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

# Conexão ao banco com tratamento de erro
try:
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
    
    files = glob.glob(os.path.join(PATH_ITENS_NEW, "*.xlsx"))
    console.log(f"{len(files)} arquivos encontrados em ITENS/NEW.")
    
    # Contadores para estatísticas
    total_registros_processados = 0
    total_registros_ignorados = 0
    total_registros_adicionados = 0
    total_arquivos_movidos = 0
    
    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        file_task = progress.add_task("Processando arquivos...", total=len(files))
        for file in files:
            try:
                file_name = os.path.basename(file)
                console.print(f"[bold green]File:[/bold green] {file_name}")
                excel = pd.ExcelFile(file, engine="openpyxl")
                sheets = excel.sheet_names
                sheet_task = progress.add_task(f"Aba(s) de {file_name}", total=len(sheets))
                
                # Flag para controlar se o arquivo foi processado com sucesso
                arquivo_processado_ok = True
                
                for sheet in sheets:
                    try:
                        console.print(f"  [bold blue]Aba:[/bold blue] {sheet}")
                        df = excel.parse(sheet)
                        df = df.loc[:, ~df.columns.str.contains("^Unnamed")]
                        if df.empty:
                            progress.advance(sheet_task)
                            continue
                        
                        # Contagem de registros antes do processamento
                        registros_antes = len(df)
                        total_registros_processados += registros_antes
                        
                        df.columns = df.columns.str.strip()
                        df.rename(columns=itens_mapping, inplace=True)
                        
                        # Tratamento para datas (colunas que contenham "data")
                        for col in df.columns:
                            if "data" in col.lower() and col in df.columns:
                                df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d")
                        
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
                            registros_ignorados = len(df) - len(registros_novos)
                            
                            total_registros_ignorados += registros_ignorados
                        else:
                            # Se não tiver as colunas chave ou não conseguiu verificar registros existentes
                            registros_novos = df
                            registros_ignorados = 0
                        
                        # Manter apenas colunas que existem na tabela do banco
                        colunas_existentes = [col for col in registros_novos.columns if col in colunas_tabela]
                        registros_filtrados = registros_novos[colunas_existentes]
                        
                        # Atualizar estatísticas
                        total_registros_adicionados += len(registros_filtrados)
                        
                        # Atualizar o conjunto de IDs existentes e inserir no banco
                        if not registros_filtrados.empty:
                            try:
                                # Adicionar novos itens ao conjunto de existentes (se estiver verificando duplicatas)
                                if "numeroControlePNCP" in registros_filtrados.columns and "numeroItem" in registros_filtrados.columns:
                                    novos_pares = set(zip(registros_filtrados["numeroControlePNCP"], registros_filtrados["numeroItem"]))
                                    existing_items.update(novos_pares)
                                
                                # Inserir registros filtrados no banco (em lotes menores para reduzir problemas de I/O)
                                batch_size = 500
                                for i in range(0, len(registros_filtrados), batch_size):
                                    batch = registros_filtrados.iloc[i:i+batch_size]
                                    batch.to_sql("item_contratacao", conn, if_exists="append", index=False)
                                    # Commit parcial para reduzir tamanho da transação
                                    conn.commit()
                                
                                console.print(f"    Registros: {len(df)} total, {registros_ignorados} ignorados, {len(registros_filtrados)} adicionados")
                                console.print(f"    Colunas inseridas: {len(colunas_existentes)}")
                            except sqlite3.Error as e:
                                console.print(f"    [bold red]Erro ao inserir registros: {e}[/bold red]")
                                arquivo_processado_ok = False
                                # Tentar reconectar ao banco
                                try:
                                    conn.close()
                                    conn = connect_to_db(DB_FILE)
                                    console.print("    [bold yellow]Reconectado ao banco de dados.[/bold yellow]")
                                except:
                                    console.print("    [bold red]Falha ao reconectar. Pulando este lote.[/bold red]")
                        
                    except Exception as e:
                        console.print(f"  [bold red]Erro ao processar aba {sheet}: {e}[/bold red]")
                        arquivo_processado_ok = False
                    
                    progress.advance(sheet_task)
                
                # Commit a cada arquivo para evitar perda de dados
                try:
                    conn.commit()
                except sqlite3.Error as e:
                    console.print(f"[bold red]Erro ao fazer commit após arquivo {file_name}: {e}[/bold red]")
                    arquivo_processado_ok = False
                
                # Mover arquivo para pasta OLD se processado com sucesso
                if arquivo_processado_ok:
                    destino = os.path.join(PATH_ITENS_OLD, file_name)
                    shutil.move(file, destino)
                    total_arquivos_movidos += 1
                    console.print(f"[bold green]Arquivo movido para: {destino}[/bold green]")
                else:
                    console.print(f"[bold yellow]Arquivo mantido em NEW devido a erros no processamento.[/bold yellow]")
                
            except Exception as e:
                console.print(f"[bold red]Erro ao processar arquivo {os.path.basename(file)}: {e}[/bold red]")
            
            progress.advance(file_task)
    
    # Finalização
    try:
        conn.commit()
    except sqlite3.Error as e:
        console.print(f"[bold red]Erro ao finalizar banco de dados: {e}[/bold red]")
    finally:
        conn.close()
    
    console.log(f"""
    Carregamento da tabela Item_Contratação concluído!
    -----------------------------------------------
    Registros processados: {total_registros_processados}
    Registros ignorados (duplicados): {total_registros_ignorados}
    Registros adicionados: {total_registros_adicionados}
    Arquivos movidos para OLD: {total_arquivos_movidos}/{len(files)}
    -----------------------------------------------
    """)

except Exception as e:
    console.print(f"[bold red]Erro crítico: {e}[/bold red]")