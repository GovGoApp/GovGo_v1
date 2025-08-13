# GovGo V1 - Configuração de Modelos OpenAI
# Modelos atualizados conforme solicitado

"""
Configuração dos modelos OpenAI para o GovGo V1
Baseado nas especificações do Terminal_v9 e Prompt_v0 do V0
Atualizados para text-embedding-3-large e gpt-4o
"""

import os
from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class OpenAIConfig:
    """Configuração unificada dos modelos OpenAI"""
    
    # Modelos principais (atualizados)
    EMBEDDING_MODEL: str = "text-embedding-3-large"
    CHAT_MODEL: str = "gpt-4o"
    
    # Configurações de embeddings
    EMBEDDING_DIMENSIONS: int = 3072  # text-embedding-3-large
    EMBEDDING_BATCH_SIZE: int = 100
    EMBEDDING_ENCODING: str = "cl100k_base"
    
    # Configurações de chat
    CHAT_MAX_TOKENS: int = 4096
    CHAT_TEMPERATURE: float = 0.1
    CHAT_TOP_P: float = 1.0
    
    # Rate limiting
    REQUESTS_PER_MINUTE: int = 3000
    TOKENS_PER_MINUTE: int = 200000
    
    @classmethod
    def from_env(cls) -> 'OpenAIConfig':
        """Carrega configuração das variáveis de ambiente"""
        return cls(
            EMBEDDING_MODEL=os.getenv("OPENAI_MODEL_EMBEDDINGS", "text-embedding-3-large"),
            CHAT_MODEL=os.getenv("OPENAI_MODEL_CHAT", "gpt-4o"),
        )
    
    def get_assistants(self) -> Dict[str, str]:
        """Carrega todos os assistants do .env de forma organizada"""
        return {
            # Sistema de busca e relevância
            "search_flexible": os.getenv("OPENAI_ASSISTANT_FLEXIBLE", ""),
            "search_restrictive": os.getenv("OPENAI_ASSISTANT_RESTRICTIVE", ""),
            "search_preprocessing": os.getenv("OPENAI_ASSISTANT_PREPROCESSING", ""),
            "search_filter": os.getenv("OPENAI_ASSISTANT_SEARCH_FILTER", ""),
            
            # Sistema de relatórios
            "reports_v0": os.getenv("OPENAI_ASSISTANT_REPORTS_V0", ""),
            "reports_v1": os.getenv("OPENAI_ASSISTANT_REPORTS_V1", ""),
            "reports_v2": os.getenv("OPENAI_ASSISTANT_REPORTS_V2", ""),
            "reports_v3": os.getenv("OPENAI_ASSISTANT_REPORTS_V3", ""),
            "reports_v4": os.getenv("OPENAI_ASSISTANT_REPORTS_V4", ""),
            "reports_supabase": os.getenv("OPENAI_ASSISTANT_SUPABASE_REPORTS", ""),
            
            # Sistema de categorização
            "category_finder": os.getenv("OPENAI_ASSISTANT_CATEGORY_FINDER", ""),
            "category_validator": os.getenv("OPENAI_ASSISTANT_CATEGORY_VALIDATOR", ""),
            "items_classifier": os.getenv("OPENAI_ASSISTANT_ITEMS_CLASSIFIER", ""),
            
            # Sistema de análise e documentos
            "financial_analyzer": os.getenv("OPENAI_ASSISTANT_FINANCIAL_ANALYZER", ""),
            "pdf_processor_v0": os.getenv("OPENAI_ASSISTANT_PDF_PROCESSOR_V0", ""),
            "pdf_processor_v1": os.getenv("OPENAI_ASSISTANT_PDF_PROCESSOR_V1", ""),
        }
    
    def get_embedding_config(self) -> Dict[str, Any]:
        """Configuração para embeddings"""
        return {
            "model": self.EMBEDDING_MODEL,
            "dimensions": self.EMBEDDING_DIMENSIONS,
            "encoding_format": "float"
        }
    
    def get_chat_config(self) -> Dict[str, Any]:
        """Configuração para chat"""
        return {
            "model": self.CHAT_MODEL,
            "max_tokens": self.CHAT_MAX_TOKENS,
            "temperature": self.CHAT_TEMPERATURE,
            "top_p": self.CHAT_TOP_P
        }

# Configurações específicas para migração do V0
V0_COMPATIBILITY = {
    # Modelos do V0 (para comparação)
    "v0_embedding_model": "text-embedding-3-small",
    "v0_embedding_dimensions": 1536,
    "v0_chat_model": "gpt-4-turbo",
    
    # Mapeamento de dimensões para migração
    "dimension_mapping": {
        1536: 3072,  # V0 → V1
    }
}

# Prompts de relevância (do sistema V0)
RELEVANCE_PROMPTS = {
    "flexible": {
        "assistant_id": "asst_tfD5oQxSgoGhtqdKQHK9UwRi",
        "file": "relevance_pncp_v3.txt",
        "description": "Filtro suave via IA - mais resultados"
    },
    "restrictive": {
        "assistant_id": "asst_XmsefQEKbuVWu51uNST7kpYT", 
        "file": "relevance_pncp_v2.txt",
        "description": "Filtro rigoroso via IA - resultados precisos"
    }
}

# Configurações completas de assistants (V0) - APENAS PARA DOCUMENTAÇÃO
# Os valores reais vêm do .env
ASSISTANTS_DOCUMENTATION = {
    # Sistema de busca e relevância
    "search": {
        "flexible": "Filtro suave via IA - mais resultados (relevance_pncp_v3.txt)",
        "restrictive": "Filtro rigoroso via IA - resultados precisos (relevance_pncp_v2.txt)",
        "preprocessing": "Processamento inteligente de consultas (SUPABASE_SEARCH_v0.txt)",
        "filter": "Filtro de relevância secundário"
    },
    
    # Sistema de relatórios (múltiplas versões)
    "reports": {
        "pncp_sql_v0": "Assistente original completo",
        "pncp_sql_v1": "Versão com campos retirados",
        "pncp_sql_v2": "Versão com campos essenciais",
        "pncp_sql_v3": "Versão resumida",
        "pncp_sql_v4": "Versão com classificação de itens",
        "supabase": "Assistente especializado em Supabase SQL"
    },
    
    # Sistema de categorização
    "categorization": {
        "finder": "Busca e encontra categorias (GPT-3.5 Turbo)",
        "validator": "Valida categorias encontradas",
        "classifier": "Classifica itens individuais (MSOCIT_to_TEXT)"
    },
    
    # Sistema de análise e documentos
    "analysis": {
        "financial": "Análise financeira de contratos",
        "pdf_v0": "Processamento de PDFs V0 (RESUMEE_v0)",
        "pdf_v1": "Processamento de PDFs V1 (RESUMEE_v1)"
    }
}

def get_assistant_by_category(config: 'OpenAIConfig', category: str, assistant_type: str) -> Optional[str]:
    """
    Helper para buscar assistant específico por categoria
    
    Args:
        config: Instância do OpenAIConfig
        category: 'search', 'reports', 'categorization', 'analysis'
        assistant_type: tipo específico dentro da categoria
    
    Returns:
        ID do assistant ou None se não encontrado
    """
    assistants = config.get_assistants()
    key = f"{category}_{assistant_type}"
    return assistants.get(key)

# Configurações de custos (estimativas)
COST_CONFIG = {
    "text-embedding-3-large": {
        "cost_per_1k_tokens": 0.00013,  # USD
        "max_tokens_per_request": 8191
    },
    "gpt-4o": {
        "cost_per_1k_input_tokens": 0.005,  # USD
        "cost_per_1k_output_tokens": 0.015,  # USD
        "max_tokens": 128000
    }
}

def get_model_config() -> OpenAIConfig:
    """Função de conveniência para obter configuração"""
    return OpenAIConfig.from_env()

def validate_models() -> bool:
    """Valida se os modelos estão disponíveis"""
    config = get_model_config()
    
    # Lista de modelos válidos (atualizar conforme OpenAI)
    valid_embedding_models = [
        "text-embedding-3-large",
        "text-embedding-3-small", 
        "text-embedding-ada-002"
    ]
    
    valid_chat_models = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-4"
    ]
    
    embedding_valid = config.EMBEDDING_MODEL in valid_embedding_models
    chat_valid = config.CHAT_MODEL in valid_chat_models
    
    if not embedding_valid:
        print(f"⚠️  Modelo de embedding inválido: {config.EMBEDDING_MODEL}")
    
    if not chat_valid:
        print(f"⚠️  Modelo de chat inválido: {config.CHAT_MODEL}")
    
    return embedding_valid and chat_valid

if __name__ == "__main__":
    # Teste da configuração
    config = get_model_config()
    print("🤖 Configuração OpenAI V1:")
    print(f"   Embeddings: {config.EMBEDDING_MODEL} ({config.EMBEDDING_DIMENSIONS}D)")
    print(f"   Chat: {config.CHAT_MODEL}")
    
    # Teste dos assistants
    assistants = config.get_assistants()
    print(f"\n🔧 Assistants configurados: {len([a for a in assistants.values() if a])}")
    
    # Mostra alguns assistants principais
    key_assistants = {
        "Busca Flexível": assistants.get("search_flexible", "N/A"),
        "Busca Restritiva": assistants.get("search_restrictive", "N/A"),
        "Relatórios V0": assistants.get("reports_v0", "N/A"),
        "Categorização": assistants.get("category_finder", "N/A")
    }
    
    for name, assistant_id in key_assistants.items():
        status = "✅" if assistant_id and assistant_id != "N/A" else "❌"
        print(f"   {status} {name}: {assistant_id[:20]}..." if len(assistant_id) > 20 else f"   {status} {name}: {assistant_id}")
    
    if validate_models():
        print("\n✅ Modelos validados com sucesso!")
    else:
        print("\n❌ Problemas na validação dos modelos!")
