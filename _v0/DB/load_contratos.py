import os
import glob
import pandas as pd
import sqlite3
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn

console = Console()

BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
DB_PATH = BASE_PATH + "DB\\"
DB_FILE = DB_PATH + "pncp.db"
PATH_CONTRATOS = BASE_PATH + "CONTRATOS\\"

# Dicionário de mapeamento para a tabela contrato
contratos_mapping = {
    "numeroControlePncpCompra": "numeroControlePncpCompra",
    "anoContrato": "anoContrato",
    "numeroContratoEmpenho": "numeroContratoEmpenho",
    "dataAssinatura": "dataAssinatura",
    "dataVigenciaInicio": "dataVigenciaInicio",
    "dataVigenciaFim": "dataVigenciaFim",
    "niFornecedor": "niFornecedor",
    "tipoPessoa": "tipoPessoa",
    "sequencialContrato": "sequencialContrato",
    "informacaoComplementar": "informacaoComplementar",
    "processo": "processo",
    "nomeRazaoSocialFornecedor": "nomeRazaoSocialFornecedor",
    "numeroControlePNCP": "numeroControlePNCP",
    "numeroParcelas": "numeroParcelas",
    "numeroRetificacao": "numeroRetificacao",
    "objetoContrato": "objetoContrato",
    "valorInicial": "valorInicial",
    "valorParcela": "valorParcela",
    "valorGlobal": "valorGlobal",
    "dataAtualizacaoGlobal": "dataAtualizacaoGlobal",
    "usuarioNome": "usuarioNome",
    "tipoContrato.id": "tipoContrato_id",
    "tipoContrato.nome": "tipoContrato_nome",
    "orgaoEntidade.cnpj": "orgaoEntidade_cnpj",
    "orgaoEntidade.razaoSocial": "orgaoEntidade_razaosocial",
    "orgaoEntidade.poderId": "orgaoEntidade_poderId",
    "orgaoEntidade.esferaId": "orgaoEntidade_esferaId",
    "categoriaProcesso.id": "categoriaProcesso_id",
    "categoriaProcesso.nome": "categoriaProcesso_nome",
    "unidadeOrgao.ufNome": "unidadeOrgao_ufNome",
    "unidadeOrgao.codigoUnidade": "unidadeOrgao_codigoUnidade",
    "unidadeOrgao.nomeUnidade": "unidadeOrgao_nomeUnidade",
    "unidadeOrgao.ufSigla": "unidadeOrgao_ufSigla",
    "unidadeOrgao.municipioNome": "unidadeOrgao_municipioNome",
    "unidadeOrgao.codigoIbge": "unidadeOrgao_codigoIbge",
    "vigenciaAno": "vigenciaAno"
}

console.log("Iniciando o carregamento dos dados da tabela Contrato...")

conn = sqlite3.connect(DB_FILE)
files = glob.glob(os.path.join(PATH_CONTRATOS, "*.xlsx"))
console.log(f"{len(files)} arquivos encontrados em CONTRATOS.")

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
        sheet_task = progress.add_task(f"Aba(s) de {file_name}", total=len(sheets))
        for sheet in sheets:
            console.print(f"  [bold blue]Aba:[/bold blue] {sheet}")
            df = excel.parse(sheet)
            df = df.loc[:, ~df.columns.str.contains("^Unnamed")]
            if df.empty:
                progress.advance(sheet_task)
                continue
            df.columns = df.columns.str.strip()
            df.rename(columns=contratos_mapping, inplace=True)
            for col in df.columns:
                if "data" in col.lower():
                    df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d")
            for col in df.columns:
                if "cnpj" in col.lower() or "cpf" in col.lower():
                    df[col] = df[col].astype(str).str.zfill(14)
            df.to_sql("contrato", conn, if_exists="append", index=False)
            progress.advance(sheet_task)
        progress.advance(file_task)

conn.commit()
console.log("Executando VACUUM para reduzir o tamanho do banco...")
conn.execute("VACUUM;")
conn.commit()
conn.close()
console.log("Carregamento da tabela Contrato concluído e VACUUM executado!")
