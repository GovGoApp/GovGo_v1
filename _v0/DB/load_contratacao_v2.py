import os
import glob
import pandas as pd
import sqlite3
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

PATH_CONTRATACAO_NEW = BASE_PATH + "CONTRATAÇÕES\\NEW\\"
PATH_CONTRATACAO_OLD = BASE_PATH + "CONTRATAÇÕES\\OLD\\"



console.log("Iniciando o carregamento dos dados da tabela Contratação...")

# Obter as colunas reais da tabela contratacao
conn = sqlite3.connect(DB_FILE)
colunas_tabela = [row[1] for row in conn.execute("PRAGMA table_info(contratacao)").fetchall()]
console.log(f"Colunas disponíveis na tabela: {len(colunas_tabela)}")

# Dicionário de mapeamento ajustado para renomear as colunas
contratacao_mapping = {
    "modoDisputaId": "modoDisputaId",
    "amparoLegal.codigo": "amparoLegal_codigo",
    "amparoLegal.descricao": "amparoLegal_descricao", 
    "amparoLegal.nome": "amparoLegal_nome",  
    "dataAberturaProposta": "dataAberturaProposta",
    "dataEncerramentoProposta": "dataEncerramentoProposta",
    "srp": "srp",
    "orgaoEntidade.cnpj": "orgaoEntidade_cnpj",
    "orgaoEntidade.razaoSocial": "orgaoEntidade_razaosocial",
    "orgaoEntidade.poderId": "orgaoEntidade_poderId",
    "orgaoEntidade.esferaId": "orgaoEntidade_esferaId",
    "anoCompra": "anoCompra",
    "sequencialCompra": "sequencialCompra",
    "informacaoComplementar": "informacaoComplementar",
    "processo": "processo",
    "objetoCompra": "objetoCompra",
    "linkSistemaOrigem": "linkSistemaOrigem",
    "justificativaPresencial": "justificativaPresencial",
    "unidadeSubRogada": "unidadeSubRogada",
    "orgaoSubRogado": "orgaoSubRogado",
    "valorTotalHomologado": "valorTotalHomologado",
    "dataInclusao": "dataInclusao",
    "dataPublicacaoPncp": "dataPublicacaoPncp",
    "dataAtualizacao": "dataAtualizacao",
    "numeroCompra": "numeroCompra",
    "unidadeOrgao.ufNome": "unidadeOrgao_ufNome",
    "unidadeOrgao.ufSigla": "unidadeOrgao_ufSigla",
    "unidadeOrgao.municipioNome": "unidadeOrgao_municipioNome",
    "unidadeOrgao.codigoUnidade": "unidadeOrgao_codigoUnidade",
    "unidadeOrgao.nomeUnidade": "unidadeOrgao_nomeUnidade",
    "unidadeOrgao.codigoIbge": "unidadeOrgao_codigoIbge",
    "modalidadeId": "modalidadeId",
    "linkProcessoEletronico": "linkProcessoEletronico",
    "dataAtualizacaoGlobal": "dataAtualizacaoGlobal",
    "numeroControlePNCP": "numeroControlePNCP",
    "tipoInstrumentoConvocatorioNome": "tipoInstrumentoConvocatorioNome",
    "tipoInstrumentoConvocatorioCodigo": "tipoInstrumentoConvocatorioCodigo",
    "valorTotalEstimado": "valorTotalEstimado",
    "modalidadeNome": "modalidadeNome",
    "modoDisputaNome": "modoDisputaNome",
    "situacaoCompraId": "situacaoCompraId",
    "situacaoCompraNome": "situacaoCompraNome",
    "usuarioNome": "usuarioNome"
}

# Obter todos os numeroControlePNCP já existentes no banco de dados
console.log("Buscando registros existentes na base de dados...")
existing_ids_df = pd.read_sql("SELECT DISTINCT numeroControlePNCP FROM contratacao WHERE numeroControlePNCP IS NOT NULL", conn)
existing_ids = set(existing_ids_df['numeroControlePNCP'].astype(str).values)
console.log(f"{len(existing_ids)} registros únicos já existentes na base de dados.")

files = glob.glob(os.path.join(PATH_CONTRATACAO_NEW, "*.xlsx"))
console.log(f"{len(files)} arquivos encontrados em CONTRATACOES/NEW.")

# Contadores para estatísticas
total_registros_processados = 0
total_registros_ignorados = 0
total_registros_adicionados = 0
total_arquivos_movidos = 0

# Usamos uma única instância de Progress para acompanhar os arquivos e as abas
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
        
        try:
            excel = pd.ExcelFile(file, engine="openpyxl")
            sheets = excel.sheet_names
            # Cria uma nova tarefa para o processamento das abas deste arquivo
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
                    df.rename(columns=contratacao_mapping, inplace=True)
                    
                    # Tratamento para datas (colunas que contenham "data")
                    for col in df.columns:
                        if "data" in col.lower() and col in df.columns:
                            df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d")
                    
                    # Tratamento para CNPJ/CPF (colunas que contenham "cnpj" ou "cpf")
                    for col in df.columns:
                        if ("cnpj" in col.lower() or "cpf" in col.lower()) and col in df.columns:
                            df[col] = df[col].astype(str).str.zfill(14)
                    
                    # Verificar e remover registros duplicados
                    if "numeroControlePNCP" in df.columns:
                        # Converter para string para garantir a comparação correta
                        df["numeroControlePNCP"] = df["numeroControlePNCP"].astype(str)
                        
                        # Filtrar apenas os registros que não existem no banco de dados
                        registros_novos = df[~df["numeroControlePNCP"].isin(existing_ids)]
                        registros_ignorados = len(df) - len(registros_novos)
                        
                        total_registros_ignorados += registros_ignorados
                        
                        # Manter apenas colunas que existem na tabela do banco
                        colunas_existentes = [col for col in registros_novos.columns if col in colunas_tabela]
                        registros_filtrados = registros_novos[colunas_existentes]
                        
                        # Atualizar estatísticas
                        total_registros_adicionados += len(registros_filtrados)
                        
                        # Atualizar o conjunto de IDs existentes e inserir no banco
                        if not registros_filtrados.empty:
                            novos_ids = set(registros_filtrados["numeroControlePNCP"].dropna())
                            existing_ids.update(novos_ids)
                            
                            # Inserir registros filtrados no banco
                            registros_filtrados.to_sql("contratacao", conn, if_exists="append", index=False)
                        
                        console.print(f"    Registros: {len(df)} total, {registros_ignorados} ignorados (já existentes), {len(registros_filtrados)} adicionados")
                        console.print(f"    Colunas originais: {len(registros_novos.columns)}, Colunas inseridas: {len(colunas_existentes)}")
                    else:
                        # Se não tiver a coluna chave, insere todos os registros (após filtragem de colunas)
                        console.print(f"    [bold yellow]AVISO: Coluna 'numeroControlePNCP' não encontrada![/bold yellow]")
                        
                        # Manter apenas colunas que existem na tabela
                        colunas_existentes = [col for col in df.columns if col in colunas_tabela]
                        registros_filtrados = df[colunas_existentes]
                        
                        total_registros_adicionados += len(registros_filtrados)
                        registros_filtrados.to_sql("contratacao", conn, if_exists="append", index=False)
                        
                        console.print(f"    [bold yellow]Todos os {len(registros_filtrados)} registros serão adicionados.[/bold yellow]")
                
                except Exception as e:
                    console.print(f"  [bold red]Erro ao processar aba {sheet}: {e}[/bold red]")
                    arquivo_processado_ok = False
                
                progress.advance(sheet_task)
            
            # Commit a cada arquivo para evitar perda de dados
            conn.commit()
            
            # Mover arquivo para pasta OLD se processado com sucesso
            if arquivo_processado_ok:
                destino = os.path.join(PATH_CONTRATACAO_OLD, file_name)
                shutil.move(file, destino)
                total_arquivos_movidos += 1
                console.print(f"[bold green]Arquivo movido para: {destino}[/bold green]")
            else:
                console.print(f"[bold yellow]Arquivo mantido em NEW devido a erros no processamento.[/bold yellow]")
            
        except Exception as e:
            console.print(f"[bold red]Erro ao processar arquivo {file_name}: {e}[/bold red]")
        
        progress.advance(file_task)

conn.commit()
conn.close()

console.log(f"""
Carregamento da tabela Contratação concluído!
-----------------------------------------------
Registros processados: {total_registros_processados}
Registros ignorados (duplicados): {total_registros_ignorados}
Registros adicionados: {total_registros_adicionados}
Arquivos movidos para OLD: {total_arquivos_movidos}/{len(files)}
-----------------------------------------------
""")