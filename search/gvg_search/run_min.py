import sys
# Import directly from local module to avoid package resolution issues when running inside this folder
from GvG_Search_Function import gvg_search

if __name__ == "__main__":
    prompt = "Merenda escolar Nordeste"
    if len(sys.argv) > 1:
        prompt = " ".join(sys.argv[1:])

    # Safe defaults: keyword search + direct, no relevance assistant, no exports
    out = gvg_search(
        prompt=prompt,
        search=1,              # 1=semantic, 2=keyword, 3=hybrid
        approach=3,            # direct
        relevance=2,           # disable relevance assistant
        order=1,               # similarity
        max_results=10,
        top_cat=10,
        negation_emb=False,    # not used in keyword mode
        filter_expired=True,
        intelligent_toggle=False,
        export=("csv",),      # do not write files
        output_dir="resultados",
        debug=True,
        return_export_paths=False,
        return_raw=False,
    )

    # Print a compact summary
    print("--- gvg_search result ---")
    print({k: v for k, v in out.items() if k in ("confidence", "elapsed", "log_path")})
    print(f"results: {len(out.get('results', []))}")
    if out.get("results"):
        first = out["results"][0]
        print("first:", {
            "rank": first.get("rank"),
            "id": first.get("id"),
            "similarity": first.get("similarity"),
            "orgao": (first.get("details", {}) or {}).get("orgao_entidade_razao_social")
        })
