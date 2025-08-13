import os
import glob
import pandas as pd
import sqlite3
import shutil
import time
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
PATH_CONTRATACAO_NEW = BASE_PATH + "CONTRATAÇÕES\\NEW\\"
PATH_CONTRATACAO_OLD = BASE_PATH + "CONTRATAÇÕES\\OLD\\"

# Criar diretório OLD se não existir
if not os.path.exists(PATH_CONTRATACAO_OLD):
    os.makedirs(PATH_CONTRATACAO_OLD)
    console.log(f"Diretório criado: {PATH_CONTRATACAO_OLD}")

# Dicionário de mapeamento para renomear as colunas
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

def process_excel_file(file_path, conn, existing_ids, colunas_tabela, progress=None, sheet_task=None):
    """Processa um arquivo Excel"""
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
                    df.rename(columns=contratacao_mapping, inplace=True)
                    
                    # Tratamento para datas - USANDO A ABORDAGEM SIMPLES DA VERSÃO V2
                    colunas_data = [col for col in df.columns if "data" in col.lower() and col in df.columns]
                    if colunas_data:
                        console.print(f"    Processando {len(colunas_data)} colunas de data...")
                        
                    for col in colunas_data:
                        try:
                            # Abordagem simples da v2 que funciona bem
                            df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d")
                        except Exception as e:
                            console.print(f"    [yellow]Aviso ao processar coluna {col}: {e}[/yellow]")
                    
                    # Tratamento para CNPJ/CPF
                    colunas_documento = [col for col in df.columns if ("cnpj" in col.lower() or "cpf" in col.lower()) and col in df.columns]
                    for col in colunas_documento:
                        try:
                            # Preencher valores nulos
                            df[col] = df[col].fillna('')
                            # Converter para string e preencher zeros à esquerda
                            df[col] = df[col].astype(str).replace('nan', '')
                            # Aplicar zfill apenas em strings numéricas não vazias
                            mask_numerico = df[col].str.match(r'^\d+$')
                            df.loc[mask_numerico, col] = df.loc[mask_numerico, col].str.zfill(14)
                        except Exception as e:
                            console.print(f"    [yellow]Aviso ao processar coluna {col}: {e}[/yellow]")
                    
                    # Verificar e remover registros duplicados
                    if "numeroControlePNCP" in df.columns:
                        # Converter para string para garantir a comparação correta
                        df["numeroControlePNCP"] = df["numeroControlePNCP"].astype(str)
                        
                        # Filtrar apenas os registros que não existem no banco de dados
                        registros_novos = df[~df["numeroControlePNCP"].isin(existing_ids)]
                        ignorados_na_aba = len(df) - len(registros_novos)
                        
                        registros_ignorados += ignorados_na_aba
                        
                        # Manter apenas colunas que existem na tabela do banco
                        colunas_existentes = [col for col in registros_novos.columns if col in colunas_tabela]
                        registros_filtrados = registros_novos[colunas_existentes]
                        
                        # Atualizar estatísticas
                        registros_adicionados += len(registros_filtrados)
                        
                        # Atualizar o conjunto de IDs existentes e inserir no banco
                        if not registros_filtrados.empty:
                            novos_ids = set(registros_filtrados["numeroControlePNCP"].dropna())
                            existing_ids.update(novos_ids)
                            
                            # Inserir registros filtrados no banco (em chunks para melhor performance)
                            registros_filtrados.to_sql("contratacao", conn, if_exists="append", index=False)
                        
                        console.print(f"    Registros: {len(df)} total, {ignorados_na_aba} ignorados (já existentes), {len(registros_filtrados)} adicionados")
                        console.print(f"    Colunas originais: {len(registros_novos.columns)}, Colunas inseridas: {len(colunas_existentes)}")
                    else:
                        # Se não tiver a coluna chave, insere todos os registros (após filtragem de colunas)
                        console.print(f"    [bold yellow]AVISO: Coluna 'numeroControlePNCP' não encontrada![/bold yellow]")
                        
                        # Manter apenas colunas que existem na tabela
                        colunas_existentes = [col for col in df.columns if col in colunas_tabela]
                        registros_filtrados = df[colunas_existentes]
                        
                        registros_adicionados += len(registros_filtrados)
                        registros_filtrados.to_sql("contratacao", conn, if_exists="append", index=False)
                        
                        console.print(f"    [bold yellow]Todos os {len(registros_filtrados)} registros serão adicionados.[/bold yellow]")
                
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
    console.log("Iniciando o carregamento dos dados da tabela Contratação...")
    
    # Conectar ao banco de dados
    conn = sqlite3.connect(DB_FILE)
    
    # Obter as colunas reais da tabela contratacao
    colunas_tabela = [row[1] for row in conn.execute("PRAGMA table_info(contratacao)").fetchall()]
    console.log(f"Colunas disponíveis na tabela: {len(colunas_tabela)}")
    
    # Obter todos os numeroControlePNCP já existentes no banco de dados
    console.log("Buscando registros existentes na base de dados...")
    existing_ids_df = pd.read_sql("SELECT DISTINCT numeroControlePNCP FROM contratacao WHERE numeroControlePNCP IS NOT NULL", conn)
    existing_ids = set(existing_ids_df['numeroControlePNCP'].astype(str).values)
    console.log(f"{len(existing_ids)} registros únicos já existentes na base de dados.")
    
    # Obter lista de arquivos para processar
    files = glob.glob(os.path.join(PATH_CONTRATACAO_NEW, "*.xlsx"))
    console.log(f"{len(files)} arquivos encontrados em CONTRATACOES/NEW.")
    
    # Contadores para estatísticas
    total_registros_processados = 0
    total_registros_ignorados = 0
    total_registros_adicionados = 0
    total_arquivos_movidos = 0
    
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
                file, conn, existing_ids, colunas_tabela, 
                progress=progress, sheet_task=sheet_task
            )
            
            arquivo_processado_ok, registros, ignorados, adicionados = resultado
            
            # Atualizar contadores
            total_registros_processados += registros
            total_registros_ignorados += ignorados
            total_registros_adicionados += adicionados
            
            # Mover arquivo para pasta OLD se processado com sucesso
            if arquivo_processado_ok:
                destino = os.path.join(PATH_CONTRATACAO_OLD, file_name)
                if safe_move_file(file, destino):
                    total_arquivos_movidos += 1
                    console.print(f"[bold green]Arquivo movido para: {destino}[/bold green]")
                else:
                    console.print(f"[bold red]Falha ao mover arquivo para OLD.[/bold red]")
            else:
                console.print(f"[bold yellow]Arquivo mantido em NEW devido a erros no processamento.[/bold yellow]")
            
            # Avançar a barra de progresso do arquivo
            progress.advance(file_task)
    
    # Finalizar conexão com o banco
    conn.commit()
    conn.close()
    
    # Exibir estatísticas finais
    console.log(f"""
    Carregamento da tabela Contratação concluído!
    -----------------------------------------------
    Registros processados: {total_registros_processados}
    Registros ignorados (duplicados): {total_registros_ignorados}
    Registros adicionados: {total_registros_adicionados}
    Arquivos movidos para OLD: {total_arquivos_movidos}/{len(files)}
    -----------------------------------------------
    """)

if __name__ == "__main__":
    main()