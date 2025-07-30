"""
GovGo V1 - Configuração Centralizada
====================================

Gerencia todas as configurações do sistema de forma centralizada,
incluindo conexões de banco, APIs, e parâmetros de processamento.
"""

import os
from typing import Optional, Dict, Any
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

# Carrega variáveis de ambiente
load_dotenv()

@dataclass
class DatabaseConfig:
    """Configurações de banco de dados"""
    supabase_url: str
    supabase_key: str
    supabase_db_url: str
    connection_pool_size: int = 10
    connection_timeout: int = 30

@dataclass
class OpenAIConfig:
    """Configurações da OpenAI"""
    api_key: str
    model_embeddings: str = "text-embedding-3-small"
    model_chat: str = "gpt-4o-mini"
    max_tokens: int = 4096
    temperature: float = 0.1

@dataclass
class PNCPConfig:
    """Configurações da API PNCP"""
    base_url: str = "https://pncp.gov.br/api/pncp/v1"
    token: Optional[str] = None
    timeout: int = 30
    retry_attempts: int = 3
    rate_limit_delay: float = 1.0

@dataclass
class ProcessingConfig:
    """Configurações de processamento"""
    batch_size: int = 100
    max_workers: int = 4
    chunk_size: int = 1000
    cache_embeddings: bool = True
    embedding_dimension: int = 1536

@dataclass
class LoggingConfig:
    """Configurações de logging"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    log_to_file: bool = True
    log_file_path: str = "logs/govgo_v1.log"
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5

class Config:
    """Configuração principal do sistema"""
    
    def __init__(self):
        self.database = DatabaseConfig(
            supabase_url=self._get_env("SUPABASE_URL"),
            supabase_key=self._get_env("SUPABASE_KEY"),
            supabase_db_url=self._get_env("SUPABASE_DB_URL")
        )
        
        self.openai = OpenAIConfig(
            api_key=self._get_env("OPENAI_API_KEY"),
            model_embeddings=self._get_env("OPENAI_MODEL_EMBEDDINGS", "text-embedding-3-small"),
            model_chat=self._get_env("OPENAI_MODEL_CHAT", "gpt-4o-mini")
        )
        
        self.pncp = PNCPConfig(
            base_url=self._get_env("PNCP_BASE_URL", "https://pncp.gov.br/api/pncp/v1"),
            token=self._get_env("PNCP_TOKEN"),
            timeout=int(self._get_env("PNCP_TIMEOUT", "30"))
        )
        
        self.processing = ProcessingConfig(
            batch_size=int(self._get_env("BATCH_SIZE", "100")),
            max_workers=int(self._get_env("MAX_WORKERS", "4")),
            cache_embeddings=self._get_env("CACHE_EMBEDDINGS", "true").lower() == "true"
        )
        
        self.logging = LoggingConfig(
            level=self._get_env("LOG_LEVEL", "INFO"),
            log_to_file=self._get_env("LOG_TO_FILE", "true").lower() == "true"
        )
        
        # Cria diretórios necessários
        self._create_directories()
    
    def _get_env(self, key: str, default: Optional[str] = None) -> str:
        """Obtém variável de ambiente com tratamento de erro"""
        value = os.getenv(key, default)
        if value is None:
            raise ValueError(f"Variável de ambiente obrigatória não encontrada: {key}")
        return value
    
    def _create_directories(self):
        """Cria diretórios necessários"""
        directories = [
            "logs",
            "cache",
            "temp",
            "exports"
        ]
        
        for directory in directories:
            Path(directory).mkdir(exist_ok=True)
    
    def validate(self) -> bool:
        """Valida se todas as configurações estão corretas"""
        try:
            # Valida URLs
            if not self.database.supabase_url.startswith("https://"):
                raise ValueError("SUPABASE_URL deve começar com https://")
            
            if not self.pncp.base_url.startswith("https://"):
                raise ValueError("PNCP_BASE_URL deve começar com https://")
            
            # Valida API keys
            if not self.openai.api_key.startswith("sk-"):
                raise ValueError("OPENAI_API_KEY deve começar com sk-")
            
            # Valida parâmetros numéricos
            if self.processing.batch_size <= 0:
                raise ValueError("BATCH_SIZE deve ser maior que 0")
            
            if self.processing.max_workers <= 0:
                raise ValueError("MAX_WORKERS deve ser maior que 0")
            
            return True
            
        except Exception as e:
            print(f"Erro na validação da configuração: {e}")
            return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Converte configuração para dicionário (para logs)"""
        return {
            "database": {
                "supabase_url": self.database.supabase_url,
                "connection_pool_size": self.database.connection_pool_size
            },
            "openai": {
                "model_embeddings": self.openai.model_embeddings,
                "model_chat": self.openai.model_chat
            },
            "pncp": {
                "base_url": self.pncp.base_url,
                "timeout": self.pncp.timeout
            },
            "processing": {
                "batch_size": self.processing.batch_size,
                "max_workers": self.processing.max_workers
            }
        }

# Instância global da configuração
config = Config()

# Valida configuração na importação
if not config.validate():
    raise RuntimeError("Configuração inválida. Verifique as variáveis de ambiente.")
