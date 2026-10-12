#!/usr/bin/env bash
set -e

# Salamandra Local Runner Script
# Inicia todos los microservicios A2A de investigación en segundo plano

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "=================================================="
echo "🦎 INICIANDO SALAMANDRA (ENTORNO LOCAL)          "
echo "=================================================="

# 1. Verificar o crear entorno virtual
if [ ! -d "venv" ]; then
    echo "[*] Creando entorno virtual Python..."
    python3 -m venv venv
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install -r requirements.txt
fi

# 2. Verificar archivo .env
if [ ! -f ".env" ]; then
    if [ -f ".env.template" ]; then
        echo "[*] Generando archivo .env a partir de .env.template..."
        cp .env.template .env
    else
        echo "❌ Error: No se encontró .env ni .env.template"
        exit 1
    fi
fi

# 3. Lanzar flota de agentes con el runner multiproceso
PYTHON_EXEC="$SCRIPT_DIR/venv/bin/python"
if [ ! -f "$PYTHON_EXEC" ]; then
    PYTHON_EXEC="python3"
fi

echo "[*] Levantando microservicios A2A de Salamandra..."
exec "$PYTHON_EXEC" run_salamandra.py
