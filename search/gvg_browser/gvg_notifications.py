"""
gvg_notifications.py
Sistema de notificações Toast para o GSB.

Uso:
    from gvg_notifications import add_note, NOTIF_SUCCESS, NOTIF_ERROR, NOTIF_WARNING, NOTIF_INFO
    add_note(NOTIF_SUCCESS, "Operação concluída com sucesso!")
"""
from __future__ import annotations

import uuid
import time
from typing import Literal, Dict, Any

# =============================
# Tipos de notificação
# =============================
NOTIF_SUCCESS = 'success'
NOTIF_ERROR = 'error'
NOTIF_WARNING = 'warning'
NOTIF_INFO = 'info'

NotificationType = Literal['success', 'error', 'warning', 'info']

# =============================
# Configurações de ícones e cores por tipo
# =============================
NOTIF_CONFIG: Dict[str, Dict[str, str]] = {
    NOTIF_SUCCESS: {
        'icon': 'fas fa-check-circle',
        'color': '#28a745',  # verde
    },
    NOTIF_ERROR: {
        'icon': 'fas fa-exclamation-circle',
        'color': '#dc3545',  # vermelho
    },
    NOTIF_WARNING: {
        'icon': 'fas fa-exclamation-triangle',
        'color': '#ffc107',  # amarelo/laranja
    },
    NOTIF_INFO: {
        'icon': 'fas fa-info-circle',
        'color': '#17a2b8',  # azul
    },
}

# =============================
# Estrutura de notificação
# =============================
def create_notification(tipo: NotificationType, texto: str) -> Dict[str, Any]:
    """Cria estrutura de notificação com ID único e timestamp."""
    if tipo not in NOTIF_CONFIG:
        tipo = NOTIF_INFO  # fallback
    
    return {
        'id': str(uuid.uuid4()),
        'tipo': tipo,
        'texto': texto,
        'icon': NOTIF_CONFIG[tipo]['icon'],
        'color': NOTIF_CONFIG[tipo]['color'],
        'timestamp': time.time(),
    }

# =============================
# Função principal: add_note
# =============================
def add_note(tipo: NotificationType, texto: str) -> Dict[str, Any]:
    """
    Adiciona uma notificação.
    
    Args:
        tipo: Tipo da notificação (success, error, warning, info)
        texto: Mensagem a ser exibida
    
    Returns:
        Dicionário com dados da notificação criada
    
    Exemplo:
        >>> add_note('success', 'Favorito adicionado!')
        {'id': '...', 'tipo': 'success', 'texto': '...', ...}
    """
    return create_notification(tipo, texto)

# =============================
# Helpers
# =============================
def get_notification_config(tipo: NotificationType) -> Dict[str, str]:
    """Retorna configuração (ícone e cor) para um tipo de notificação."""
    return NOTIF_CONFIG.get(tipo, NOTIF_CONFIG[NOTIF_INFO])

def format_notification_for_store(notif: Dict[str, Any]) -> Dict[str, Any]:
    """Formata notificação para armazenamento na Store do Dash."""
    return {
        'id': notif['id'],
        'tipo': notif['tipo'],
        'texto': notif['texto'],
        'icon': notif['icon'],
        'color': notif['color'],
        'timestamp': notif['timestamp'],
    }

# =============================
# Validação
# =============================
def is_valid_notification_type(tipo: str) -> bool:
    """Verifica se o tipo de notificação é válido."""
    return tipo in NOTIF_CONFIG

__all__ = [
    'add_note',
    'create_notification',
    'get_notification_config',
    'format_notification_for_store',
    'is_valid_notification_type',
    'NOTIF_SUCCESS',
    'NOTIF_ERROR',
    'NOTIF_WARNING',
    'NOTIF_INFO',
    'NotificationType',
]
