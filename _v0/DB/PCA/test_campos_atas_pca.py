import requests
import pandas as pd
from rich.console import Console
from rich.table import Table

console = Console()

# Teste de endpoint ATAS
url_atas = "https://pncp.gov.br/api/consulta/v1/atas"
params_atas = {
    "dataInicial": "20250301",
    "dataFinal": "20250331",
    "pagina": 1,
    "tamanhoPagina": 10
}
resp_atas = requests.get(url_atas, params=params_atas)
if resp_atas.status_code == 200:
    data_atas = resp_atas.json().get("data", [])
    if data_atas:
        df_atas = pd.json_normalize(data_atas)
        console.print("[bold green]Campos encontrados em ATAS:")
        for col in df_atas.columns:
            console.print(f"- {col}")
    else:
        console.print("[yellow]Nenhum dado encontrado para ATAS no período informado.")
else:
    console.print(f"[red]Erro ao consultar ATAS: {resp_atas.status_code} - {resp_atas.text}")

# Teste de endpoint PCA
url_pca = "https://pncp.gov.br/api/consulta/v1/pca"
params_pca = {
    "ano": "2025",
    "pagina": 1,
    "tamanhoPagina": 10
}
resp_pca = requests.get(url_pca, params=params_pca)
if resp_pca.status_code == 200:
    data_pca = resp_pca.json().get("data", [])
    if data_pca:
        df_pca = pd.json_normalize(data_pca)
        console.print("\n[bold green]Campos encontrados em PCA:")
        for col in df_pca.columns:
            console.print(f"- {col}")
    else:
        console.print("[yellow]Nenhum dado encontrado para PCA no ano informado.")
else:
    console.print(f"[red]Erro ao consultar PCA: {resp_pca.status_code} - {resp_pca.text}")
