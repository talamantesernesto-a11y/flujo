"""Prueba de integración sin micrófono: voz sintética en español → Whisper → texto.

Genera audio con la voz del sistema (es_MX/es_ES), lo convierte a WAV 16 kHz
y lo pasa por el pipeline completo (motor + formato). Descarga el modelo la
primera vez, por eso está marcada como `integracion`:

    uv run pytest -m integracion -s
"""
import os
import subprocess

import pytest

from flujo.audio import cargar_wav
from flujo.config import Config
from flujo.engine import MotorWhisperMLX
from flujo.formatter import formatear

FRASE = "Hola, esto es una prueba de dictado en español para el proyecto."
PALABRAS_ESPERADAS = ("prueba", "dictado", "proyecto")


def _voz_en_espanol() -> str | None:
    listado = subprocess.run(["say", "-v", "?"], capture_output=True, text=True)
    for preferida in ("Paulina", "Mónica", "Monica"):
        if preferida in listado.stdout:
            return preferida
    for linea in listado.stdout.splitlines():
        if "es_MX" in linea or "es_ES" in linea:
            return linea.split()[0]
    return None


@pytest.mark.integracion
def test_dictado_completo_con_voz_sintetica(tmp_path):
    voz = _voz_en_espanol()
    if voz is None:
        pytest.skip("No hay voces en español instaladas en macOS")

    aiff = tmp_path / "frase.aiff"
    wav = tmp_path / "frase.wav"
    subprocess.run(["say", "-v", voz, "-o", str(aiff), FRASE], check=True)
    subprocess.run(
        ["afconvert", "-f", "WAVE", "-d", "LEI16@16000", "-c", "1", str(aiff), str(wav)],
        check=True,
    )

    modelo = os.environ.get("FLUJO_TEST_MODEL", "mlx-community/whisper-large-v3-turbo")
    motor = MotorWhisperMLX(modelo, "es")
    crudo = motor.transcribir(cargar_wav(wav))
    print(f"\nVoz: {voz} | Modelo: {modelo}\nCrudo: {crudo}")

    minusculas = crudo.lower()
    encontradas = [p for p in PALABRAS_ESPERADAS if p in minusculas]
    assert len(encontradas) >= 2, f"Transcripción irreconocible: {crudo!r}"

    final = formatear(crudo, Config())
    assert final[0].isupper() or not final[0].isalpha()
    assert final.endswith((".", "!", "?"))
