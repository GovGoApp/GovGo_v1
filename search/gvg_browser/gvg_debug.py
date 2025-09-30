"""
Helpers de debug para o GvG Browser com categorias e Rich Console.

Uso:
    from gvg_debug import debug_log as dbg, is_debug_enabled as isdbg, debug_sql as dbg_sql
    dbg('AUTH', 'mensagem')

Sinalizadores de ambiente (booleanos: 1/true/yes/on):
    DEBUG              -> master: quando false, desliga TODOS os logs; quando true, respeita apenas as flags por área
    GVG_<AREA>_DEBUG   -> por área (ex.: GVG_AUTH_DEBUG, GVG_SEARCH_DEBUG, GVG_SQL_DEBUG, ...)
Aliases legados suportados:
    GVG_BROWSER_DEBUG  -> area=BROWSER
    GVG_SQL_DEBUG      -> area=SQL
"""
from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

try:
    from rich.console import Console  # type: ignore
    _console = Console(highlight=False, soft_wrap=False)  # Console global
except Exception:
    class _PlainConsole:
        def print(self, *args, **kwargs):  # ignore styles, behave like print
            try:
                msg = " ".join(str(a) for a in args)
                end = kwargs.get('end', '\n')
                print(msg, end=end)
            except Exception:
                try:
                    print(*args, **kwargs)
                except Exception:
                    pass
    _console = _PlainConsole()

# Estilos por área (cores Rich)
_AREA_STYLE_MAP: Dict[str, str] = {
    'SQL': 'yellow',
    'AUTH': 'green',
    'SEARCH': 'cyan',
    'DOCS': 'magenta',
    'ASSISTANT': 'bright_magenta',
    'UI': 'white',
    'BROWSER': 'bright_white',
    'BOLETIM': 'bright_cyan',
    'BMK': 'bright_magenta',
    'FAV': 'bright_magenta',
    'PREPROC': 'blue',
    'RESUMO': 'bright_green',
    'ERROR': 'bold red',
}

_TRUE_SET = {'1', 'true', 'yes', 'on', 'y', 't'}


def _env_flag(name: str) -> bool:
    try:
        val = (os.getenv(name) or '').strip().lower()
        return val in _TRUE_SET
    except Exception:
        return False


def is_debug_enabled(area: str) -> bool:
    """Retorna True se a categoria está habilitada.

    Política:
    - DEBUG=false => todos desabilitados (ignora flags por área).
    - DEBUG=true  => NÃO habilita tudo; apenas áreas com GVG_<AREA>_DEBUG=true.
    """
    area_norm = (area or '').strip().upper() or 'BROWSER'
    if not _env_flag('DEBUG'):
        return False
    # Área específica
    if _env_flag(f'GVG_{area_norm}_DEBUG'):
        return True
    return False


def debug_log(area: str, *args: Any, sep: str = ' ', end: str = '\n') -> None:
    """Log simples por categoria usando Rich, sem prefixos customizados."""
    if not is_debug_enabled(area):
        return
    try:
        area_norm = (area or '').strip().upper() or 'BROWSER'
        style = _AREA_STYLE_MAP.get(area_norm, 'white')
        # Prefixar a mensagem com [AREA]
        msg = sep.join(str(a) for a in args)
        prefixed = f"[{area_norm}] {msg}" if msg else f"[{area_norm}]"
        _console.print(prefixed, style=style, end=end)
    except Exception:
        pass


def _summarize_param(p: Any) -> str:
    """Representação compacta de parâmetros para logs SQL."""
    try:
        import numpy as _np  # type: ignore
        if isinstance(p, _np.ndarray):
            try:
                return f"<ndarray shape={p.shape}>"
            except Exception:
                try:
                    return f"<ndarray len={p.size}>"
                except Exception:
                    return "<ndarray>"
    except Exception:
        pass
    try:
        if isinstance(p, (list, tuple)):
            if len(p) > 100 and all(isinstance(x, (int, float)) for x in p[: min(10, len(p))]):
                return f"<vector len={len(p)}>"
            head = ", ".join(repr(x) for x in p[:3])
            ell = ", ..." if len(p) > 3 else ""
            return f"[{head}{ell}] (len={len(p)})"
        if isinstance(p, str):
            s = repr(p)
            return s if len(s) <= 120 else s[:117] + "...'"
        return str(p)
    except Exception:
        return f"<{type(p).__name__}>"


def debug_sql(label: str, sql: str, params: Optional[List[Any]] = None, names: Optional[List[str]] = None) -> None:
    """Log SQL padronizado com contagem de placeholders e parâmetros resumidos."""
    if not is_debug_enabled('SQL'):
        return
    try:
        import re as _re
        placeholders = len(_re.findall(r'(?<!%)%s', sql))
    except Exception:
        placeholders = sql.count('%s') if isinstance(sql, str) else 0
    style = _AREA_STYLE_MAP.get('SQL', 'yellow')
    try:
        prefix = "[SQL] "
        _console.print(f"{prefix}{label}: placeholders={placeholders} params={len(params or [])} match={'YES' if placeholders==(len(params or [])) else 'NO'}", style=style)
        _console.print(f"{prefix}{sql}", style=style)
        if params:
            _console.print(f"{prefix}-- PARAMETERS:", style=style)
            for i, p in enumerate(params):
                name = names[i] if (names and i < len(names)) else None
                prefix = (name + " = ") if name else ""
                _console.print(f"[SQL]   {i:02d}: {prefix}{_summarize_param(p)}", style=style)
    except Exception:
        pass
