#!/bin/bash
# Instala Flujo en una Mac nueva (Apple Silicon). Uso: ./instalar.sh
set -e
cd "$(dirname "$0")"

if [ "$(uname -m)" != "arm64" ]; then
    echo "❌ Flujo requiere una Mac con Apple Silicon (chip M1 o posterior)."
    exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
    echo "→ Instalando uv (gestor de Python de Astral)…"
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

echo "→ Instalando dependencias en .venv…"
uv sync

echo "→ Preparando Flujo.app (firma local y sin cuarentena)…"
chmod +x Flujo.app/Contents/MacOS/flujo flujo.sh
xattr -dr com.apple.quarantine Flujo.app 2>/dev/null || true
codesign --force -s - Flujo.app 2>/dev/null || true

echo
./flujo.sh doctor || true
echo
echo "✅ Instalación lista. Arranca con:  ./flujo.sh   (o doble clic en Flujo.app)"
echo "   • La primera vez se descarga el modelo de voz (~1.6 GB); después todo es offline."
echo "   • macOS pedirá permisos de Micrófono, Accesibilidad y Monitoreo de entrada"
echo "     (Ajustes del Sistema → Privacidad y seguridad)."
echo "   • Edita tu diccionario personal en ~/.flujo/config.json"
