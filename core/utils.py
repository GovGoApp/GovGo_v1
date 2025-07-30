"""
GovGo V1 - Utilitários Comuns
=============================

Funções utilitárias compartilhadas em todo o sistema.
"""

import re
import json
import logging
import hashlib
import unicodedata
from typing import Any, Dict, List, Optional, Union
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path

logger = logging.getLogger(__name__)

# ===============================
# LIMPEZA E NORMALIZAÇÃO DE TEXTO
# ===============================

def limpar_texto(texto: str) -> str:
    """Limpa e normaliza texto para processamento"""
    if not texto:
        return ""
    
    # Remove acentos
    texto = unicodedata.normalize('NFD', texto)
    texto = ''.join(char for char in texto if unicodedata.category(char) != 'Mn')
    
    # Remove caracteres especiais, mantém apenas letras, números e espaços
    texto = re.sub(r'[^\w\s]', ' ', texto)
    
    # Remove espaços múltiplos
    texto = re.sub(r'\s+', ' ', texto)
    
    return texto.strip()

def extrair_numeros(texto: str) -> List[str]:
    """Extrai números de um texto"""
    if not texto:
        return []
    
    return re.findall(r'\d+', texto)

def normalizar_cnpj(cnpj: str) -> str:
    """Normaliza CNPJ removendo caracteres especiais"""
    if not cnpj:
        return ""
    
    return re.sub(r'[^\d]', '', cnpj)

def validar_cnpj(cnpj: str) -> bool:
    """Valida formato de CNPJ"""
    cnpj_limpo = normalizar_cnpj(cnpj)
    return len(cnpj_limpo) == 14 and cnpj_limpo.isdigit()

# ===============================
# FORMATAÇÃO DE VALORES
# ===============================

def formatar_valor(valor: Union[float, Decimal, None]) -> str:
    """Formata valor monetário para exibição"""
    if valor is None:
        return "N/A"
    
    try:
        if isinstance(valor, str):
            valor = float(valor)
        
        return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return "N/A"

def formatar_data(data: Union[date, datetime, str, None]) -> str:
    """Formata data para exibição"""
    if data is None:
        return "N/A"
    
    try:
        if isinstance(data, str):
            # Tenta diferentes formatos
            for formato in ["%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%d/%m/%Y"]:
                try:
                    data = datetime.strptime(data, formato).date()
                    break
                except ValueError:
                    continue
            else:
                return data  # Retorna string original se não conseguir converter
        
        if isinstance(data, datetime):
            data = data.date()
        
        return data.strftime("%d/%m/%Y")
    except (ValueError, TypeError):
        return str(data) if data else "N/A"

def parse_valor(valor_str: str) -> Optional[Decimal]:
    """Converte string de valor para Decimal"""
    if not valor_str:
        return None
    
    try:
        # Remove caracteres não numéricos exceto vírgula e ponto
        valor_limpo = re.sub(r'[^\d,.]', '', str(valor_str))
        
        # Se tem vírgula e ponto, assume que vírgula é separador de milhar
        if ',' in valor_limpo and '.' in valor_limpo:
            valor_limpo = valor_limpo.replace(',', '')
        elif ',' in valor_limpo:
            # Se só tem vírgula, verifica se é decimal ou milhar
            partes = valor_limpo.split(',')
            if len(partes) == 2 and len(partes[1]) <= 2:
                # Provavelmente decimal
                valor_limpo = valor_limpo.replace(',', '.')
            else:
                # Provavelmente milhar
                valor_limpo = valor_limpo.replace(',', '')
        
        return Decimal(valor_limpo)
    except (ValueError, TypeError):
        return None

# ===============================
# MANIPULAÇÃO DE ARQUIVOS
# ===============================

def garantir_diretorio(caminho: Union[str, Path]) -> Path:
    """Garante que um diretório existe, criando se necessário"""
    caminho = Path(caminho)
    caminho.mkdir(parents=True, exist_ok=True)
    return caminho

def ler_arquivo_json(caminho: Union[str, Path]) -> Optional[Dict[str, Any]]:
    """Lê arquivo JSON com tratamento de erro"""
    try:
        with open(caminho, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.error(f"Erro ao ler arquivo JSON {caminho}: {e}")
        return None

def salvar_arquivo_json(dados: Dict[str, Any], caminho: Union[str, Path]) -> bool:
    """Salva dados em arquivo JSON"""
    try:
        # Garante que o diretório existe
        caminho = Path(caminho)
        garantir_diretorio(caminho.parent)
        
        with open(caminho, 'w', encoding='utf-8') as f:
            json.dump(dados, f, ensure_ascii=False, indent=2, default=str)
        return True
    except Exception as e:
        logger.error(f"Erro ao salvar arquivo JSON {caminho}: {e}")
        return False

# ===============================
# CACHE E HASH
# ===============================

def gerar_hash(texto: str) -> str:
    """Gera hash MD5 de um texto"""
    return hashlib.md5(texto.encode('utf-8')).hexdigest()

def gerar_cache_key(*args) -> str:
    """Gera chave de cache baseada nos argumentos"""
    texto = "_".join(str(arg) for arg in args)
    return gerar_hash(texto)

# ===============================
# VALIDAÇÃO DE DADOS
# ===============================

def validar_numero_controle_pncp(numero: str) -> bool:
    """Valida formato do número de controle PNCP"""
    if not numero:
        return False
    
    # Formato típico: YYYYMMDDHHMMSS-CNPJ ou similar
    return len(numero) >= 10 and '-' in numero

def validar_email(email: str) -> bool:
    """Valida formato de email"""
    if not email:
        return False
    
    padrao = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(padrao, email))

def validar_url(url: str) -> bool:
    """Valida formato de URL"""
    if not url:
        return False
    
    padrao = r'^https?://[^\s]+$'
    return bool(re.match(padrao, url))

# ===============================
# CONVERSÃO DE DADOS
# ===============================

def dict_para_objeto(dados: Dict[str, Any], classe) -> Any:
    """Converte dicionário para objeto da classe especificada"""
    try:
        return classe(**dados)
    except Exception as e:
        logger.error(f"Erro ao converter dicionário para {classe.__name__}: {e}")
        return None

def objeto_para_dict(objeto: Any) -> Dict[str, Any]:
    """Converte objeto para dicionário"""
    if hasattr(objeto, 'dict'):
        return objeto.dict()
    elif hasattr(objeto, '__dict__'):
        return objeto.__dict__
    else:
        return {}

def serializar_para_json(dados: Any) -> str:
    """Serializa dados para JSON com tratamento de tipos especiais"""
    def default_serializer(obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, Decimal):
            return float(obj)
        elif hasattr(obj, 'dict'):
            return obj.dict()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        return str(obj)
    
    return json.dumps(dados, default=default_serializer, ensure_ascii=False, indent=2)

# ===============================
# LOGGING E DEBUG
# ===============================

def configurar_logging(level: str = "INFO", log_file: Optional[str] = None):
    """Configura sistema de logging"""
    import logging.handlers
    
    # Define nível
    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f'Invalid log level: {level}')
    
    # Formato das mensagens
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Logger root
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Remove handlers existentes
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Handler para console
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Handler para arquivo (se especificado)
    if log_file:
        garantir_diretorio(Path(log_file).parent)
        file_handler = logging.handlers.RotatingFileHandler(
            log_file, maxBytes=10*1024*1024, backupCount=5, encoding='utf-8'
        )
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

def log_tempo_execucao(func):
    """Decorator para logar tempo de execução de funções"""
    def wrapper(*args, **kwargs):
        inicio = datetime.now()
        try:
            resultado = func(*args, **kwargs)
            fim = datetime.now()
            tempo = (fim - inicio).total_seconds()
            logger.info(f"{func.__name__} executada em {tempo:.2f}s")
            return resultado
        except Exception as e:
            fim = datetime.now()
            tempo = (fim - inicio).total_seconds()
            logger.error(f"{func.__name__} falhou após {tempo:.2f}s: {e}")
            raise
    return wrapper

# ===============================
# UTILITÁRIOS DE PROCESSAMENTO
# ===============================

def dividir_em_lotes(lista: List[Any], tamanho_lote: int) -> List[List[Any]]:
    """Divide lista em lotes de tamanho específico"""
    if tamanho_lote <= 0:
        raise ValueError("Tamanho do lote deve ser maior que 0")
    
    return [lista[i:i + tamanho_lote] for i in range(0, len(lista), tamanho_lote)]

def calcular_progresso(atual: int, total: int) -> float:
    """Calcula percentual de progresso"""
    if total <= 0:
        return 0.0
    return min(100.0, (atual / total) * 100.0)

def estimar_tempo_restante(inicio: datetime, atual: int, total: int) -> Optional[str]:
    """Estima tempo restante baseado no progresso"""
    if atual <= 0 or total <= 0 or atual >= total:
        return None
    
    tempo_decorrido = (datetime.now() - inicio).total_seconds()
    tempo_por_item = tempo_decorrido / atual
    itens_restantes = total - atual
    segundos_restantes = tempo_por_item * itens_restantes
    
    # Converte para formato legível
    if segundos_restantes < 60:
        return f"{int(segundos_restantes)}s"
    elif segundos_restantes < 3600:
        minutos = int(segundos_restantes / 60)
        return f"{minutos}m"
    else:
        horas = int(segundos_restantes / 3600)
        minutos = int((segundos_restantes % 3600) / 60)
        return f"{horas}h{minutos:02d}m"

# ===============================
# CONSTANTES ÚTEIS
# ===============================

MESES_PORTUGUES = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março", 4: "Abril",
    5: "Maio", 6: "Junho", 7: "Julho", 8: "Agosto",
    9: "Setembro", 10: "Outubro", 11: "Novembro", 12: "Dezembro"
}

MODALIDADES_PNCP = {
    1: "Convite", 2: "Tomada de Preços", 3: "Concorrência",
    4: "Pregão", 5: "Concurso", 6: "Consulta",
    7: "Regime Diferenciado de Contratações Públicas",
    8: "Leilão", 9: "Credenciamento", 10: "Manifestação de Interesse",
    11: "Pré-qualificação", 12: "Procedimento de Manifestação de Interesse",
    13: "Diálogo Competitivo", 99: "Outros"
}

SITUACOES_COMPRA = {
    1: "Planejamento", 2: "Divulgação", 3: "Recebimento de Propostas",
    4: "Em Julgamento", 5: "Homologada", 6: "Adjudicada",
    7: "Fracassada", 8: "Deserta", 9: "Suspensa", 10: "Cancelada"
}
