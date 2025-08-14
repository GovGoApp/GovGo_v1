import requests
import pandas as pd
import concurrent.futures
from rich.progress import Progress, BarColumn, TextColumn, TimeElapsedColumn, TimeRemainingColumn
import math

# Função para buscar PCA de um órgão
def fetch_pca(cnpjs, progress, task_id):
    resultados = []
    for cnpj in cnpjs:
        url = f"https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/pca/2025/consolidado"
        try:
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                dados = resp.json()
                dados["cnpj"] = cnpj
                resultados.append(dados)
        except Exception:
            pass
        progress.update(task_id, advance=1)
    return resultados

# Main
if __name__ == "__main__":
    orgaos = pd.read_csv(r"c:\Users\Haroldo Duraes\Desktop\PYTHON\Python Scripts\#GOvGO\python\DB\TABELAS\lista_orgaos.csv")
    cnpjs = orgaos["cnpj"].tolist()
    n_threads = 20
    chunk_size = math.ceil(len(cnpjs) / n_threads)
    grupos = [cnpjs[i*chunk_size:(i+1)*chunk_size] for i in range(n_threads)]

    for ano in range(2021, 2025):
        resultados = []
        def fetch_pca_ano(cnpjs, progress, task_id):
            resultados_local = []
            for cnpj in cnpjs:
                url = f"https://pncp.gov.br/api/pncp/v1/orgaos/{cnpj}/pca/{ano}/consolidado"
                try:
                    resp = requests.get(url, timeout=10)
                    if resp.status_code == 200:
                        dados = resp.json()
                        dados["cnpj"] = cnpj
                        dados["ano"] = ano
                        resultados_local.append(dados)
                except Exception:
                    pass
                progress.update(task_id, advance=1)
            return resultados_local

        progress = Progress(
            TextColumn(f"[bold white]Ano {ano} - {{task.description}}"),
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
            TimeElapsedColumn(),
            TimeRemainingColumn(),
        )

        with progress:
            with concurrent.futures.ThreadPoolExecutor(max_workers=n_threads) as executor:
                future_to_task = {}
                for i, grupo in enumerate(grupos):
                    task_id = progress.add_task(f"[cyan]Thread {i+1}", total=len(grupo))
                    future = executor.submit(fetch_pca_ano, grupo, progress, task_id)
                    future_to_task[future] = task_id

                for future in concurrent.futures.as_completed(future_to_task):
                    result = future.result()
                    resultados.extend(result)
                    progress.remove_task(future_to_task[future])

        pd.DataFrame(resultados).to_csv(f"pca_{ano}.csv", index=False, encoding="utf-8")
        print(f"Salvo em pca_{ano}.csv com {len(resultados)} PCAs.")
