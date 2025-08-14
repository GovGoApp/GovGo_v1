# =======================================================================
# CARGA DE CONTRATAÇÕES PARA BANCO SQLITE - VERSÃO COMPLETA (V2)
# =======================================================================
# Este script importa os dados de contratações para um banco SQLite,
# organizando-os em tabelas estruturadas.
# 
# VERSÃO 2: Suporte completo a TODOS os campos baixados pela API PNCP
# 
# Funcionalidades:
# - Lê os dados de contratações processados (com campos completos)
# - Cria/atualiza estrutura de tabelas no SQLite
# - Realiza a carga dos dados, evitando duplicidades
# - Implementa validações e transformações de dados necessárias
# - Suporte a campos aninhados (orgaoEntidade, unidadeOrgao, etc.)
# - Suporte a campos extras (orcamentoSigilo, fontes orçamentárias, etc.)
# 
# Resultado: Banco de dados atualizado com contratações completas.
# =======================================================================

import os
import glob
import pandas as pd
import sqlite3
import shutil
import time
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
PATH_CONTRATACAO_NEW = os.getenv("CONTRATACOES_NEW")
PATH_CONTRATACAO_OLD = os.getenv("CONTRATACOES_OLD")

# Criar diretório OLD se não existir
if not os.path.exists(PATH_CONTRATACAO_OLD):
    os.makedirs(PATH_CONTRATACAO_OLD)
    console.log(f"Diretório criado: {PATH_CONTRATACAO_OLD}")

# Dicionário de mapeamento para renomear as colunas - VERSÃO COMPLETA (V2)
# Inclui TODOS os campos baixados pelo script 01_pncp_download_v2.py
contratacao_mapping = {
    # Identificação
    "numeroControlePNCP": "numeroControlePNCP",
    "anoCompra": "anoCompra",
    "sequencialCompra": "sequencialCompra",
    "numeroCompra": "numeroCompra",
    "processo": "processo",
    
    # Valores
    "valorTotalEstimado": "valorTotalEstimado",
    "valorTotalHomologado": "valorTotalHomologado",
    "orcamentoSigilosoCodigo": "orcamentoSigilosoCodigo",
    "orcamentoSigilosoDescricao": "orcamentoSigilosoDescricao",
    
    # Modalidade e disputa
    "modalidadeId": "modalidadeId",
    "modalidadeNome": "modalidadeNome",
    "modoDisputaId": "modoDisputaId",
    "modoDisputaNome": "modoDisputaNome",
    "tipoInstrumentoConvocatorioCodigo": "tipoInstrumentoConvocatorioCodigo",
    "tipoInstrumentoConvocatorioNome": "tipoInstrumentoConvocatorioNome",
    
    # Amparo legal
    "amparoLegal.codigo": "amparoLegal_codigo",
    "amparoLegal.nome": "amparoLegal_nome",
    "amparoLegal.descricao": "amparoLegal_descricao",
    
    # Objeto e informações
    "objetoCompra": "objetoCompra",
    "informacaoComplementar": "informacaoComplementar",
    "justificativaPresencial": "justificativaPresencial",
    "srp": "srp",
    
    # Links
    "linkSistemaOrigem": "linkSistemaOrigem",
    "linkProcessoEletronico": "linkProcessoEletronico",
    
    # Situação
    "situacaoCompraId": "situacaoCompraId",
    "situacaoCompraNome": "situacaoCompraNome",
    "existeResultado": "existeResultado",
    
    # Datas
    "dataPublicacaoPncp": "dataPublicacaoPncp",
    "dataAberturaProposta": "dataAberturaProposta",
    "dataEncerramentoProposta": "dataEncerramentoProposta",
    "dataInclusao": "dataInclusao",
    
    # Órgão e unidade (campos aninhados)
    "orgaoEntidade.razaoSocial": "orgaoEntidade_razaoSocial",
    "orgaoEntidade.nomeFantasia": "orgaoEntidade_nomeFantasia",
    "orgaoEntidade.cnpj": "orgaoEntidade_cnpj",
    "orgaoEntidade.municipio.nome": "orgaoEntidade_municipio_nome",
    "orgaoEntidade.municipio.ibge": "orgaoEntidade_municipio_ibge",
    "orgaoEntidade.municipio.uf.sigla": "orgaoEntidade_municipio_uf_sigla",
    "orgaoEntidade.municipio.uf.nome": "orgaoEntidade_municipio_uf_nome",
    "orgaoEntidade.poder.codigo": "orgaoEntidade_poder_codigo",
    "orgaoEntidade.poder.nome": "orgaoEntidade_poder_nome",
    "orgaoEntidade.esferaId": "orgaoEntidade_esferaId",
    "orgaoEntidade.esfera": "orgaoEntidade_esfera",
    "orgaoEntidade.tipoOrganizacao": "orgaoEntidade_tipoOrganizacao",
    "orgaoEntidade.endereco.logradouro": "orgaoEntidade_endereco_logradouro",
    "orgaoEntidade.endereco.numero": "orgaoEntidade_endereco_numero",
    "orgaoEntidade.endereco.bairro": "orgaoEntidade_endereco_bairro",
    "orgaoEntidade.endereco.cep": "orgaoEntidade_endereco_cep",
    "orgaoEntidade.endereco.complemento": "orgaoEntidade_endereco_complemento",
    "orgaoEntidade.endereco.ddd": "orgaoEntidade_endereco_ddd",
    "orgaoEntidade.endereco.telefone": "orgaoEntidade_endereco_telefone",
    "orgaoEntidade.endereco.email": "orgaoEntidade_endereco_email",
    "orgaoEntidade.endereco.site": "orgaoEntidade_endereco_site",
    
    # Unidade orgão
    "unidadeOrgao.nome": "unidadeOrgao_nome",
    "unidadeOrgao.codigoUnidade": "unidadeOrgao_codigoUnidade",
    "unidadeOrgao.nomeUnidade": "unidadeOrgao_nomeUnidade",
    "unidadeOrgao.municipio.nome": "unidadeOrgao_municipio_nome",
    "unidadeOrgao.municipio.ibge": "unidadeOrgao_municipio_ibge",
    "unidadeOrgao.municipio.uf.sigla": "unidadeOrgao_municipio_uf_sigla",
    "unidadeOrgao.municipio.uf.nome": "unidadeOrgao_municipio_uf_nome",
    
    # Usuário
    "usuarioNome": "usuarioNome",
    "usuarioId": "usuarioId",
    
    # Outros campos específicos
    "tipoRecurso": "tipoRecurso",
    "isSrp": "isSrp",
    "isOrcamentoSigiloso": "isOrcamentoSigiloso",
    "existeContratoAssociado": "existeContratoAssociado",
    
    # Observações
    "observacoes": "observacoes",
    
    # Descrição completa (campo derivado)
    "descricaoCompleta": "descricaoCompleta"
}

# Função para criar uma conexão com o banco
def create_connection():
    """Cria e retorna uma conexão com o banco SQLite"""
    conn = sqlite3.connect(DB_FILE)
    return conn

# Função para criar tabela se não existir
def create_table_if_not_exists(conn):
    """Cria a tabela de contratações se ela não existir - VERSÃO COMPLETA (V2)"""
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS contratacoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            
            -- Identificação
            numeroControlePNCP TEXT UNIQUE NOT NULL,
            anoCompra INTEGER,
            sequencialCompra INTEGER,
            numeroCompra TEXT,
            processo TEXT,
            
            -- Valores
            valorTotalEstimado REAL,
            valorTotalHomologado REAL,
            orcamentoSigilosoCodigo TEXT,
            orcamentoSigilosoDescricao TEXT,
            
            -- Modalidade e disputa
            modalidadeId INTEGER,
            modalidadeNome TEXT,
            modoDisputaId INTEGER,
            modoDisputaNome TEXT,
            tipoInstrumentoConvocatorioCodigo TEXT,
            tipoInstrumentoConvocatorioNome TEXT,
            
            -- Amparo legal
            amparoLegal_codigo TEXT,
            amparoLegal_nome TEXT,
            amparoLegal_descricao TEXT,
            
            -- Objeto e informações
            objetoCompra TEXT,
            informacaoComplementar TEXT,
            justificativaPresencial TEXT,
            srp INTEGER,
            
            -- Links
            linkSistemaOrigem TEXT,
            linkProcessoEletronico TEXT,
            
            -- Situação
            situacaoCompraId INTEGER,
            situacaoCompraNome TEXT,
            existeResultado INTEGER,
            
            -- Datas
            dataPublicacaoPncp TEXT,
            dataAberturaProposta TEXT,
            dataEncerramentoProposta TEXT,
            dataInclusao TEXT,
            
            -- Órgão e entidade
            orgaoEntidade_razaoSocial TEXT,
            orgaoEntidade_nomeFantasia TEXT,
            orgaoEntidade_cnpj TEXT,
            orgaoEntidade_municipio_nome TEXT,
            orgaoEntidade_municipio_ibge TEXT,
            orgaoEntidade_municipio_uf_sigla TEXT,
            orgaoEntidade_municipio_uf_nome TEXT,
            orgaoEntidade_poder_codigo INTEGER,
            orgaoEntidade_poder_nome TEXT,
            orgaoEntidade_esferaId INTEGER,
            orgaoEntidade_esfera TEXT,
            orgaoEntidade_tipoOrganizacao TEXT,
            orgaoEntidade_endereco_logradouro TEXT,
            orgaoEntidade_endereco_numero TEXT,
            orgaoEntidade_endereco_bairro TEXT,
            orgaoEntidade_endereco_cep TEXT,
            orgaoEntidade_endereco_complemento TEXT,
            orgaoEntidade_endereco_ddd TEXT,
            orgaoEntidade_endereco_telefone TEXT,
            orgaoEntidade_endereco_email TEXT,
            orgaoEntidade_endereco_site TEXT,
            
            -- Unidade orgão
            unidadeOrgao_nome TEXT,
            unidadeOrgao_codigoUnidade TEXT,
            unidadeOrgao_nomeUnidade TEXT,
            unidadeOrgao_municipio_nome TEXT,
            unidadeOrgao_municipio_ibge TEXT,
            unidadeOrgao_municipio_uf_sigla TEXT,
            unidadeOrgao_municipio_uf_nome TEXT,
            
            -- Usuário
            usuarioNome TEXT,
            usuarioId INTEGER,
            
            -- Outros campos específicos
            tipoRecurso TEXT,
            isSrp INTEGER,
            isOrcamentoSigiloso INTEGER,
            existeContratoAssociado INTEGER,
            
            -- Observações
            observacoes TEXT,
            
            -- Descrição completa (campo derivado)
            descricaoCompleta TEXT
        )
    """)
    
    # Criar índices para melhorar performance
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_numeroControlePNCP ON contratacoes (numeroControlePNCP)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_anoCompra ON contratacoes (anoCompra)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_municipio ON contratacoes (unidadeOrgao_municipio_nome)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_uf ON contratacoes (unidadeOrgao_municipio_uf_sigla)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_modalidade ON contratacoes (modalidadeId)
    """)
    
    cursor.execute("""
        CREATE INDEX IF NOT EXISTS idx_valor ON contratacoes (valorTotalEstimado)
    """)
    
    conn.commit()
    cursor.close()

# Função para obter colunas da tabela
def get_table_columns(conn):
    """Obtém as colunas da tabela de contratações"""
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(contratacoes)")
    columns = [row[1] for row in cursor.fetchall()]
    cursor.close()
    return columns

# Função para mover arquivo para outro diretório
def move_file_to_processed(file_path, max_attempts=3):
    """Move um arquivo para o diretório de processados"""
    filename = os.path.basename(file_path)
    destination = os.path.join(PATH_CONTRATACAO_OLD, filename)
    
    for attempt in range(max_attempts):
        try:
            shutil.move(file_path, destination)
            return True
        except PermissionError:
            if attempt < max_attempts - 1:
                console.print(f"[yellow]Arquivo em uso, tentativa {attempt+1}/{max_attempts}...[/yellow]")
                time.sleep(2 * (attempt + 1))  # Espera progressivamente mais tempo
            else:
                # Se falhar após todas as tentativas, tenta copiar
                try:
                    console.print(f"[yellow]Tentando copiar o arquivo em vez de movê-lo...[/yellow]")
                    shutil.copy2(file_path, destination)
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
    """Processa um arquivo Excel com todos os campos V2"""
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
                    
                    # Verificar se o DataFrame possui a coluna de ID
                    if 'numeroControlePNCP' not in df.columns:
                        console.print(f"[red]Coluna 'numeroControlePNCP' não encontrada na aba {sheet}[/red]")
                        arquivo_processado_ok = False
                        continue
                    
                    # Filtrar registros que já existem no banco
                    df_filtered = df[~df['numeroControlePNCP'].isin(existing_ids)]
                    registros_novos = len(df_filtered)
                    registros_duplicados = len(df) - registros_novos
                    
                    console.print(f"    [blue]Registros novos:[/blue] {registros_novos}")
                    console.print(f"    [yellow]Registros duplicados (ignorados):[/yellow] {registros_duplicados}")
                    
                    registros_ignorados += registros_duplicados
                    
                    if registros_novos > 0:
                        # Garantir que todas as colunas necessárias existam
                        for col in colunas_tabela:
                            if col not in df_filtered.columns:
                                df_filtered[col] = None
                        
                        # Filtrar apenas as colunas que existem na tabela
                        df_to_insert = df_filtered[colunas_tabela]
                        
                        # Inserir os dados
                        df_to_insert.to_sql('contratacoes', conn, if_exists='append', index=False)
                        
                        # Atualizar conjunto de IDs existentes
                        existing_ids.update(df_filtered['numeroControlePNCP'].tolist())
                        
                        registros_adicionados += registros_novos
                        console.print(f"    [green]Registros adicionados:[/green] {registros_novos}")
                    
                    # Atualizar progress bar se fornecida
                    if progress and sheet_task:
                        progress.advance(sheet_task)
                    
                except Exception as e:
                    console.print(f"[red]Erro ao processar aba {sheet}: {e}[/red]")
                    arquivo_processado_ok = False
                    continue
                    
    except Exception as e:
        console.print(f"[red]Erro ao processar arquivo {file_path}: {e}[/red]")
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
            f.write(f"{data_atual} - SCRIPT03: {registros_adicionados} registros adicionados\n")
    except Exception as e:
        log_message(f"Erro ao escrever no log: {str(e)}", "error")

def main():
    """Função principal que executa o processamento"""
    console.print(Panel("[bold blue] [3/7] CARGA DE CONTRATAÇÕES SQLITE[/bold blue]"))

    try:
        # Criar conexão e tabela
        conn = create_connection()
        create_table_if_not_exists(conn)
        colunas_tabela = get_table_columns(conn)
        
        # Carregar IDs existentes
        cursor = conn.cursor()
        cursor.execute("SELECT numeroControlePNCP FROM contratacoes")
        existing_ids = set(row[0] for row in cursor.fetchall())
        cursor.close()
        
        log_message(f"Registros existentes: {len(existing_ids):,}")
        
        # Buscar arquivos Excel
        excel_files = glob.glob(os.path.join(PATH_CONTRATACAO_NEW, "*.xlsx"))
        excel_files.extend(glob.glob(os.path.join(PATH_CONTRATACAO_NEW, "*.xls")))
        
        if not excel_files:
            log_message("Nenhum arquivo encontrado", "success")
            return
        
        log_message(f"Processando {len(excel_files)} arquivo(s)")
        
        # Estatísticas
        arquivos_processados = 0
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
            task = progress.add_task("Carga para SQLite", total=len(excel_files))
            
            for file_path in excel_files:
                arquivo_nome = os.path.basename(file_path)
                
                # Processar arquivo
                arquivo_ok, registros_processados, registros_ignorados, registros_adicionados = process_excel_file(
                    file_path, conn, existing_ids, colunas_tabela
                )
                
                if arquivo_ok:
                    arquivos_processados += 1
                    total_registros_adicionados += registros_adicionados
                    
                    if registros_adicionados > 0:
                        log_message(f"{arquivo_nome}: {registros_adicionados} novos registros", "success")
                    else:
                        log_message(f"{arquivo_nome}: Sem novos registros", "warning")
                    
                    # Mover arquivo
                    if move_file_to_processed(file_path):
                        existing_ids.update([None])  # Placeholder para evitar reprocessamento
                    
                else:
                    log_message(f"{arquivo_nome}: Erro no processamento", "error")
                
                progress.advance(task)
        
        # Commit final
        conn.commit()
        
        # Resultado final
        if total_registros_adicionados > 0:
            log_message(f"Carga concluída: {total_registros_adicionados:,} novos registros", "success")
            console.print(Panel("[bold green]✅ CARGA CONCLUÍDA[/bold green]"))
            # Escrever no arquivo de log
            write_processing_log(total_registros_adicionados)
        else:
            log_message("Carga concluída: Sem novos registros", "success")
            console.print(Panel("[bold green]✅ SEM NOVOS DADOS[/bold green]"))
            # Escrever zero no log
            write_processing_log(0)
        
        # Escrever log de processamento
        write_processing_log(total_registros_adicionados)
        
    except Exception as e:
        log_message(f"Erro na carga: {str(e)}", "error")
        console.print(Panel(f"[bold red]❌ ERRO NA CARGA: {str(e)}[/bold red]"))
        raise
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()
