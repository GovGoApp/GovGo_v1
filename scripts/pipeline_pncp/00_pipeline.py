#!/usr/bin/env python3
"""
Pipeline PNCP (novo) — executa 01 → 02 → 03 em sequência.
- Define PIPELINE_TIMESTAMP único para sessão
- Compartilha arquivo de log logs/log_<PIPELINE_TIMESTAMP>.log
- Retorna código !=0 se qualquer etapa falhar
"""

from __future__ import annotations

import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path


def main() -> int:
    folder = Path(__file__).resolve().parent
    v1_root = folder.parent
    logs_dir = v1_root / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    ts = os.environ.get("PIPELINE_TIMESTAMP")
    if not ts:
        ts = datetime.now().strftime("%Y%m%d_%H%M")
        os.environ["PIPELINE_TIMESTAMP"] = ts

    steps = [
        ("ETAPA_1_DOWNLOAD", "01_pipeline_pncp_download.py", []),
        ("ETAPA_2_EMBEDDINGS", "02_pipeline_pncp_embeddings.py", []),
        ("ETAPA_3_CATEGORIZACAO", "03_pipeline_pncp_categorization.py", []),
    ]

    print("================================================================================")
    print("GOVGO v1 - PIPELINE PNCP (novo) - SESSÃO:", ts)
    print("Diretório:", folder)
    print("================================================================================")

    base_env = os.environ.copy()

    for step_name, script_name, args in steps:
        script_path = folder / script_name
        if not script_path.exists():
            print(f"[ERRO] Script não encontrado: {script_path}")
            return 1

        env = base_env.copy()
        env["PIPELINE_STEP"] = step_name

        print("\n--------------------------------------------------------------------------------")
        print(f"[{step_name}] Executando: {script_name} {' '.join(args)}")
        print("--------------------------------------------------------------------------------")

        try:
            subprocess.run([sys.executable, str(script_path), *args], cwd=str(folder), env=env, check=True)
        except subprocess.CalledProcessError as e:
            print(f"[ERRO] {script_name} retornou código {e.returncode}")
            return e.returncode or 1
        except Exception as e:
            print(f"[ERRO] Falha ao executar {script_name}: {e}")
            return 1

        print(f"[OK] {step_name} concluída")

    print("\n================================================================================")
    print("[SUCESSO] PIPELINE PNCP (novo) CONCLUÍDO — Sessão:", ts)
    print("================================================================================")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
