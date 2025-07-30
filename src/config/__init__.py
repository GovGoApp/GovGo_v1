# GovGo V1 - Módulo de Configuração

"""
Módulo de configuração do GovGo V1
Integração das configurações do Terminal_v9 e Prompt_v0 do V0
Modelos atualizados: text-embedding-3-large e gpt-4o
"""

from .settings import (
    GovGoV1Config,
    DatabaseConfig,
    PathConfig,
    PNCPConfig,
    SearchConfig,
    RelevanceConfig,
    ProcessingConfig,
    UIConfig,
    DocumentConfig,
    LoggingConfig,
    MigrationConfig,
    get_config,
    reload_config,
    validate_config
)

from .models import (
    OpenAIConfig,
    get_model_config,
    validate_models,
    V0_COMPATIBILITY,
    RELEVANCE_PROMPTS,
    COST_CONFIG,
    ASSISTANTS_DOCUMENTATION,
    get_assistant_by_category
)

__all__ = [
    # Configuração principal
    "GovGoV1Config",
    "get_config",
    "reload_config", 
    "validate_config",
    
    # Subconfiguração
    "DatabaseConfig",
    "PathConfig",
    "PNCPConfig",
    "SearchConfig",
    "RelevanceConfig",
    "ProcessingConfig",
    "UIConfig",
    "DocumentConfig",
    "LoggingConfig",
    "MigrationConfig",
    
    # Modelos OpenAI
    "OpenAIConfig",
    "get_model_config",
    "validate_models",
    
    # Constantes
    "V0_COMPATIBILITY",
    "RELEVANCE_PROMPTS", 
    "COST_CONFIG",
    "ASSISTANTS_DOCUMENTATION",
    
    # Funções utilitárias
    "get_assistant_by_category"
]

# Versão do módulo
__version__ = "1.0.0"

# Configuração padrão (lazy loading)
_default_config = None

def setup_config() -> GovGoV1Config:
    """
    Setup inicial da configuração
    Baseado nas configurações do Terminal_v9 e Prompt_v0
    """
    global _default_config
    
    if _default_config is None:
        print("🏛️ Inicializando GovGo V1...")
        print("📋 Carregando configurações do Terminal_v9 e Prompt_v0...")
        
        _default_config = get_config()
        
        # Validação
        if validate_config():
            print("✅ Configuração V1 carregada com sucesso!")
            
            # Resumo das configurações principais
            summary = _default_config.get_summary()
            print(f"🤖 Modelos: {summary['openai_models']['embeddings']} + {summary['openai_models']['chat']}")
            print(f"🗄️  Database: {summary['database']['host']}:{summary['database']['port']}")
            print(f"🔧 Features: V0={summary['features']['v0_compatibility']}, UI={summary['features']['rich_ui']}")
        else:
            print("❌ Erros na configuração! Verifique as variáveis de ambiente.")
    
    return _default_config

def quick_setup() -> bool:
    """Setup rápido para testes"""
    try:
        config = setup_config()
        return len(config.validate()) == 0
    except Exception as e:
        print(f"❌ Erro no setup: {e}")
        return False

# Convenience functions para acesso rápido às configurações
def get_openai_config() -> OpenAIConfig:
    """Acesso rápido à configuração OpenAI"""
    return get_config().openai

def get_database_config() -> DatabaseConfig:
    """Acesso rápido à configuração do banco"""
    return get_config().database

def get_search_config() -> SearchConfig:
    """Acesso rápido à configuração de busca"""
    return get_config().search

def get_paths_config() -> PathConfig:
    """Acesso rápido à configuração de paths"""
    return get_config().paths

def is_v0_compatible() -> bool:
    """Verifica se a compatibilidade V0 está habilitada"""
    return get_config().migration.enable_v0_compatibility

def get_relevance_system() -> RelevanceConfig:
    """Acesso rápido ao sistema de relevância"""
    return get_config().relevance
