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
import importlib.util


def _print(msg: str):  # impressão simples padronizada
    print(msg, flush=True)


def ensure_dependencies():
    """Bootstrap idempotente das dependências mínimas do pipeline.

    Se qualquer pacote crítico não estiver importável, executa:
      python -m pip install --no-cache-dir -r scripts/requirements.txt

    Controle via env:
      PIPELINE_SKIP_BOOTSTRAP=1  -> pula checagem
      PIPELINE_DEBUG_BOOTSTRAP=1 -> imprime detalhes extras
    """
    if os.environ.get("PIPELINE_SKIP_BOOTSTRAP") == "1":
        _print("[BOOTSTRAP] Pulado (PIPELINE_SKIP_BOOTSTRAP=1)")
        return

    critical = [
        ("requests", "requests"),
        ("openai", "openai"),
        ("psycopg2", "psycopg2"),
        ("numpy", "numpy"),
        ("pandas", "pandas"),
        ("rich", "rich"),
        ("dotenv", "python-dotenv"),  # import nome -> pacote pypi
    ]

    missing = []
    for import_name, pkg in critical:
        if importlib.util.find_spec(import_name) is None:
            missing.append(pkg)

    if not missing:
        _print("[BOOTSTRAP] Dependências já presentes")
        if os.environ.get("PIPELINE_DEBUG_BOOTSTRAP") == "1":
            _print(f"[BOOTSTRAP] Python: {sys.executable}")
        return

    req_path = Path(__file__).resolve().parent / "requirements.txt"
    if not req_path.exists():
        _print(f"[BOOTSTRAP][ERRO] requirements não encontrado em {req_path}")
        sys.exit(2)

    _print(f"[BOOTSTRAP] Faltando: {', '.join(missing)} -> instalando via {req_path.name}")
    try:
        cmd = [sys.executable, "-m", "pip", "install", "--no-cache-dir", "-r", str(req_path)]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            _print("[BOOTSTRAP][ERRO] Falha na instalação pip")
            _print(result.stdout)
            _print(result.stderr)
            sys.exit(3)
        _print("[BOOTSTRAP] Instalação concluída")
    except Exception as e:
        _print(f"[BOOTSTRAP][ERRO] Exceção na instalação: {e}")
        sys.exit(4)

    # Verificar novamente
    still_missing = [pkg for imp, pkg in critical if importlib.util.find_spec(imp) is None]
    if still_missing:
        _print(f"[BOOTSTRAP][ERRO] Ainda faltando: {', '.join(still_missing)}")
        sys.exit(5)
    _print("[BOOTSTRAP] Verificação final OK")


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

    # Bootstrap de dependências antes de qualquer execução
    ensure_dependencies()

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
