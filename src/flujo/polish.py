"""Pulido opcional del texto con un LLM local vía Ollama.

Es el paso opcional de LLM del pipeline, corriendo en tu máquina.
Si Ollama no está instalado o falla, se conserva el texto original:
el dictado nunca se pierde por culpa del pulido.
"""
from __future__ import annotations

import json
import logging
from urllib.error import URLError
from urllib.request import Request, urlopen

from .config import ConfigPulido

log = logging.getLogger(__name__)

_PROMPT = (
    "Eres un corrector de textos dictados en español. Corrige puntuación, acentos y "
    "mayúsculas, elimina muletillas (eh, este, o sea, mmm) y palabras repetidas por "
    "error. NO cambies el significado, NO agregues ni quites información, NO "
    "traduzcas. Responde únicamente con el texto corregido, sin comillas ni "
    "explicaciones.\n\nTexto dictado: {texto}"
)


def ollama_disponible(url: str, timeout: float = 1.5) -> bool:
    try:
        with urlopen(f"{url}/api/tags", timeout=timeout) as respuesta:
            return respuesta.status == 200
    except (URLError, OSError, ValueError):
        return False


def _respuesta_sospechosa(original: str, pulido: str) -> bool:
    """Un buen pulido conserva el tamaño; si el LLM divagó, mejor el original."""
    return not pulido or len(pulido) > max(80, len(original) * 3)


def pulir(texto: str, config: ConfigPulido) -> str:
    if not texto.strip():
        return texto
    cuerpo = json.dumps(
        {
            "model": config.modelo,
            "prompt": _PROMPT.format(texto=texto),
            "stream": False,
            "options": {"temperature": 0.1},
        }
    ).encode("utf-8")
    peticion = Request(
        f"{config.url}/api/generate",
        data=cuerpo,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urlopen(peticion, timeout=config.timeout_segundos) as respuesta:
            datos = json.load(respuesta)
    except (URLError, OSError, ValueError, json.JSONDecodeError) as exc:
        log.warning("Pulido con Ollama falló, uso el texto sin pulir: %s", exc)
        return texto

    pulido = str(datos.get("response") or "").strip()
    if _respuesta_sospechosa(texto, pulido):
        log.warning("Respuesta de Ollama sospechosa, uso el texto sin pulir")
        return texto
    return pulido
