import os
import glob
import pandas as pd
import sqlite3
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn

console = Console()

BASE_PATH = "C:\\Users\\Haroldo Duraes\\Desktop\\GOvGO\\v0\\#DATA\\PNCP\\"
DB_PATH = BASE_PATH + "DB\\"
DB_FILE = DB_PATH + "pncp_v2.db"
PATH_ITENS = BASE_PATH + "ITENS\\"

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

console.log("Iniciando o carregamento dos dados da tabela Item_Contratação...")

conn = sqlite3.connect(DB_FILE)
files = glob.glob(os.path.join(PATH_ITENS, "*.xlsx"))
console.log(f"{len(files)} arquivos encontrados em ITENS.")

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
            df.rename(columns=itens_mapping, inplace=True)
            for col in df.columns:
                if "data" in col.lower():
                    df[col] = pd.to_datetime(df[col], errors="coerce").dt.strftime("%Y-%m-%d")
            for col in df.columns:
                if "cnpj" in col.lower() or "cpf" in col.lower():
                    df[col] = df[col].astype(str).str.zfill(14)
            df.to_sql("item_contratacao", conn, if_exists="append", index=False)
            progress.advance(sheet_task)
        progress.advance(file_task)

conn.commit()
console.log("Executando VACUUM para reduzir o tamanho do banco...")
conn.execute("VACUUM;")
conn.commit()
conn.close()
console.log("Carregamento da tabela Item_Contratação concluído e VACUUM executado!")
