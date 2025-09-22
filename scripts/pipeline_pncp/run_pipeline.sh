#!/usr/bin/env bash
# Wrapper idempotente para executar o novo pipeline (00 -> 01 -> 02 -> 03) no Cron da Render
# - Garante deps via pip apenas se faltarem (ou quando FORCE_PIP_INSTALL=1)
# - Usa o Python disponível no runtime do Cron
# - Executa 00_pipeline.py nesta pasta

set -Eeuo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Descobrir Python
PY="${PYTHON_BIN:-python}"
if ! command -v "$PY" >/dev/null 2>&1; then
  if command -v python3 >/dev/null 2>&1; then
    PY=python3
  else
    PY=/usr/bin/python3
  fi
fi

if [[ "${DEBUG_BOOTSTRAP:-0}" == "1" ]]; then
  echo "[bootstrap] Python exec: $($PY -c 'import sys; print(sys.executable)')"
  $PY -m pip --version || true
fi

check_imports() {
  "$PY" - <<'PYCODE'
import importlib, sys
mods = ['requests','openai','psycopg2','dotenv']
missing = [m for m in mods if importlib.util.find_spec(m) is None]
if missing:
    print("[bootstrap] Missing:", ",".join(missing))
    sys.exit(1)
sys.exit(0)
PYCODE
}

# Instalar dependências se necessário (ou forçado)
if [[ "${FORCE_PIP_INSTALL:-0}" == "1" ]]; then
  echo "[bootstrap] Installing deps (forced)..."
  "$PY" -m pip install --no-input -r requirements.txt
elif ! check_imports; then
  echo "[bootstrap] Installing deps (missing detected)..."
  "$PY" -m pip install --no-input -r requirements.txt
else
  echo "[bootstrap] Deps OK."
fi

# Variáveis úteis (opcional)
export PIPELINE_DEBUG="${PIPELINE_DEBUG:-1}"

# Executar pipeline
exec "$PY" 00_pipeline.py
