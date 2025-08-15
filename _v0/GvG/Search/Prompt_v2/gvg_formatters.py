"""
gvg_formatters.py
Módulo otimizado para formatação de dados GvG
Contém apenas as funções de formatação realmente utilizadas pelo Terminal_v9
"""

from datetime import datetime

def format_currency(value):
    """
    Formata valor monetário para exibição
    
    Args:
        value: Valor numérico a ser formatado
        
    Returns:
        str: Valor formatado como moeda (R$ XX.XXX.XXX,XX)
    """
    try:
        if value is None:
            return "R$ 0,00"
        return f"R$ {float(value):,.2f}".replace(',', 'X').replace('.', ',').replace('X', '.')
    except (ValueError, TypeError):
        return "R$ 0,00"

def format_date(date_value):
    """
    Formata data para exibição consistente
    
    Args:
        date_value: Data em vários formatos possíveis
        
    Returns:
        str: Data formatada como DD/MM/AAAA ou string original se inválida
    """
    if not date_value:
        return ""
    
    try:
        # Se já é string no formato brasileiro, retorna como está
        if isinstance(date_value, str) and '/' in date_value:
            parts = date_value.split('/')
            if len(parts) == 3 and len(parts[2]) == 4:
                return date_value
        
        # Se é datetime object
        if isinstance(date_value, datetime):
            return date_value.strftime('%d/%m/%Y')
        
        # Se é string ISO (YYYY-MM-DD)
        if isinstance(date_value, str) and '-' in date_value:
            try:
                dt = datetime.strptime(date_value[:10], '%Y-%m-%d')
                return dt.strftime('%d/%m/%Y')
            except ValueError:
                pass
        
        # Retorna original se não conseguiu converter
        return str(date_value)
        
    except Exception:
        return str(date_value) if date_value else ""

def decode_poder(poder_code):
    """
    Decodifica código do poder para nome completo
    
    Args:
        poder_code: Código numérico do poder
        
    Returns:
        str: Nome do poder correspondente
    """
    poder_map = {
        1: "Executivo",
        2: "Legislativo", 
        3: "Judiciário",
        4: "Ministério Público",
        5: "Defensoria Pública",
        6: "Tribunal de Contas"
    }
    
    try:
        code = int(poder_code) if poder_code else 0
        return poder_map.get(code, f"Código {code}")
    except (ValueError, TypeError):
        return str(poder_code) if poder_code else "Não informado"

def decode_esfera(esfera_code):
    """
    Decodifica código da esfera para nome completo
    
    Args:
        esfera_code: Código numérico da esfera
        
    Returns:
        str: Nome da esfera correspondente
    """
    esfera_map = {
        1: "Federal",
        2: "Estadual",
        3: "Municipal",
        4: "Distrital"
    }
    
    try:
        code = int(esfera_code) if esfera_code else 0
        return esfera_map.get(code, f"Código {code}")
    except (ValueError, TypeError):
        return str(esfera_code) if esfera_code else "Não informado"
