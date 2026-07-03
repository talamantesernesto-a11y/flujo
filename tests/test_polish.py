"""Pruebas del pulido con Ollama (con la red simulada: nada sale de la máquina)."""
import io
import json

import pytest

from flujo import polish
from flujo.config import ConfigPulido


CONFIG = ConfigPulido(activado=True)


class _RespuestaFalsa(io.BytesIO):
    status = 200

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _simular_ollama(monkeypatch, respuesta_texto: str):
    cuerpo = json.dumps({"response": respuesta_texto}).encode("utf-8")

    def urlopen_falso(peticion, timeout=None):
        return _RespuestaFalsa(cuerpo)

    monkeypatch.setattr(polish, "urlopen", urlopen_falso)


def test_pulir_devuelve_texto_del_modelo(monkeypatch):
    _simular_ollama(monkeypatch, "El proyecto va bien.")
    assert polish.pulir("eh el proyecto va bien", CONFIG) == "El proyecto va bien."


def test_pulir_conserva_original_si_ollama_falla(monkeypatch):
    def urlopen_roto(peticion, timeout=None):
        raise OSError("conexión rechazada")

    monkeypatch.setattr(polish, "urlopen", urlopen_roto)
    assert polish.pulir("texto original", CONFIG) == "texto original"


def test_pulir_conserva_original_si_respuesta_vacia(monkeypatch):
    _simular_ollama(monkeypatch, "")
    assert polish.pulir("texto original", CONFIG) == "texto original"


def test_pulir_conserva_original_si_el_modelo_divaga(monkeypatch):
    _simular_ollama(monkeypatch, "Claro, aquí tienes: " + "bla " * 200)
    assert polish.pulir("hola", CONFIG) == "hola"


def test_texto_vacio_no_llama_a_ollama(monkeypatch):
    def urlopen_prohibido(*args, **kwargs):
        raise AssertionError("no debería llamar a la red con texto vacío")

    monkeypatch.setattr(polish, "urlopen", urlopen_prohibido)
    assert polish.pulir("   ", CONFIG) == "   "


def test_ollama_disponible_falso_sin_servidor(monkeypatch):
    def urlopen_roto(url, timeout=None):
        raise OSError("sin servidor")

    monkeypatch.setattr(polish, "urlopen", urlopen_roto)
    assert polish.ollama_disponible("http://localhost:11434") is False
