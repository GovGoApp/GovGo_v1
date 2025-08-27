"""
Script mínimo para testar gvg_search (GvG_Search_Function)
Executa uma busca simples sem exportação e imprime 3 primeiros resultados.
Evita chamadas de IA substituindo SearchQueryProcessor por um stub local.
"""

import os
import GvG_Search_Function as GSF
import GvG_Search_Prompt as GSP
import gvg_search_core as CORE


# Substitui o processamento inteligente por um stub para evitar rede
class _StubProcessor:
    def process_query(self, prompt: str):
        return {"search_terms": "", "negative_terms": "", "sql_conditions": []}

# Importante: o perform_search do Function reutiliza o do Prompt,
# então precisamos substituir no módulo do Prompt.
GSP.SearchQueryProcessor = _StubProcessor
CORE.SearchQueryProcessor = _StubProcessor
GSF.SearchQueryProcessor = _StubProcessor


def main():
    resp = GSF.gvg_search(
        prompt="alimentação escolar no nordeste tirando capitais com data de encerramento antes de setembro de 2025 -- kit lanche",
        search=1,            # Semântica
        approach=3,          # Filtro
        relevance=2,         # Flexível
        order=1,             # Similaridade desc
        max_results=30,
        top_cat=20,
        export=("json",),   # sem exportação
        debug=True,
        return_export_paths=False,
        return_raw=True,
    )
    results = resp.get("results", [])
    print(f"Resultados: {len(results)}")
    for r in results[:3]:
        d = r.get("details", {})
        unidade = (
            d.get("unidadeorgao_nomeunidade")
            or d.get("unidadeOrgao_nomeUnidade")
            or d.get("orgaoentidade_razaosocial")
            or "N/A"
        )
        print(f"#{r.get('rank')}: sim={r.get('similarity', 0):.4f} - {unidade}")

    # Exibir TODO o log
    log_path = resp.get("log_path")
    if log_path and os.path.exists(log_path):
        print("\n===== LOG COMPLETO =====")
        with open(log_path, "r", encoding="utf-8", errors="replace") as f:
            print(f.read())
    else:
        print("\n[AVISO] Log não encontrado.")
    log_path = resp.get("log_path")
    if log_path:
        print(f"LOG: {log_path}")
        try:
            with open(log_path, "r", encoding="utf-8") as f:
                lines = [next(f) for _ in range(15)]
            print("--- INÍCIO DO LOG ---")
            for line in lines:
                print(line.rstrip())
            print("--- FIM DO TRECHO ---")
        except Exception as e:
            print(f"Falha ao ler LOG: {e}")


if __name__ == "__main__":
    main()
