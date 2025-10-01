#!/usr/bin/env python3
"""
Pipeline Boletim — executa 01 -> 02 em sequência na mesma sessão.
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
import importlib.util
import importlib.util


def main() -> int:
    folder = Path(__file__).resolve().parent
    logs_dir = folder / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)

    ts = os.environ.get("PIPELINE_TIMESTAMP")
    if not ts:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.environ["PIPELINE_TIMESTAMP"] = ts

    # Executar etapas como módulos (-m) para assegurar contexto de pacote
    steps = [
        ("ETAPA_1_EXECUCAO", "search.gvg_browser.scripts.01_run_scheduled_boletins", []),
        ("ETAPA_2_ENVIO", "search.gvg_browser.scripts.02_send_boletins_email", []),
    ]

    print("================================================================================")
    print("GOVGO v1 - PIPELINE BOLETIM - SESSÃO:", ts)
    print("Diretório:", folder)
    print("================================================================================")

    base_env = os.environ.copy()
    # Garante PYTHONPATH com a raiz do projeto (../.. da pasta scripts)
    proj_root = str((folder / ".." / ".." / "..").resolve())
    base_env["PYTHONPATH"] = proj_root + os.pathsep + base_env.get("PYTHONPATH", "")

    # Bootstrap de dependências: instala requirements se módulos essenciais faltarem
    def _has_mod(name: str) -> bool:
        try:
            return importlib.util.find_spec(name) is not None
        except Exception:
            return False

    essential = ["sqlalchemy", "psycopg2", "dotenv", "requests", "pandas", "numpy", "rich"]
    missing = [m for m in essential if not _has_mod(m)]
    if missing:
        print(f"[bootstrap] Dependências ausentes: {', '.join(missing)} — instalando...")
        reqs = folder / "requirements.txt"
        alt_reqs = Path(proj_root) / "requirements.txt"
        req_file = reqs if reqs.exists() else (alt_reqs if alt_reqs.exists() else None)
        try:
            if req_file:
                subprocess.run([sys.executable, "-m", "pip", "install", "-r", str(req_file)], check=True)
            else:
                # fallback minimal
                subprocess.run([sys.executable, "-m", "pip", "install", "SQLAlchemy", "psycopg2-binary", "python-dotenv", "requests", "pandas", "numpy", "rich"], check=True)
        except subprocess.CalledProcessError as e:
            print(f"[bootstrap][ERRO] pip install retornou código {e.returncode}")
            return e.returncode or 1
        except Exception as e:
            print(f"[bootstrap][ERRO] Falha no pip install: {e}")
            return 1

    for step_name, module_name, args in steps:
        # validar módulo
        if importlib.util.find_spec(module_name) is None:
            print(f"[ERRO] Módulo não encontrado: {module_name}")
            return 1

        env = base_env.copy()
        env["PIPELINE_STEP"] = step_name

        print("\n--------------------------------------------------------------------------------")
        print(f"[{step_name}] Executando módulo: {module_name} {' '.join(args)}")
        print("--------------------------------------------------------------------------------")

        try:
            # Executa como módulo a partir da raiz do projeto (proj_root)
            subprocess.run([sys.executable, "-m", module_name, *args], cwd=str(Path(proj_root)), env=env, check=True)
        except subprocess.CalledProcessError as e:
            print(f"[ERRO] {module_name} retornou código {e.returncode}")
            return e.returncode or 1
        except Exception as e:
            print(f"[ERRO] Falha ao executar {module_name}: {e}")
            return 1

        print(f"[OK] {step_name} concluída")

    print("\n================================================================================")
    print("[SUCESSO] PIPELINE BOLETIM CONCLUÍDO — Sessão:", ts)
    print("================================================================================")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
