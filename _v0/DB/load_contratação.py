import os
import glob
import pandas as pd
import sqlite3
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn

console = Console()

BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
#DB_PATH = BASE_PATH + "DB\\"
#DB_FILE = DB_PATH + "pncp.db"

DB_PATH = "I:\\Meu Drive\\#GOvGO\\v0\\#DATA\\PNCP\\DB\\"
DB_FILE = DB_PATH + "pncp_v2.db" #pncp.db era a base anterior com todos os campos

PATH_CONTRATACAO = BASE_PATH + "CONTRATAÇÕES\\"

console.log("Iniciando o carregamento dos dados da tabela Contratação...")

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

conn = sqlite3.connect(DB_FILE)

files = glob.glob(os.path.join(PATH_CONTRATACAO, "*.xlsx"))
console.log(f"{len(files)} arquivos encontrados em CONTRATACOES.")

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
        excel = pd.ExcelFile(file, engine="openpyxl")
        sheets = excel.sheet_names
        # Cria uma nova tarefa para o processamento das abas deste arquivo
        sheet_task = progress.add_task(f"Aba(s) de {file_name}", total=len(sheets))
        for sheet in sheets:
            console.print(f"  [bold blue]Aba:[/bold blue] {sheet}")
            df = excel.parse(sheet)
            df = df.loc[:, ~df.columns.str.contains("^Unnamed")]
            if df.empty:
                progress.advance(sheet_task)
                continue
            df.columns = df.columns.str.strip()
            df.rename(columns=contratacao_mapping, inplace=True)
            # Tratamento para datas (colunas que contenham "data")
            for col in df.columns:
                if "data" in col.lower():
                    df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d")
            # Tratamento para CNPJ/CPF (colunas que contenham "cnpj" ou "cpf")
            for col in df.columns:
                if "cnpj" in col.lower() or "cpf" in col.lower():
                    df[col] = df[col].astype(str).str.zfill(14)
            df.to_sql("contratacao", conn, if_exists="append", index=False)
            progress.advance(sheet_task)
        progress.advance(file_task)

conn.commit()
console.log("Executando VACUUM para reduzir o tamanho do banco...")
conn.execute("VACUUM;")
conn.commit()
conn.close()
console.log("Carregamento da tabela Contratação concluído e VACUUM executado!")
