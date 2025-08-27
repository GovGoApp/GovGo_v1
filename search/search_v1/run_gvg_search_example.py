"""Exemplo mínimo de uso da função gvg_search.
Execute diretamente este arquivo para fazer uma busca rápida.
"""

from search.search_v1.GvG_Search_Function_v0 import gvg_search


def main():
    resultado = gvg_search(
        prompt="serviço merenda escolar -- agricultura familiar",
        search=1,       # 1=Semântica (default)
        approach=3,     # 3=Filtro por categorias (default)
        relevance=1,    # 2=Flexível (default)
        order=1,        # 1=Similaridade (default)
        export=None,    # Sem exportação de arquivos
        debug=True     # Coloque True para ver progresso se Rich instalado
    )

    print(f"Total de resultados: {len(resultado['results'])}")
    print(f"Confiança média: {resultado['confidence']:.4f}")
    print("Top 3 resultados:")
    for r in resultado['results'][:3]:
        details = r.get('details', {})
        unidade = details.get('unidadeorgao_nomeunidade') or details.get('unidadeOrgao_nomeUnidade') or 'N/A'
        print(f"  #{r.get('rank')} | sim={r.get('similarity'):.4f} | {unidade}")


if __name__ == "__main__":
    main()
