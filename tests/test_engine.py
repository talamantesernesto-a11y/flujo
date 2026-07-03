"""Pruebas del glosario y del modo offline del motor."""
import dataclasses

from flujo.config import Config
from flujo.engine import activar_modo_offline_si_hay_cache, armar_glosario


def test_glosario_incluye_diccionario_y_vocabulario():
    config = dataclasses.replace(Config(), vocabulario=("Lanzza", "GuardIA"))
    glosario = armar_glosario(config)
    assert glosario.startswith("Glosario: ")
    for termino in ("ObraKit", "Supabase", "Lanzza", "GuardIA"):
        assert termino in glosario


def test_glosario_sin_terminos_devuelve_none():
    config = dataclasses.replace(Config(), diccionario={}, vocabulario=())
    assert armar_glosario(config) is None


def test_glosario_no_repite_terminos():
    config = dataclasses.replace(
        Config(), diccionario={"obra kit": "ObraKit"}, vocabulario=("ObraKit",)
    )
    assert armar_glosario(config).count("ObraKit") == 1


def test_glosario_se_recorta_si_es_enorme():
    config = dataclasses.replace(
        Config(), vocabulario=tuple(f"Termino{i}" for i in range(200))
    )
    assert len(armar_glosario(config)) <= 400


def test_modo_offline_solo_si_el_modelo_esta_en_cache(tmp_path):
    entorno: dict[str, str] = {}
    modelo = "mlx-community/whisper-large-v3-turbo"

    assert not activar_modo_offline_si_hay_cache(modelo, cache=tmp_path, entorno=entorno)
    assert "HF_HUB_OFFLINE" not in entorno  # sin cache: la descarga debe poder correr

    (tmp_path / "models--mlx-community--whisper-large-v3-turbo").mkdir()
    assert activar_modo_offline_si_hay_cache(modelo, cache=tmp_path, entorno=entorno)
    assert entorno["HF_HUB_OFFLINE"] == "1"


def test_modo_offline_respeta_variable_ya_definida(tmp_path):
    entorno = {"HF_HUB_OFFLINE": "0"}  # el usuario mandó lo contrario: se respeta
    (tmp_path / "models--mlx-community--whisper-large-v3-turbo").mkdir()
    activar_modo_offline_si_hay_cache(
        "mlx-community/whisper-large-v3-turbo", cache=tmp_path, entorno=entorno
    )
    assert entorno["HF_HUB_OFFLINE"] == "0"
