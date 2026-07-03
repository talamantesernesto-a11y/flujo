"""Retroalimentación sonora con los sonidos del sistema (no bloquea)."""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)

# Un solo sonido (Tink) para empezar y para confirmar el pegado: menos ruido.
_SONIDOS = {
    "inicio": "/System/Library/Sounds/Tink.aiff",
    "listo": "/System/Library/Sounds/Tink.aiff",
    "error": "/System/Library/Sounds/Basso.aiff",
}


def reproducir(nombre: str, activado: bool = True) -> None:
    if not activado:
        return
    ruta = _SONIDOS.get(nombre)
    if not ruta or not Path(ruta).exists():
        return
    try:
        subprocess.Popen(
            ["afplay", ruta],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as exc:
        log.debug("No pude reproducir el sonido %s: %s", nombre, exc)
