"""Pruebas de configuración: defaults, persistencia, validación e inmutabilidad."""
import dataclasses
import json

import pytest

from flujo import config as cfg


def test_defaults_validos():
    config = cfg.validar(cfg.Config())
    assert config.idioma == "es"
    assert config.motor == "whisper"
    assert config.modo == "mantener"
    assert config.tecla == "alt_r"
    assert not config.pulido.activado


def test_config_es_inmutable():
    config = cfg.Config()
    with pytest.raises(dataclasses.FrozenInstanceError):
        config.idioma = "en"


def test_primer_arranque_crea_archivo(hogar_flujo_temporal):
    config = cfg.cargar()
    assert cfg.ruta_config().exists()
    assert config == cfg.Config()


def test_guardar_y_cargar_conserva_valores():
    original = dataclasses.replace(
        cfg.Config(), tecla="f13", modo="alternar", quitar_muletillas=True
    )
    cfg.guardar(original)
    cargada = cfg.cargar()
    assert cargada.tecla == "f13"
    assert cargada.modo == "alternar"
    assert cargada.quitar_muletillas is True


def test_desde_dict_ignora_claves_desconocidas():
    config = cfg.desde_dict({"idioma": "es", "clave_inventada": 1})
    assert config.idioma == "es"


def test_desde_dict_valida_modo_invalido():
    with pytest.raises(cfg.ErrorConfig, match="modo"):
        cfg.desde_dict({"modo": "apretar"})


def test_desde_dict_valida_motor_invalido():
    with pytest.raises(cfg.ErrorConfig, match="motor"):
        cfg.desde_dict({"motor": "siri"})


def test_desde_dict_construye_pulido_anidado():
    config = cfg.desde_dict({"pulido": {"activado": True, "modelo": "gemma3:4b"}})
    assert config.pulido.activado is True
    assert config.pulido.modelo == "gemma3:4b"
    assert config.pulido.url == "http://localhost:11434"


def test_json_corrupto_da_error_claro(hogar_flujo_temporal):
    ruta = cfg.ruta_config()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text("{esto no es json", "utf-8")
    with pytest.raises(cfg.ErrorConfig, match="No pude leer"):
        cfg.cargar()


def test_guardar_produce_json_legible():
    cfg.guardar(cfg.Config())
    datos = json.loads(cfg.ruta_config().read_text("utf-8"))
    assert datos["idioma"] == "es"
    assert datos["diccionario"]["obra kit"] == "ObraKit"
