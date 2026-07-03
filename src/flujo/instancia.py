"""Garantiza una sola instancia de Flujo.

Con la app en Elementos de inicio y el launcher de Terminal conviviendo, es
fácil arrancar Flujo dos veces: dos escuchas de tecla pegarían el texto doble.
El candado es un archivo PID en ~/.flujo/.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path

from .config import ruta_base

log = logging.getLogger(__name__)


def _ruta_pid() -> Path:
    return ruta_base() / "flujo.pid"


def _proceso_vivo(pid: int) -> bool:
    try:
        os.kill(pid, 0)  # señal nula: solo comprueba existencia
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # existe, pero es de otro usuario
    except OSError:
        return False
    return True


def adquirir() -> int | None:
    """Reclama la instancia. Devuelve el PID del otro Flujo si ya hay uno vivo."""
    ruta = _ruta_pid()
    if ruta.exists():
        try:
            pid = int(ruta.read_text("utf-8").strip())
        except (ValueError, OSError):
            pid = None  # archivo corrupto: se reclama
        if pid is not None and pid != os.getpid() and _proceso_vivo(pid):
            return pid
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(str(os.getpid()), "utf-8")
    return None


def liberar() -> None:
    """Borra el archivo PID solo si le pertenece a este proceso."""
    ruta = _ruta_pid()
    try:
        if ruta.exists() and ruta.read_text("utf-8").strip() == str(os.getpid()):
            ruta.unlink()
    except OSError as exc:
        log.debug("No pude liberar el archivo PID: %s", exc)
