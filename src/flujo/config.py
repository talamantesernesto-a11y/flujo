"""Configuración de Flujo: valores por defecto, validación y persistencia en JSON."""
from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Mapping

log = logging.getLogger(__name__)

MODELO_PREDETERMINADO = "mlx-community/whisper-large-v3-turbo"
MODOS_VALIDOS = ("mantener", "alternar")
INSERCIONES_VALIDAS = ("pegar", "teclear")
MOTORES_VALIDOS = ("whisper", "parakeet")

# Reemplazos iniciales: nombres propios que Whisper suele escribir mal al dictar.
DICCIONARIO_INICIAL = {
    "obra kit": "ObraKit",
    "obra ya": "ObraYA",
    "obraya": "ObraYA",
    "notarix": "Notarix",
    "vantem": "Vantem",
    "supabase": "Supabase",
    "su pavase": "Supabase",  # así suele oír Whisper "Supabase" en español
    "supa base": "Supabase",
    "whatsapp": "WhatsApp",
}


class ErrorConfig(ValueError):
    """La configuración es inválida o no se pudo leer."""


def ruta_base() -> Path:
    return Path(os.environ.get("FLUJO_HOME", str(Path.home() / ".flujo")))


def ruta_config() -> Path:
    return ruta_base() / "config.json"


@dataclass(frozen=True)
class ConfigPulido:
    """Pulido opcional del texto con un LLM local servido por Ollama."""

    activado: bool = False
    modelo: str = "qwen2.5:7b"
    url: str = "http://localhost:11434"
    timeout_segundos: float = 20.0


@dataclass(frozen=True)
class Config:
    idioma: str = "es"
    motor: str = "whisper"  # "whisper" (mejor puntuación) o "parakeet" (más rápido)
    modelo: str = MODELO_PREDETERMINADO
    tecla: str = "alt_r"
    modo: str = "mantener"  # "mantener" (push-to-talk) o "alternar" (toggle)
    insercion: str = "pegar"  # "pegar" (Cmd+V) o "teclear" (simula teclas)
    sonidos: bool = True
    comandos_dictado: bool = True  # "punto y aparte" → párrafo nuevo, etc.
    quitar_muletillas: bool = False
    muletillas: tuple[str, ...] = ("eh", "em", "mmm")
    diccionario: Mapping[str, str] = field(
        default_factory=lambda: dict(DICCIONARIO_INICIAL)
    )
    # Términos extra que el motor debe reconocer aunque no necesiten reemplazo
    # (nombres propios, tecnicismos). Se pasan a Whisper como glosario.
    vocabulario: tuple[str, ...] = ()
    pulido: ConfigPulido = field(default_factory=ConfigPulido)
    historial_max: int = 500


def _errores(config: Config) -> list[str]:
    errores: list[str] = []
    if config.modo not in MODOS_VALIDOS:
        errores.append(f"'modo' debe ser uno de {MODOS_VALIDOS}, no '{config.modo}'")
    if config.motor not in MOTORES_VALIDOS:
        errores.append(f"'motor' debe ser uno de {MOTORES_VALIDOS}, no '{config.motor}'")
    if config.insercion not in INSERCIONES_VALIDAS:
        errores.append(
            f"'insercion' debe ser una de {INSERCIONES_VALIDAS}, no '{config.insercion}'"
        )
    if not config.idioma or not (2 <= len(config.idioma) <= 5):
        errores.append(f"'idioma' debe ser un código como 'es', no '{config.idioma}'")
    if not config.modelo or not isinstance(config.modelo, str):
        errores.append("'modelo' debe ser un repo de Hugging Face o ruta local")
    if not config.tecla or not isinstance(config.tecla, str):
        errores.append("'tecla' debe ser el nombre de una tecla, p. ej. 'alt_r'")
    if not isinstance(config.historial_max, int) or config.historial_max < 1:
        errores.append("'historial_max' debe ser un entero positivo")
    if not isinstance(config.diccionario, Mapping) or not all(
        isinstance(k, str) and isinstance(v, str) for k, v in config.diccionario.items()
    ):
        errores.append("'diccionario' debe mapear texto dictado → texto correcto")
    return errores


def validar(config: Config) -> Config:
    errores = _errores(config)
    if errores:
        raise ErrorConfig(
            "Configuración inválida:\n  - " + "\n  - ".join(errores)
        )
    return config


def desde_dict(datos: Mapping[str, Any]) -> Config:
    """Construye una Config validada desde un dict (claves desconocidas se ignoran)."""
    base = Config()
    conocidas = set(asdict(base).keys())
    ignoradas = set(datos.keys()) - conocidas
    if ignoradas:
        log.warning("Claves desconocidas en config.json ignoradas: %s", sorted(ignoradas))

    campos = {k: v for k, v in datos.items() if k in conocidas}
    if "muletillas" in campos:
        campos["muletillas"] = tuple(str(m) for m in campos["muletillas"])
    if "vocabulario" in campos:
        campos["vocabulario"] = tuple(str(v) for v in campos["vocabulario"])
    if "pulido" in campos:
        if not isinstance(campos["pulido"], Mapping):
            raise ErrorConfig("'pulido' debe ser un objeto JSON")
        pulido_base = asdict(ConfigPulido())
        pulido = {k: v for k, v in campos["pulido"].items() if k in pulido_base}
        campos["pulido"] = ConfigPulido(**{**pulido_base, **pulido})
    try:
        config = Config(**{**asdict(base), "pulido": base.pulido, **campos})
    except TypeError as exc:
        raise ErrorConfig(f"Configuración con tipos inválidos: {exc}") from exc
    return validar(config)


def cargar() -> Config:
    """Lee ~/.flujo/config.json; si no existe, lo crea con los valores por defecto."""
    ruta = ruta_config()
    if not ruta.exists():
        config = Config()
        guardar(config)
        log.info("Configuración inicial creada en %s", ruta)
        return config
    try:
        datos = json.loads(ruta.read_text("utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ErrorConfig(f"No pude leer {ruta}: {exc}") from exc
    if not isinstance(datos, dict):
        raise ErrorConfig(f"{ruta} debe contener un objeto JSON")
    return desde_dict(datos)


def guardar(config: Config) -> Path:
    ruta = ruta_config()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(
        json.dumps(asdict(config), indent=2, ensure_ascii=False) + "\n", "utf-8"
    )
    return ruta
