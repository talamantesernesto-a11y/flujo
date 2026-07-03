# Flujo

Dictado por voz 100% local para macOS en español (Whisper + MLX, app de barra de menús).
Python 3.12 + uv. Todo el código, nombres y mensajes están en español.

## Comandos

```bash
uv sync                          # instalar dependencias
uv run pytest                    # pruebas unitarias (rápidas)
uv run pytest -m integracion -s  # E2E con voz sintética (descarga modelo)
./flujo.sh                       # correr la app de barra de menús
./flujo.sh doctor                # diagnóstico
```

## Arquitectura

Pipeline: `hotkey` (pynput, push-to-talk) → `audio` (sounddevice 16 kHz) →
`engine` (mlx-whisper large-v3-turbo; parakeet-mlx opcional) → `formatter`
(diccionario personal, comandos de dictado, puntuación — funciones puras) →
`polish` (Ollama opcional, conserva el original si falla) → `paster`
(portapapeles + Cmd+V simulado, restaura) → `history` (JSONL local).
`app.py` (rumps) orquesta; `__main__.py` es la CLI.

Estado del usuario en `~/.flujo/` (override con env `FLUJO_HOME`, así se aíslan
las pruebas). Config inmutable (dataclasses frozen); usar `dataclasses.replace`.

## Reglas del proyecto

- Nada de red salvo: descarga inicial del modelo (Hugging Face) y Ollama en localhost.
- Los errores de pulido/inserción nunca tiran la app ni pierden el texto dictado.
- Español en identificadores y mensajes; los tests usan `FLUJO_HOME` temporal (conftest).
