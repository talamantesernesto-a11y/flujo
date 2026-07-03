"""Motores de transcripción locales para Apple Silicon.

- "whisper": mlx-whisper con large-v3-turbo. Puntuación y acentos excelentes
  en español; ~1 s por dictado en chips M. Es el predeterminado.
- "parakeet": parakeet-mlx (NVIDIA Parakeet TDT 0.6B v3). Casi instantáneo y
  con detección automática español/inglés, pero puntuación más simple.
  Requiere instalarlo aparte: `uv add parakeet-mlx`.
"""
from __future__ import annotations

import logging
import os
import platform
import tempfile
from pathlib import Path
from typing import MutableMapping, Protocol

import numpy as np

from .config import Config
from . import audio as audio_util

log = logging.getLogger(__name__)

PARAKEET_PREDETERMINADO = "mlx-community/parakeet-tdt-0.6b-v3"
# Whisper acepta ~224 tokens de contexto; con esto sobra para un glosario.
_LARGO_MAXIMO_GLOSARIO = 400


def armar_glosario(config: Config) -> str | None:
    """Contexto que sesga a Whisper hacia tus términos (marcas, tecnicismos).

    Junta los valores del diccionario personal y la lista `vocabulario` de la
    configuración: así "Supabase" u "ObraKit" se transcriben bien a la primera,
    sin esperar a que el reemplazo de texto los corrija después.
    """
    terminos = list(dict.fromkeys([*config.diccionario.values(), *config.vocabulario]))
    if not terminos:
        return None
    return ("Glosario: " + ", ".join(terminos) + ".")[:_LARGO_MAXIMO_GLOSARIO]


class ErrorMotor(RuntimeError):
    """El motor de transcripción no está disponible o falló."""


class Motor(Protocol):
    nombre: str

    def cargar(self) -> None: ...

    def transcribir(self, audio: np.ndarray) -> str: ...


class MotorWhisperMLX:
    """Whisper vía MLX (GPU de Apple Silicon)."""

    def __init__(self, modelo: str, idioma: str, glosario: str | None = None) -> None:
        self.nombre = f"whisper ({modelo})"
        self._modelo = modelo
        self._idioma = idioma
        self._glosario = glosario
        self._mlx = None

    def cargar(self) -> None:
        """Descarga el modelo si hace falta y calienta los pesos con silencio."""
        self._importar()
        self.transcribir(np.zeros(8000, dtype=np.float32))

    def _importar(self):
        if self._mlx is None:
            try:
                import mlx_whisper
            except ImportError as exc:
                raise ErrorMotor(
                    "mlx-whisper no está instalado; corre `uv sync` en el proyecto."
                ) from exc
            self._mlx = mlx_whisper
        return self._mlx

    def transcribir(self, audio: np.ndarray | str) -> str:
        mlx = self._importar()
        try:
            resultado = mlx.transcribe(
                audio,
                path_or_hf_repo=self._modelo,
                language=self._idioma,
                condition_on_previous_text=False,
                initial_prompt=self._glosario,
            )
        except Exception as exc:
            raise ErrorMotor(f"La transcripción con {self.nombre} falló: {exc}") from exc
        return str(resultado.get("text") or "").strip()


class MotorParakeetMLX:
    """Parakeet TDT vía MLX. Escribe un WAV temporal porque su API recibe rutas."""

    def __init__(self, modelo: str) -> None:
        self.nombre = f"parakeet ({modelo})"
        self._repo = modelo
        self._modelo = None

    def cargar(self) -> None:
        if self._modelo is not None:
            return
        try:
            from parakeet_mlx import from_pretrained
        except ImportError as exc:
            raise ErrorMotor(
                "El motor 'parakeet' requiere el paquete parakeet-mlx. "
                "Instálalo con: uv add parakeet-mlx"
            ) from exc
        self._modelo = from_pretrained(self._repo)

    def transcribir(self, audio: np.ndarray | str) -> str:
        if self._modelo is None:
            self.cargar()
        try:
            if isinstance(audio, str):
                resultado = self._modelo.transcribe(audio)
            else:
                with tempfile.NamedTemporaryFile(suffix=".wav", delete=True) as temporal:
                    audio_util.guardar_wav(audio, temporal.name)
                    resultado = self._modelo.transcribe(temporal.name)
        except Exception as exc:
            raise ErrorMotor(f"La transcripción con {self.nombre} falló: {exc}") from exc
        return str(getattr(resultado, "text", "") or "").strip()


def activar_modo_offline_si_hay_cache(
    modelo: str,
    cache: Path | None = None,
    entorno: MutableMapping[str, str] = os.environ,
) -> bool:
    """Si el modelo ya está en disco, evita toda llamada a huggingface.co.

    Debe correr antes de importar mlx_whisper/huggingface_hub (que leen la
    variable al importarse). Si el modelo aún no se descarga, no hace nada
    para no bloquear la descarga inicial.
    """
    if cache is None:
        cache = Path.home() / ".cache" / "huggingface" / "hub"
    descargado = (cache / ("models--" + modelo.replace("/", "--"))).exists()
    if descargado:
        entorno.setdefault("HF_HUB_OFFLINE", "1")
    return descargado


def crear_motor(config: Config) -> Motor:
    if platform.machine() != "arm64":
        raise ErrorMotor(
            "Flujo usa MLX y requiere una Mac con Apple Silicon (chip M)."
        )
    if config.motor == "parakeet":
        repo = config.modelo if "parakeet" in config.modelo else PARAKEET_PREDETERMINADO
        activar_modo_offline_si_hay_cache(repo)
        return MotorParakeetMLX(repo)
    activar_modo_offline_si_hay_cache(config.modelo)
    return MotorWhisperMLX(config.modelo, config.idioma, armar_glosario(config))
