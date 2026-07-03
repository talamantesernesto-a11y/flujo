"""Captura de micrófono y utilidades WAV a 16 kHz mono (formato de Whisper)."""
from __future__ import annotations

import logging
import threading
import wave
from pathlib import Path

import numpy as np

log = logging.getLogger(__name__)

FRECUENCIA_WHISPER = 16000


class ErrorAudio(RuntimeError):
    """Problema con el micrófono o con un archivo de audio."""


class Grabadora:
    """Graba del micrófono por defecto mientras la tecla está presionada."""

    def __init__(self, frecuencia: int = FRECUENCIA_WHISPER) -> None:
        self._frecuencia = frecuencia
        self._bloques: list[np.ndarray] = []
        self._candado = threading.Lock()
        self._stream = None

    @property
    def grabando(self) -> bool:
        return self._stream is not None

    def iniciar(self) -> None:
        if self._stream is not None:
            return
        import sounddevice as sd  # import tardío: requiere PortAudio/micrófono

        with self._candado:
            self._bloques = []
        try:
            self._stream = sd.InputStream(
                samplerate=self._frecuencia,
                channels=1,
                dtype="float32",
                callback=self._recibir_bloque,
            )
            self._stream.start()
        except Exception as exc:
            self._stream = None
            raise ErrorAudio(
                "No pude abrir el micrófono. Revisa el permiso de Micrófono en "
                "Ajustes del Sistema → Privacidad y seguridad."
            ) from exc

    def _recibir_bloque(self, indata, cuadros, tiempo, estado) -> None:
        if estado:
            log.warning("Aviso de captura de audio: %s", estado)
        with self._candado:
            self._bloques.append(indata.copy())

    def detener(self) -> np.ndarray:
        """Detiene la captura y devuelve el audio como float32 mono."""
        stream, self._stream = self._stream, None
        if stream is not None:
            try:
                stream.stop()
                stream.close()
            except Exception as exc:
                log.warning("Error al cerrar el micrófono: %s", exc)
        with self._candado:
            bloques, self._bloques = self._bloques, []
        if not bloques:
            return np.zeros(0, dtype=np.float32)
        return np.concatenate(bloques).flatten().astype(np.float32)


def duracion_segundos(audio: np.ndarray, frecuencia: int = FRECUENCIA_WHISPER) -> float:
    return float(len(audio)) / float(frecuencia)


def cargar_wav(ruta: Path | str) -> np.ndarray:
    """Lee un WAV PCM 16-bit mono a 16 kHz y lo devuelve como float32 en [-1, 1]."""
    ruta = Path(ruta)
    try:
        with wave.open(str(ruta), "rb") as archivo:
            if archivo.getsampwidth() != 2:
                raise ErrorAudio(f"{ruta} debe ser PCM de 16 bits")
            if archivo.getframerate() != FRECUENCIA_WHISPER:
                raise ErrorAudio(
                    f"{ruta} está a {archivo.getframerate()} Hz; conviértelo con: "
                    f"afconvert -f WAVE -d LEI16@{FRECUENCIA_WHISPER} -c 1 entrada salida.wav"
                )
            crudo = archivo.readframes(archivo.getnframes())
            canales = archivo.getnchannels()
    except (wave.Error, OSError) as exc:
        raise ErrorAudio(f"No pude leer {ruta}: {exc}") from exc

    muestras = np.frombuffer(crudo, dtype=np.int16).astype(np.float32) / 32768.0
    if canales > 1:
        muestras = muestras.reshape(-1, canales).mean(axis=1)
    return muestras


def guardar_wav(audio: np.ndarray, ruta: Path | str) -> Path:
    """Escribe float32 [-1, 1] como WAV PCM 16-bit mono a 16 kHz."""
    ruta = Path(ruta)
    enteros = np.clip(audio * 32767.0, -32768, 32767).astype(np.int16)
    with wave.open(str(ruta), "wb") as archivo:
        archivo.setnchannels(1)
        archivo.setsampwidth(2)
        archivo.setframerate(FRECUENCIA_WHISPER)
        archivo.writeframes(enteros.tobytes())
    return ruta
