"""Inserta el texto dictado en la app activa.

Método principal: guardar el portapapeles, poner el
texto, simular Cmd+V y restaurar el portapapeles. Alternativa: teclear el
texto carácter por carácter (no toca el portapapeles, pero es más lento).
Requiere el permiso de Accesibilidad para la app que corre Flujo.
"""
from __future__ import annotations

import logging
import subprocess
import time

from .config import Config

log = logging.getLogger(__name__)

# Pausas para que la app receptora alcance a ver el portapapeles nuevo antes
# del Cmd+V, y a procesar el pegado antes de restaurar el portapapeles.
_PAUSA_ANTES_DE_PEGAR = 0.15
_PAUSA_ANTES_DE_RESTAURAR = 0.40


class ErrorInsercion(RuntimeError):
    """No se pudo insertar el texto; queda en el portapapeles como respaldo."""


def obtener_portapapeles() -> str:
    resultado = subprocess.run(["pbpaste"], capture_output=True, timeout=5)
    return resultado.stdout.decode("utf-8", "replace")


def poner_portapapeles(texto: str) -> None:
    resultado = subprocess.run(["pbcopy"], input=texto.encode("utf-8"), timeout=5)
    if resultado.returncode != 0:
        raise ErrorInsercion("pbcopy falló al escribir el portapapeles")


def _simular_cmd_v() -> None:
    from pynput.keyboard import Controller, Key

    teclado = Controller()
    with teclado.pressed(Key.cmd):
        teclado.press("v")
        teclado.release("v")


def pegar(texto: str, restaurar: bool = True) -> None:
    anterior = obtener_portapapeles() if restaurar else ""
    poner_portapapeles(texto)
    time.sleep(_PAUSA_ANTES_DE_PEGAR)
    _simular_cmd_v()
    if restaurar:
        time.sleep(_PAUSA_ANTES_DE_RESTAURAR)
        poner_portapapeles(anterior)


def teclear(texto: str) -> None:
    from pynput.keyboard import Controller

    Controller().type(texto)


def insertar(texto: str, config: Config) -> None:
    """Inserta el texto según la configuración; ante un fallo lo deja copiado."""
    if not texto:
        return
    try:
        if config.insercion == "teclear":
            teclear(texto)
        else:
            pegar(texto)
    except Exception as exc:
        try:
            poner_portapapeles(texto)
            respaldo = "El texto completo quedó copiado: pégalo con Cmd+V."
        except Exception:
            respaldo = "Tampoco pude copiarlo al portapapeles."
        if config.insercion == "teclear":
            # El tecleo escribe carácter por carácter: pudo quedar un
            # fragmento ya escrito en la app antes de fallar.
            respaldo = "Puede que una parte ya se haya escrito. " + respaldo
        raise ErrorInsercion(
            "No pude insertar el texto (¿falta el permiso de Accesibilidad?). "
            + respaldo
        ) from exc
