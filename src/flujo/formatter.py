"""Limpieza y formato del texto dictado. Solo reglas locales, sin red.

Es el paso de formateo del pipeline: diccionario personal, comandos de
dictado, muletillas y puntuación.
Todas las funciones son puras: reciben texto y devuelven texto nuevo.
"""
from __future__ import annotations

import re
from typing import Iterable, Mapping

from .config import Config

# Comandos hablados de dictado. Se consumen junto con la
# puntuación que Whisper les pega alrededor ("..., punto y aparte, ...").
# "Punto y aparte" cierra la oración con punto, como en el dictado escolar.
_COMANDOS = (
    (re.compile(r"[.,;]?\s*\bpunto y aparte\b[.,;]?\s*", re.IGNORECASE), ".\n\n"),
    (
        re.compile(
            r"[.,;]?\s*\b(?:nueva l[ií]nea|salto de l[ií]nea)\b[.,;]?\s*",
            re.IGNORECASE,
        ),
        "\n",
    ),
)

# "¿listo? punto y aparte" produciría "?.": se conserva el signo original.
_PUNTUACION_DUPLICADA = re.compile(r"([.!?…])\.(?=\s|$)")

_FIN_DE_ORACION = ".!?…:\n»)\"'"


def colapsar_espacios(texto: str) -> str:
    sin_tabs = re.sub(r"[ \t]+", " ", texto)
    sin_bordes = re.sub(r" *\n *", "\n", sin_tabs)
    return sin_bordes.strip()


def aplicar_diccionario(texto: str, diccionario: Mapping[str, str]) -> str:
    """Reemplaza términos del diccionario personal (palabra completa, sin mayúsculas)."""
    resultado = texto
    for dictado in sorted(diccionario, key=len, reverse=True):
        patron = re.compile(rf"\b{re.escape(dictado)}\b", re.IGNORECASE)
        resultado = patron.sub(diccionario[dictado], resultado)
    return resultado


def quitar_muletillas(texto: str, muletillas: Iterable[str]) -> str:
    resultado = texto
    for muleta in muletillas:
        patron = re.compile(rf"(?<!\w){re.escape(muleta)}(?!\w)[,.]?\s*", re.IGNORECASE)
        resultado = patron.sub("", resultado)
    resultado = re.sub(r"\s+([,.;:!?])", r"\1", resultado)
    return colapsar_espacios(resultado)


def aplicar_comandos(texto: str) -> str:
    resultado = texto
    for patron, reemplazo in _COMANDOS:
        resultado = patron.sub(reemplazo, resultado)
    return _PUNTUACION_DUPLICADA.sub(r"\1", resultado)


def capitalizar_lineas(texto: str) -> str:
    """Pone en mayúscula la primera letra de cada línea (respeta '¿' y '¡')."""
    lineas = []
    for linea in texto.split("\n"):
        for i, caracter in enumerate(linea):
            if caracter.isalpha():
                linea = linea[:i] + caracter.upper() + linea[i + 1 :]
                break
        lineas.append(linea)
    return "\n".join(lineas)


def asegurar_puntuacion_final(texto: str) -> str:
    if texto and texto[-1] not in _FIN_DE_ORACION and texto[-1] != ",":
        return texto + "."
    if texto and texto[-1] == ",":
        return texto[:-1] + "."
    return texto


def formatear(texto: str, config: Config) -> str:
    """Pipeline completo de formato local. Devuelve "" si no hay nada que decir."""
    limpio = colapsar_espacios(texto)
    if not limpio:
        return ""
    limpio = aplicar_diccionario(limpio, config.diccionario)
    if config.quitar_muletillas:
        limpio = quitar_muletillas(limpio, config.muletillas)
    if config.comandos_dictado:
        limpio = aplicar_comandos(limpio)
    limpio = colapsar_espacios(limpio)
    if not limpio:
        return ""
    limpio = capitalizar_lineas(limpio)
    return asegurar_puntuacion_final(limpio)
