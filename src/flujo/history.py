"""Historial local de dictados en JSONL (~/.flujo/historial.jsonl).

Tu historial es un archivo tuyo, en tu disco, y de nadie más.
"""
from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from .config import ruta_base

log = logging.getLogger(__name__)

# Se recorta solo cuando el excedente ya es notorio, para no reescribir
# el archivo completo en cada dictado.
_MARGEN_RECORTE = 50


def ruta_historial() -> Path:
    return ruta_base() / "historial.jsonl"


def registrar(
    texto_crudo: str,
    texto_final: str,
    duracion_segundos: float,
    maximo: int = 500,
) -> None:
    entrada = {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "duracion_segundos": round(duracion_segundos, 1),
        "crudo": texto_crudo,
        "texto": texto_final,
    }
    ruta = ruta_historial()
    try:
        ruta.parent.mkdir(parents=True, exist_ok=True)
        with ruta.open("a", encoding="utf-8") as archivo:
            archivo.write(json.dumps(entrada, ensure_ascii=False) + "\n")
        _recortar(ruta, maximo)
    except OSError as exc:
        log.warning("No pude guardar el historial: %s", exc)


def leer(cantidad: int = 20) -> list[dict]:
    """Devuelve las últimas entradas (las líneas corruptas se ignoran)."""
    ruta = ruta_historial()
    if not ruta.exists():
        return []
    entradas: list[dict] = []
    try:
        lineas = ruta.read_text("utf-8").splitlines()
    except OSError as exc:
        log.warning("No pude leer el historial: %s", exc)
        return []
    for linea in lineas[-cantidad:]:
        try:
            dato = json.loads(linea)
            if isinstance(dato, dict):
                entradas.append(dato)
        except json.JSONDecodeError:
            continue
    return entradas


def _recortar(ruta: Path, maximo: int) -> None:
    lineas = ruta.read_text("utf-8").splitlines()
    if len(lineas) <= maximo + _MARGEN_RECORTE:
        return
    ruta.write_text("\n".join(lineas[-maximo:]) + "\n", "utf-8")
