import os
import sys
import types
import importlib.util

# Caminho absoluto do módulo alvo
MODULE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '_v0', 'GvG', 'Search', 'Prompt_v2', 'GvG_Search_Function.py'))

def load_module():
    spec = importlib.util.spec_from_file_location('GvG_Search_Function', MODULE_PATH)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)  # type: ignore
    return mod


def test_gvg_search_basic(tmp_path):
    mod = load_module()

    # ---- Mocks leves ----
    def fake_extract_pos_neg_terms(q):
        parts = q.split('-')
        pos = parts[0].strip()
        neg = parts[1].strip() if len(parts) > 1 else ''
        return pos, neg

    def fake_semantic_search(q, limit=30, filter_expired=True, use_negation=True):
        return [
            {"id": 1, "similarity": 0.91, "details": {"unidadeorgao_nomeunidade": "UNIDADE A", "unidadeorgao_municipionome": "CidadeX", "unidadeorgao_ufsigla": "SP", "valortotalestimado": 10000, "dataencerramentoproposta": "2025-12-31"}},
            {"id": 2, "similarity": 0.82, "details": {"unidadeorgao_nomeunidade": "UNIDADE B", "unidadeorgao_municipionome": "CidadeY", "unidadeorgao_ufsigla": "RJ", "valortotalestimado": 5000, "dataencerramentoproposta": "2025-11-30"}},
        ][:limit], 0.87

    def fake_hybrid_search(q, limit=30, filter_expired=True, use_negation=True):
        res, conf = fake_semantic_search(q, limit, filter_expired, use_negation)
        return res, conf

    def fake_get_top_categories_for_query(query_text, top_n=10, use_negation=False, search_type=1, console=None):
        return [
            {"rank": 1, "codigo": "1234", "similarity_score": 0.77, "descricao": "Categoria Teste 1"},
            {"rank": 2, "codigo": "5678", "similarity_score": 0.66, "descricao": "Categoria Teste 2"},
        ][:top_n]

    def fake_category_filtered_search(query_text, search_type, top_categories, limit=30, filter_expired=True, use_negation=True, console=None):
        res, conf = fake_semantic_search(query_text, limit, filter_expired, use_negation)
        return res, conf, {"categories_used": len(top_categories)}

    def fake_get_intelligent_status():
        return {"intelligent_processing": False, "model": "mock"}

    def fake_get_relevance_filter_status():
        return {"level": 2}

    def fake_set_relevance_filter_level(level):
        return None

    def fake_toggle_intelligent_processing(value):
        return None

    # Aplicar mocks no módulo
    mod.extract_pos_neg_terms = fake_extract_pos_neg_terms
    mod.semantic_search = fake_semantic_search
    mod.hybrid_search = fake_hybrid_search
    mod.get_top_categories_for_query = fake_get_top_categories_for_query
    mod.categories_category_filtered_search = fake_category_filtered_search
    mod.get_intelligent_status = fake_get_intelligent_status
    mod.get_relevance_filter_status = fake_get_relevance_filter_status
    mod.set_relevance_filter_level = fake_set_relevance_filter_level
    mod.toggle_intelligent_processing = fake_toggle_intelligent_processing

    # Execução: abordagem 3 (Filtro) + híbrida (3) + export json
    result = mod.gvg_search(
        prompt="compra de computadores -usados",
        search=3,
        approach=3,
        relevance=2,
        order=1,
        max_results=5,
        top_cat=5,
        export=("json",),
        output_dir=str(tmp_path),
        debug=False,
    )

    # Asserções básicas
    assert isinstance(result, dict)
    assert 'results' in result and 'categories' in result
    assert len(result['results']) == 2
    assert result['results'][0]['rank'] == 1
    assert result['results'][1]['rank'] == 2
    assert result['categories'][0]['codigo'] == '1234'
    assert 'exports' in result and 'json' in result['exports']
    assert os.path.isfile(result['exports']['json'])


def test_gvg_search_no_export(tmp_path):
    mod = load_module()

    # Mocks mínimos
    mod.extract_pos_neg_terms = lambda q: (q, '')
    mod.semantic_search = lambda q, limit=30, filter_expired=True, use_negation=True: ([{"id": 9, "similarity": 0.5, "details": {}}], 0.5)
    mod.get_intelligent_status = lambda: {"intelligent_processing": False}
    mod.get_relevance_filter_status = lambda: {"level": 2}
    mod.set_relevance_filter_level = lambda level: None
    mod.toggle_intelligent_processing = lambda v: None

    res = mod.gvg_search(
        prompt="teste simples",
        search=1,
        approach=1,
        export=None,
        output_dir=str(tmp_path),
        debug=False,
    )
    assert res['exports'] == {}
    assert res['results'][0]['rank'] == 1
