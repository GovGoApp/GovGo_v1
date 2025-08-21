"""DEPRECIADO: use as funções em gvg_preprocessing.

Este arquivo permanece apenas para compatibilidade transitória.
Todas as funções foram migradas para `gvg_preprocessing`.
Importe diretamente:
    from gvg_preprocessing import format_currency, format_date, decode_poder, decode_esfera
"""

from gvg_preprocessing import (
    format_currency,
    format_date,
    decode_poder,
    decode_esfera,
)

__all__ = [
    'format_currency',
    'format_date',
    'decode_poder',
    'decode_esfera'
]
