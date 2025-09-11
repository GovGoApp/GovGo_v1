#!/usr/bin/env python3
"""
Pipeline GovGo v1 (scripts) — executa 03 → 04 → 05 em sequência.

• Define PIPELINE_TIMESTAMP único para compartilhar o mesmo arquivo de log.
• Define PIPELINE_STEP antes de cada etapa (apenas informativo para os scripts).
• Usa o mesmo Python do ambiente atual (sys.executable).
• Retorna código de saída != 0 se qualquer etapa falhar.

Uso local (opcional):
  python pipeline.py            # modo padrão
  PIPELINE_DEBUG=1 python pipeline.py  # ativa --debug nos scripts que suportam
"""

from __future__ import annotations

import os
import sys
import subprocess
from datetime import datetime
from pathlib import Path


def main() -> int:
    scripts_dir = Path(__file__).resolve().parent

    # Timestamp único da sessão (compartilhado pelos três scripts)
    pipeline_ts = os.environ.get("PIPELINE_TIMESTAMP")
    if not pipeline_ts:
        pipeline_ts = datetime.now().strftime("%Y%m%d_%H%M")
        os.environ["PIPELINE_TIMESTAMP"] = pipeline_ts

    # Modo debug opcional: exporte PIPELINE_DEBUG=1 para propagar --debug
    debug_enabled = os.environ.get("PIPELINE_DEBUG") in {"1", "true", "TRUE", "yes", "on"}
    base_env = os.environ.copy()

    steps = [
        ("ETAPA_1_DOWNLOAD", "03_download_pncp_contracts.py", ["--debug"] if debug_enabled else []),
        ("ETAPA_2_EMBEDDINGS", "04_generate_embeddings.py", ["--debug"] if debug_enabled else []),
        ("ETAPA_3_CATEGORIZACAO", "05_categorize_contracts.py", []),
    ]

    print("================================================================================")
    print("GOVGO v1 - PIPELINE (Python) - SESSÃO:", pipeline_ts)
    print("Diretório:", scripts_dir)
    print("================================================================================")

    for step_name, script_name, args in steps:
        script_path = scripts_dir / script_name
        if not script_path.exists():
            print(f"[ERRO] Arquivo não encontrado: {script_path}")
            return 1

        # Atualiza variável de ambiente informativa para os scripts
        env = base_env.copy()
        env["PIPELINE_STEP"] = step_name

        print("\n--------------------------------------------------------------------------------")
        print(f"[{step_name}] Executando: {script_name} {' '.join(args)}")
        print("--------------------------------------------------------------------------------")

        try:
            result = subprocess.run(
                [sys.executable, str(script_path), *args],
                cwd=str(scripts_dir),
                env=env,
                check=True,
            )
        except subprocess.CalledProcessError as e:
            print(f"[ERRO] {script_name} retornou código {e.returncode}")
            return e.returncode or 1
        except Exception as e:
            print(f"[ERRO] Falha ao executar {script_name}: {e}")
            return 1

        print(f"[OK] {step_name} concluída com sucesso")

    print("\n================================================================================")
    print("[SUCESSO] PIPELINE CONCLUÍDO SEM ERROS — Sessão:", pipeline_ts)
    print("================================================================================")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
