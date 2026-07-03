"""Pruebas del historial local JSONL."""
from flujo import history


def test_historial_vacio_devuelve_lista_vacia():
    assert history.leer() == []


def test_registrar_y_leer():
    history.registrar("hola crudo", "Hola final.", 2.5)
    entradas = history.leer()
    assert len(entradas) == 1
    assert entradas[0]["crudo"] == "hola crudo"
    assert entradas[0]["texto"] == "Hola final."
    assert entradas[0]["duracion_segundos"] == 2.5
    assert "fecha" in entradas[0]


def test_leer_devuelve_las_ultimas():
    for i in range(30):
        history.registrar(f"crudo {i}", f"texto {i}", 1.0)
    entradas = history.leer(cantidad=5)
    assert len(entradas) == 5
    assert entradas[-1]["texto"] == "texto 29"


def test_lineas_corruptas_se_ignoran():
    history.registrar("bueno", "Bueno.", 1.0)
    with history.ruta_historial().open("a", encoding="utf-8") as archivo:
        archivo.write("esto no es json\n")
    entradas = history.leer()
    assert len(entradas) == 1


def test_recorte_mantiene_las_ultimas_entradas():
    # margen de recorte = 50: con maximo=10 se recorta al pasar de 60 líneas
    for i in range(70):
        history.registrar(f"crudo {i}", f"texto {i}", 1.0, maximo=10)
    lineas = history.ruta_historial().read_text("utf-8").splitlines()
    assert len(lineas) <= 60 + 1
    entradas = history.leer(cantidad=200)
    assert entradas[-1]["texto"] == "texto 69"
