"""
GovGo V1 - Configurações do Sistema
===================================
Carrega todas as configurações do arquivo .env
Remove valores hardcoded - tudo vem do ambiente
"""

import os
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import Optional

# Carregar variáveis do .env
load_dotenv()

@dataclass
class SupabaseConfig:
    """Configurações do Supabase V1 (nova base)"""
    url: str
    key: str
    db_url: str
    user: str
    password: str
    host: str
    port: int
    database: str

@dataclass
class SupabaseV0Config:
    """Configurações do Supabase V0 (base existente)"""
    url: str
    key: str
    db_url: str
    user: str
    password: str
    host: str
    port: int
    database: str

@dataclass
class OpenAIConfig:
    """Configurações da OpenAI"""
    api_key: str
    model_embeddings: str
    model_chat: str
    
    # Assistants
    assistant_flexible: str
    assistant_restrictive: str
    assistant_preprocessing: str
    assistant_search_filter: str
    assistant_reports_v0: str
    assistant_reports_v1: str
    assistant_reports_v2: str
    assistant_reports_v3: str
    assistant_reports_v4: str
    assistant_supabase_reports: str
    assistant_category_finder: str
    assistant_category_validator: str
    assistant_items_classifier: str
    assistant_financial_analyzer: str
    assistant_pdf_processor_v0: str
    assistant_pdf_processor_v1: str

@dataclass
class PNCPConfig:
    """Configurações da API PNCP"""
    base_url: str
    token: Optional[str]
    timeout: int

@dataclass
class PathsConfig:
    """Configurações de caminhos"""
    base_path: str
    results_path: str
    files_path: str
    temp_path: str
    v0_base_path: str
    v0_results_path: str
    v0_files_path: str
    v0_sqlite_path: str
    v0_categories_path: str

@dataclass
class ProcessingConfig:
    """Configurações de processamento"""
    batch_size: int
    max_workers: int
    chunk_size: int
    cache_embeddings: bool
    search_max_results: int
    search_similarity_threshold: float
    search_enable_hybrid: bool
    search_enable_fts: bool

@dataclass
class RelevanceConfig:
    """Configurações do sistema de relevância"""
    system_enabled: bool
    default_level: int
    prompts_path: str

@dataclass
class LoggingConfig:
    """Configurações de logging"""
    level: str
    to_file: bool
    file_path: str

@dataclass
class MigrationConfig:
    """Configurações de migração"""
    enable_v0_compatibility: bool

@dataclass
class DevelopmentConfig:
    """Configurações de desenvolvimento"""
    debug: bool
    environment: str
    interface_mode: str
    enable_rich_ui: bool
    enable_docling: bool
    enable_markitdown: bool
    document_analysis_enabled: bool

class Config:
    """Classe principal de configuração - carrega tudo do .env"""
    
    def __init__(self):
        # Supabase V1 (nova base)
        self.supabase = SupabaseConfig(
            url=os.getenv("SUPABASE_V1_URL", ""),
            key=os.getenv("SUPABASE_V1_KEY", ""),
            db_url=os.getenv("SUPABASE_V1_DB_URL", ""),
            user=os.getenv("SUPABASE_USER", ""),
            password=os.getenv("SUPABASE_PASSWORD", ""),
            host=os.getenv("SUPABASE_HOST", ""),
            port=int(os.getenv("SUPABASE_PORT", "5432")),
            database=os.getenv("SUPABASE_DBNAME", "postgres")
        )
        
        # Supabase V0 (base existente)
        self.supabase_v0 = SupabaseV0Config(
            url=os.getenv("SUPABASE_URL", ""),
            key=os.getenv("SUPABASE_KEY", ""),
            db_url=os.getenv("SUPABASE_DB_URL", ""),
            user=os.getenv("SUPABASE_V0_USER", ""),
            password=os.getenv("SUPABASE_V0_PASSWORD", ""),
            host=os.getenv("SUPABASE_V0_HOST", ""),
            port=int(os.getenv("SUPABASE_V0_PORT", "5432")),
            database=os.getenv("SUPABASE_V0_DBNAME", "postgres")
        )
        
        # OpenAI
        self.openai = OpenAIConfig(
            api_key=os.getenv("OPENAI_API_KEY", ""),
            model_embeddings=os.getenv("OPENAI_MODEL_EMBEDDINGS", "text-embedding-3-large"),
            model_chat=os.getenv("OPENAI_MODEL_CHAT", "gpt-4o"),
            assistant_flexible=os.getenv("OPENAI_ASSISTANT_FLEXIBLE", ""),
            assistant_restrictive=os.getenv("OPENAI_ASSISTANT_RESTRICTIVE", ""),
            assistant_preprocessing=os.getenv("OPENAI_ASSISTANT_PREPROCESSING", ""),
            assistant_search_filter=os.getenv("OPENAI_ASSISTANT_SEARCH_FILTER", ""),
            assistant_reports_v0=os.getenv("OPENAI_ASSISTANT_REPORTS_V0", ""),
            assistant_reports_v1=os.getenv("OPENAI_ASSISTANT_REPORTS_V1", ""),
            assistant_reports_v2=os.getenv("OPENAI_ASSISTANT_REPORTS_V2", ""),
            assistant_reports_v3=os.getenv("OPENAI_ASSISTANT_REPORTS_V3", ""),
            assistant_reports_v4=os.getenv("OPENAI_ASSISTANT_REPORTS_V4", ""),
            assistant_supabase_reports=os.getenv("OPENAI_ASSISTANT_SUPABASE_REPORTS", ""),
            assistant_category_finder=os.getenv("OPENAI_ASSISTANT_CATEGORY_FINDER", ""),
            assistant_category_validator=os.getenv("OPENAI_ASSISTANT_CATEGORY_VALIDATOR", ""),
            assistant_items_classifier=os.getenv("OPENAI_ASSISTANT_ITEMS_CLASSIFIER", ""),
            assistant_financial_analyzer=os.getenv("OPENAI_ASSISTANT_FINANCIAL_ANALYZER", ""),
            assistant_pdf_processor_v0=os.getenv("OPENAI_ASSISTANT_PDF_PROCESSOR_V0", ""),
            assistant_pdf_processor_v1=os.getenv("OPENAI_ASSISTANT_PDF_PROCESSOR_V1", "")
        )
        
        # PNCP
        self.pncp = PNCPConfig(
            base_url=os.getenv("PNCP_BASE_URL", "https://pncp.gov.br/api/pncp/v1"),
            token=os.getenv("PNCP_TOKEN"),
            timeout=int(os.getenv("PNCP_TIMEOUT", "30"))
        )
        
        # Paths
        self.paths = PathsConfig(
            base_path=os.getenv("BASE_PATH", ""),
            results_path=os.getenv("RESULTS_PATH", ""),
            files_path=os.getenv("FILES_PATH", ""),
            temp_path=os.getenv("TEMP_PATH", ""),
            v0_base_path=os.getenv("V0_BASE_PATH", ""),
            v0_results_path=os.getenv("V0_RESULTS_PATH", ""),
            v0_files_path=os.getenv("V0_FILES_PATH", ""),
            v0_sqlite_path=os.getenv("V0_SQLITE_PATH", ""),
            v0_categories_path=os.getenv("V0_CATEGORIES_PATH", "")
        )
        
        # Processing
        self.processing = ProcessingConfig(
            batch_size=int(os.getenv("BATCH_SIZE", "100")),
            max_workers=int(os.getenv("MAX_WORKERS", "4")),
            chunk_size=int(os.getenv("CHUNK_SIZE", "1000")),
            cache_embeddings=os.getenv("CACHE_EMBEDDINGS", "true").lower() == "true",
            search_max_results=int(os.getenv("SEARCH_MAX_RESULTS", "50")),
            search_similarity_threshold=float(os.getenv("SEARCH_SIMILARITY_THRESHOLD", "0.7")),
            search_enable_hybrid=os.getenv("SEARCH_ENABLE_HYBRID", "true").lower() == "true",
            search_enable_fts=os.getenv("SEARCH_ENABLE_FTS", "true").lower() == "true"
        )
        
        # Relevance
        self.relevance = RelevanceConfig(
            system_enabled=os.getenv("RELEVANCE_SYSTEM_ENABLED", "true").lower() == "true",
            default_level=int(os.getenv("RELEVANCE_DEFAULT_LEVEL", "2")),
            prompts_path=os.getenv("RELEVANCE_PROMPTS_PATH", "prompts/relevance/")
        )
        
        # Logging
        self.logging = LoggingConfig(
            level=os.getenv("LOG_LEVEL", "INFO"),
            to_file=os.getenv("LOG_TO_FILE", "true").lower() == "true",
            file_path=os.getenv("LOG_FILE_PATH", "logs/govgo_v1.log")
        )
        
        # Migration
        self.migration = MigrationConfig(
            enable_v0_compatibility=os.getenv("ENABLE_V0_COMPATIBILITY", "true").lower() == "true"
        )
        
        # Development
        self.development = DevelopmentConfig(
            debug=os.getenv("DEBUG", "false").lower() == "true",
            environment=os.getenv("ENVIRONMENT", "production"),
            interface_mode=os.getenv("INTERFACE_MODE", "terminal"),
            enable_rich_ui=os.getenv("ENABLE_RICH_UI", "true").lower() == "true",
            enable_docling=os.getenv("ENABLE_DOCLING", "true").lower() == "true",
            enable_markitdown=os.getenv("ENABLE_MARKITDOWN", "true").lower() == "true",
            document_analysis_enabled=os.getenv("DOCUMENT_ANALYSIS_ENABLED", "true").lower() == "true"
        )

# Instância global da configuração
config = Config()

# Aliases para compatibilidade com os scripts existentes
supabase_host = config.supabase.host
supabase_database = config.supabase.database
supabase_user = config.supabase.user
supabase_password = config.supabase.password
supabase_port = config.supabase.port
