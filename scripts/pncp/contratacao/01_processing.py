#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
01_processing (Contratação)

Ponte para o pipeline existente 01_pipeline_pncp_download.py, mantendo a nova organização por domínio/estágio.
"""
import os
import runpy

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # caminho relativo até scripts/pipeline_pncp/01_pipeline_pncp_download.py
    legacy = os.path.normpath(os.path.join(base_dir, "..", "..", "pipeline_pncp", "01_pipeline_pncp_download.py"))
    runpy.run_path(path=legacy, run_name="__main__")
