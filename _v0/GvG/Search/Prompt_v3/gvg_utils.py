"""
gvg_utils.py
Módulo unificado e otimizado de utilitários GvG
Importa seletivamente apenas as funções realmente utilizadas pelo Terminal_v9
"""

# Importações seletivas dos módulos especializados
# (Formatters migrados para gvg_preprocessing – remoção de gvg_formatters.py)
from gvg_preprocessing import (
    format_currency,
    format_date,
    decode_poder,
    decode_esfera,
)

from gvg_ai_utils import (
    get_embedding,
    get_negation_embedding,
    extract_pos_neg_terms,
    generate_keywords,
    calculate_confidence
)

from gvg_database import (
    create_connection,
    create_engine_connection,
    fetch_documentos
)

from gvg_search_core import (
    # Funções principais (com aliases)
    semantic_search,
    keyword_search,
    hybrid_search,
    
    # Funções de controle
    toggle_intelligent_processing,
    toggle_intelligent_debug,
    get_intelligent_status
)

from gvg_preprocessing import (
    SearchQueryProcessor,
    process_search_query
)

# Importar preprocessor para compatibilidade
import gvg_preprocessing as preprocessor

# Configurações globais (reexportadas para compatibilidade)
MAX_RESULTS = 30
MIN_RESULTS = 5
SEMANTIC_WEIGHT = 0.75
DEFAULT_FILTER_EXPIRED = True
DEFAULT_USE_NEGATION = True

# Sistema de filtro de relevância (placeholder - não utilizado efetivamente)
RELEVANCE_FILTER_LEVEL = 1

def set_relevance_filter_level(level):
    """
    Define nível do filtro de relevância (compatibilidade)
    
    Args:
        level (int): Nível do filtro (1-3)
    """
    global RELEVANCE_FILTER_LEVEL
    RELEVANCE_FILTER_LEVEL = level
    print(f"🎯 Filtro de Relevância definido para nível {level}")

def get_relevance_filter_status():
    """
    Retorna status atual do filtro de relevância
    
    Returns:
        dict: Status do filtro
    """
    level_names = {1: "Desabilitado", 2: "Flexível", 3: "Restritivo"}
    return {
        'level': RELEVANCE_FILTER_LEVEL,
        'name': level_names.get(RELEVANCE_FILTER_LEVEL, "Desconhecido"),
        'active': RELEVANCE_FILTER_LEVEL > 1
    }

# Lista de todas as funções disponíveis (para referência)
__all__ = [
    # Formatação
    'format_currency',
    'format_date',
    'decode_poder', 
    'decode_esfera',
    
    # IA/Embeddings
    'get_embedding',
    'get_negation_embedding',
    'extract_pos_neg_terms',
    'generate_keywords',
    'calculate_confidence',
    
    # Banco de dados
    'create_connection',
    'create_engine_connection', 
    'fetch_documentos',
    
    # Busca principal
    'semantic_search',
    'keyword_search',
    'hybrid_search',
    
    # Controle sistema
    'toggle_intelligent_processing',
    'toggle_intelligent_debug',
    'get_intelligent_status',
    'set_relevance_filter_level',
    'get_relevance_filter_status',
    
    # Preprocessamento
    'SearchQueryProcessor',
    'process_search_query',
    'preprocessor',
    
    # Constantes
    'MAX_RESULTS',
    'MIN_RESULTS', 
    'SEMANTIC_WEIGHT',
    'DEFAULT_FILTER_EXPIRED',
    'DEFAULT_USE_NEGATION',
    'RELEVANCE_FILTER_LEVEL'
]

# Informações do módulo
__version__ = "1.0.0"
__description__ = "Módulo unificado e otimizado de utilitários GvG"

def get_module_info():
    """
    Retorna informações sobre o módulo otimizado
    
    Returns:
        dict: Informações do módulo
    """
    return {
        'version': __version__,
        'description': __description__,
        'total_functions': len(__all__),
        'specialized_modules': [
            'gvg_formatters',
            'gvg_ai_utils', 
            'gvg_database',
            'gvg_search_core',
            'gvg_preprocessing'
        ],
        'optimization': 'Importações seletivas - apenas funções utilizadas'
    }
