#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Camada de compatibilidade para executar gvg_cnpj_search com psycopg3.

Este módulo injeta um shim mínimo da API do psycopg2 (apenas partes usadas
no gvg_cnpj_search original) construído sobre o driver oficial psycopg v3.
Assim conseguimos reaproveitar a lógica existente sem editar o arquivo
`gvg_cnpj_search.py`, garantindo suporte ao Python 3.13 em ambientes onde
`psycopg2-binary` não possui wheels atualizados.
"""

from __future__ import annotations

import importlib.util
import logging
import sys
import types
from pathlib import Path

_ORIG_MODULE_NAME = "gvg_cnpj_search_original_v2"
_ORIG_PATH = Path(__file__).with_name("gvg_cnpj_search.py")


def _install_psycopg2_shim() -> None:
    """Registra módulos `psycopg2` e `psycopg2.extras` compatíveis via psycopg3."""

    try:
        import psycopg  # type: ignore
        from psycopg import errors as psy_errors  # type: ignore
        from psycopg.rows import dict_row  # type: ignore
    except Exception as exc:  # pragma: no cover - erro crítico de dependência
        raise ImportError(
            "psycopg (v3) é obrigatório para gvg_cnpj_search_v2"
        ) from exc

    class _RealDictCursor:
        """Sentinela usada para mapear `cursor_factory=RealDictCursor`."""

        __slots__ = ()

    class _CompatConnection:
        """Wrapper fino para adaptar a API de conexão do psycopg2."""

        __slots__ = ("_raw",)

        def __init__(self, raw_conn):
            self._raw = raw_conn

        def cursor(self, *args, **kwargs):
            cursor_factory = kwargs.pop("cursor_factory", None)
            if cursor_factory is _RealDictCursor:
                kwargs["row_factory"] = dict_row
            elif cursor_factory is not None:
                logging.warning(
                    "cursor_factory custom não suportado; usando cursor padrão"
                )
            return self._raw.cursor(*args, **kwargs)

        def __enter__(self):
            self._raw.__enter__()
            return self

        def __exit__(self, exc_type, exc, tb):
            return self._raw.__exit__(exc_type, exc, tb)

        def __getattr__(self, attr):
            return getattr(self._raw, attr)

    def _connect(*args, **kwargs):
        return _CompatConnection(psycopg.connect(*args, **kwargs))

    shim = types.ModuleType("psycopg2")
    shim.connect = _connect  # type: ignore[attr-defined]
    shim.errors = psy_errors  # type: ignore[attr-defined]

    extras = types.ModuleType("psycopg2.extras")
    extras.RealDictCursor = _RealDictCursor  # type: ignore[attr-defined]

    shim.extras = extras  # type: ignore[attr-defined]
    sys.modules["psycopg2"] = shim
    sys.modules["psycopg2.extras"] = extras


def _ensure_psycopg2() -> None:
    try:
        import psycopg2  # type: ignore  # noqa: F401
    except Exception:
        _install_psycopg2_shim()


def _load_original_module():
    spec = importlib.util.spec_from_file_location(_ORIG_MODULE_NAME, _ORIG_PATH)
    if spec is None or spec.loader is None:
        raise ImportError("Não foi possível carregar gvg_cnpj_search original.")
    module = importlib.util.module_from_spec(spec)
    sys.modules[_ORIG_MODULE_NAME] = module
    spec.loader.exec_module(module)  # type: ignore[call-arg]
    return module


_ensure_psycopg2()
_ORIG = _load_original_module()

run_search = _ORIG.run_search
get_db_conn = _ORIG.get_db_conn
load_municipios_coords = _ORIG.load_municipios_coords
extract_hq_ibge = _ORIG.extract_hq_ibge
normalize_cnpj = _ORIG.normalize_cnpj

__all__ = [
    "run_search",
    "get_db_conn",
    "load_municipios_coords",
    "extract_hq_ibge",
    "normalize_cnpj",
]