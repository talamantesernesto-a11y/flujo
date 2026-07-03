"""Pruebas de utilidades de audio (sin micrófono real)."""
import numpy as np
import pytest

from flujo import audio


def test_guardar_y_cargar_wav_conserva_la_senal(tmp_path):
    tono = np.sin(np.linspace(0, 440 * 2 * np.pi, audio.FRECUENCIA_WHISPER)).astype(
        np.float32
    ) * 0.5
    ruta = audio.guardar_wav(tono, tmp_path / "tono.wav")
    recuperado = audio.cargar_wav(ruta)
    assert recuperado.dtype == np.float32
    assert len(recuperado) == len(tono)
    assert np.allclose(recuperado, tono, atol=1e-3)


def test_duracion_segundos():
    un_segundo = np.zeros(audio.FRECUENCIA_WHISPER, dtype=np.float32)
    assert audio.duracion_segundos(un_segundo) == pytest.approx(1.0)


def test_cargar_wav_rechaza_frecuencia_incorrecta(tmp_path):
    import wave

    ruta = tmp_path / "malo.wav"
    with wave.open(str(ruta), "wb") as archivo:
        archivo.setnchannels(1)
        archivo.setsampwidth(2)
        archivo.setframerate(44100)
        archivo.writeframes(b"\x00\x00" * 100)
    with pytest.raises(audio.ErrorAudio, match="afconvert"):
        audio.cargar_wav(ruta)


def test_cargar_wav_inexistente_da_error_claro(tmp_path):
    with pytest.raises(audio.ErrorAudio, match="No pude leer"):
        audio.cargar_wav(tmp_path / "no-existe.wav")


def test_detener_sin_grabar_devuelve_audio_vacio():
    grabadora = audio.Grabadora()
    resultado = grabadora.detener()
    assert isinstance(resultado, np.ndarray)
    assert len(resultado) == 0
