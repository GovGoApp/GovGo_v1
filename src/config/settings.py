# GovGo V1 - Configurações Principais
# Baseado nas configurações do Terminal_v9 e Prompt_v0 do V0

"""
Configurações unificadas do GovGo V1
Migração e expansão das configurações do sistema V0
"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from .models import OpenAIConfig, get_model_config

@dataclass
class DatabaseConfig:
    """Configuração do banco de dados Supabase"""
    
    # Configurações baseadas no supabase_v0.env do V0
    url: str = field(default_factory=lambda: os.getenv("SUPABASE_URL", ""))
    key: str = field(default_factory=lambda: os.getenv("SUPABASE_KEY", ""))
    db_url: str = field(default_factory=lambda: os.getenv("SUPABASE_DB_URL", ""))
    
    # Configurações detalhadas (compatibilidade V0)
    user: str = field(default_factory=lambda: os.getenv("SUPABASE_USER", "postgres.bzgtlersjbetwilubnng"))
    password: str = field(default_factory=lambda: os.getenv("SUPABASE_PASSWORD", "GovGo2025!!"))
    host: str = field(default_factory=lambda: os.getenv("SUPABASE_HOST", "aws-0-sa-east-1.pooler.supabase.com"))
    port: int = field(default_factory=lambda: int(os.getenv("SUPABASE_PORT", "6543")))
    dbname: str = field(default_factory=lambda: os.getenv("SUPABASE_DBNAME", "postgres"))
    
    # Pool settings
    max_connections: int = 20
    min_connections: int = 1
    
    def get_connection_string(self) -> str:
        """Retorna string de conexão PostgreSQL"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.dbname}"

@dataclass
class PathConfig:
    """Configuração de diretórios - baseada no dir.env do V0"""
    
    # Paths V1
    base_path: Path = field(default_factory=lambda: Path(os.getenv("BASE_PATH", "data/")))
    results_path: Path = field(default_factory=lambda: Path(os.getenv("RESULTS_PATH", "data/reports/")))
    files_path: Path = field(default_factory=lambda: Path(os.getenv("FILES_PATH", "data/files/")))
    temp_path: Path = field(default_factory=lambda: Path(os.getenv("TEMP_PATH", "data/temp/")))
    
    # Paths V0 (para compatibilidade)
    v0_base_path: Path = field(default_factory=lambda: Path(os.getenv("V0_BASE_PATH", 
        "C:/Users/Haroldo Duraes/Desktop/GOvGO/v0/#DATA/PNCP/GvG/Terminal/")))
    v0_results_path: Path = field(default_factory=lambda: Path(os.getenv("V0_RESULTS_PATH", 
        "C:/Users/Haroldo Duraes/Desktop/GOvGO/v0/#DATA/PNCP/GvG/Terminal/Relatórios/")))
    v0_files_path: Path = field(default_factory=lambda: Path(os.getenv("V0_FILES_PATH", 
        "C:/Users/Haroldo Duraes/Desktop/GOvGO/v0/#DATA/PNCP/GvG/Terminal/Arquivos/")))
    
    # Migração V0
    v0_sqlite_path: Path = field(default_factory=lambda: Path(os.getenv("V0_SQLITE_PATH", 
        "C:/Users/Haroldo Duraes/Desktop/GOvGO/v0/#DATA/PNCP/DB/govgo.db")))
    v0_categories_path: Path = field(default_factory=lambda: Path(os.getenv("V0_CATEGORIES_PATH", 
        "C:/Users/Haroldo Duraes/Desktop/GOvGO/v0/#DATA/PNCP/DB/categorias_governamentais.db")))
    
    def create_directories(self):
        """Cria diretórios necessários"""
        for path in [self.base_path, self.results_path, self.files_path, self.temp_path]:
            path.mkdir(parents=True, exist_ok=True)

@dataclass
class PNCPConfig:
    """Configuração da API PNCP"""
    
    base_url: str = field(default_factory=lambda: os.getenv("PNCP_BASE_URL", "https://pncp.gov.br/api/pncp/v1"))
    token: Optional[str] = field(default_factory=lambda: os.getenv("PNCP_TOKEN"))
    timeout: int = field(default_factory=lambda: int(os.getenv("PNCP_TIMEOUT", "30")))
    
    # Rate limiting
    requests_per_second: int = 5
    max_retries: int = 3
    backoff_factor: float = 1.0

@dataclass
class SearchConfig:
    """Configuração do sistema de busca - baseado no Terminal_v9"""
    
    # Configurações básicas
    max_results: int = field(default_factory=lambda: int(os.getenv("SEARCH_MAX_RESULTS", "50")))
    similarity_threshold: float = field(default_factory=lambda: float(os.getenv("SEARCH_SIMILARITY_THRESHOLD", "0.7")))
    
    # Funcionalidades
    enable_hybrid: bool = field(default_factory=lambda: os.getenv("SEARCH_ENABLE_HYBRID", "true").lower() == "true")
    enable_fts: bool = field(default_factory=lambda: os.getenv("SEARCH_ENABLE_FTS", "true").lower() == "true")
    
    # Cache
    cache_embeddings: bool = field(default_factory=lambda: os.getenv("CACHE_EMBEDDINGS", "true").lower() == "true")
    cache_ttl: int = 3600  # 1 hora

@dataclass
class RelevanceConfig:
    """Sistema de relevância do V0 - 3 níveis"""
    
    enabled: bool = field(default_factory=lambda: os.getenv("RELEVANCE_SYSTEM_ENABLED", "true").lower() == "true")
    default_level: int = field(default_factory=lambda: int(os.getenv("RELEVANCE_DEFAULT_LEVEL", "2")))
    prompts_path: Path = field(default_factory=lambda: Path(os.getenv("RELEVANCE_PROMPTS_PATH", "prompts/relevance/")))
    
    # Assistants do V0
    assistant_flexible: str = field(default_factory=lambda: os.getenv("OPENAI_ASSISTANT_FLEXIBLE", "asst_tfD5oQxSgoGhtqdKQHK9UwRi"))
    assistant_restrictive: str = field(default_factory=lambda: os.getenv("OPENAI_ASSISTANT_RESTRICTIVE", "asst_XmsefQEKbuVWu51uNST7kpYT"))

@dataclass
class ProcessingConfig:
    """Configuração de processamento"""
    
    batch_size: int = field(default_factory=lambda: int(os.getenv("BATCH_SIZE", "100")))
    max_workers: int = field(default_factory=lambda: int(os.getenv("MAX_WORKERS", "4")))
    chunk_size: int = field(default_factory=lambda: int(os.getenv("CHUNK_SIZE", "1000")))
    
    # Timeouts
    embedding_timeout: int = 30
    processing_timeout: int = 300

@dataclass
class UIConfig:
    """Configuração da interface - baseada no Terminal_v9"""
    
    interface_mode: str = field(default_factory=lambda: os.getenv("INTERFACE_MODE", "terminal"))  # terminal, prompt, api
    enable_rich_ui: bool = field(default_factory=lambda: os.getenv("ENABLE_RICH_UI", "true").lower() == "true")
    
    # Configurações do Rich UI
    console_width: Optional[int] = None
    show_progress: bool = True
    show_timestamps: bool = True

@dataclass
class DocumentConfig:
    """Configuração para processamento de documentos - do V0"""
    
    enable_docling: bool = field(default_factory=lambda: os.getenv("ENABLE_DOCLING", "true").lower() == "true")
    enable_markitdown: bool = field(default_factory=lambda: os.getenv("ENABLE_MARKITDOWN", "true").lower() == "true")
    analysis_enabled: bool = field(default_factory=lambda: os.getenv("DOCUMENT_ANALYSIS_ENABLED", "true").lower() == "true")
    
    # Formatos suportados
    supported_formats: List[str] = field(default_factory=lambda: ['.pdf', '.doc', '.docx', '.txt', '.zip'])
    max_file_size: int = 50 * 1024 * 1024  # 50MB

@dataclass
class LoggingConfig:
    """Configuração de logging"""
    
    level: str = field(default_factory=lambda: os.getenv("LOG_LEVEL", "INFO"))
    to_file: bool = field(default_factory=lambda: os.getenv("LOG_TO_FILE", "true").lower() == "true")
    file_path: Path = field(default_factory=lambda: Path(os.getenv("LOG_FILE_PATH", "logs/govgo_v1.log")))
    
    # Formatação
    format_string: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    date_format: str = "%Y-%m-%d %H:%M:%S"

@dataclass
class MigrationConfig:
    """Configuração para migração do V0"""
    
    enable_v0_compatibility: bool = field(default_factory=lambda: os.getenv("ENABLE_V0_COMPATIBILITY", "true").lower() == "true")
    migration_batch_size: int = 1000
    preserve_v0_data: bool = True
    
    # Mapeamento de tabelas
    table_mapping: Dict[str, str] = field(default_factory=lambda: {
        "contratacao": "contratacoes",
        "categoria": "categorias"
    })

@dataclass
class GovGoV1Config:
    """Configuração principal do GovGo V1"""
    
    # Subcomponentes
    database: DatabaseConfig = field(default_factory=DatabaseConfig)
    paths: PathConfig = field(default_factory=PathConfig)
    pncp: PNCPConfig = field(default_factory=PNCPConfig)
    openai: OpenAIConfig = field(default_factory=get_model_config)
    search: SearchConfig = field(default_factory=SearchConfig)
    relevance: RelevanceConfig = field(default_factory=RelevanceConfig)
    processing: ProcessingConfig = field(default_factory=ProcessingConfig)
    ui: UIConfig = field(default_factory=UIConfig)
    documents: DocumentConfig = field(default_factory=DocumentConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    migration: MigrationConfig = field(default_factory=MigrationConfig)
    
    # Configurações globais
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")
    environment: str = field(default_factory=lambda: os.getenv("ENVIRONMENT", "production"))
    version: str = "1.0.0"
    
    def __post_init__(self):
        """Inicialização pós-criação"""
        # Criar diretórios necessários
        self.paths.create_directories()
        
        # Criar diretório de logs
        self.logging.file_path.parent.mkdir(parents=True, exist_ok=True)
    
    def validate(self) -> List[str]:
        """Valida configuração e retorna lista de erros"""
        errors = []
        
        # Validar OpenAI
        if not os.getenv("OPENAI_API_KEY"):
            errors.append("OPENAI_API_KEY não configurada")
        
        # Validar Supabase
        if not self.database.url or not self.database.key:
            errors.append("Credenciais Supabase incompletas")
        
        # Validar paths V0 se compatibilidade habilitada
        if self.migration.enable_v0_compatibility:
            if not self.paths.v0_sqlite_path.exists():
                errors.append(f"Banco SQLite V0 não encontrado: {self.paths.v0_sqlite_path}")
        
        return errors
    
    def get_summary(self) -> Dict[str, Any]:
        """Retorna resumo da configuração"""
        return {
            "version": self.version,
            "environment": self.environment,
            "debug": self.debug,
            "openai_models": {
                "embeddings": self.openai.EMBEDDING_MODEL,
                "chat": self.openai.CHAT_MODEL
            },
            "database": {
                "host": self.database.host,
                "port": self.database.port
            },
            "features": {
                "v0_compatibility": self.migration.enable_v0_compatibility,
                "relevance_system": self.relevance.enabled,
                "rich_ui": self.ui.enable_rich_ui,
                "document_analysis": self.documents.analysis_enabled
            }
        }

# Instância global da configuração
_config: Optional[GovGoV1Config] = None

def get_config() -> GovGoV1Config:
    """Obtém instância global da configuração"""
    global _config
    if _config is None:
        _config = GovGoV1Config()
    return _config

def reload_config() -> GovGoV1Config:
    """Recarrega configuração (útil para testes)"""
    global _config
    _config = None
    return get_config()

def validate_config() -> bool:
    """Valida configuração atual"""
    config = get_config()
    errors = config.validate()
    
    if errors:
        print("❌ Erros na configuração:")
        for error in errors:
            print(f"   - {error}")
        return False
    
    print("✅ Configuração validada com sucesso!")
    return True

if __name__ == "__main__":
    # Teste da configuração
    config = get_config()
    
    print("🏛️ GovGo V1 - Configuração:")
    print(f"   Versão: {config.version}")
    print(f"   Ambiente: {config.environment}")
    print(f"   Debug: {config.debug}")
    print()
    
    print("📊 Resumo:")
    summary = config.get_summary()
    for key, value in summary.items():
        print(f"   {key}: {value}")
    print()
    
    # Validação
    validate_config()
