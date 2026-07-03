#!/bin/bash
# Lanza Flujo (dictado local en español). Uso: ./flujo.sh [correr|probar|archivo|doctor|config]
# Al arrancar desde Finder/Elementos de inicio el PATH es mínimo: uv y homebrew van aquí.
export PATH="$HOME/.local/bin:/opt/homebrew/bin:$PATH"
cd "$(dirname "$0")" && exec uv run python -m flujo "$@"
