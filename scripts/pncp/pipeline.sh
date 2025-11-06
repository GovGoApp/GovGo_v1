#!/usr/bin/env bash
# GovGo v1 — Pipeline PNCP (contratacao -> contrato)
# - Root deste script: scripts/pncp
# - Descobre Python, instala deps se necessário e executa 01/02/03 de cada domínio

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
mods = ['requests','openai','psycopg2','dotenv','rich']
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

# Exportar .env local (se existir)
set -a
if [[ -f ./.env ]]; then
  source ./.env
fi
set +a

# Variáveis úteis
export PIPELINE_DEBUG="${PIPELINE_DEBUG:-1}"
if [[ -z "${PIPELINE_TIMESTAMP:-}" ]]; then
  export PIPELINE_TIMESTAMP="$(date +%Y%m%d_%H%M%S)"
fi

# Execução: contratacao (01->02->03)
exec_step() {
  local title="$1"; shift
  echo "[run] $title: $*"
  if ! "$PY" "$@"; then
    echo "[run] FAIL: $title" >&2
    return 1
  fi
}

set +e
exec_step "contratacao/01_processing" contratacao/01_processing.py || exit 1
exec_step "contratacao/02_embeddings" contratacao/02_embeddings.py || exit 1
exec_step "contratacao/03_categorization" contratacao/03_categorization.py || exit 1

# Execução: contrato (01->02->03); 01 com --mode atualizacao --tipo diario
exec_step "contrato/01_processing" contrato/01_processing.py --mode atualizacao --tipo diario || exit 1
exec_step "contrato/02_embeddings" contrato/02_embeddings.py || exit 1
exec_step "contrato/03_categorization" contrato/03_categorization.py || exit 1
set -e

echo "[run] Pipeline PNCP finalizado com sucesso."