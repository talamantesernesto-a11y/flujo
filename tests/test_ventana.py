"""Pruebas de la parte pura de la ventana (las filas de la tabla)."""
from flujo.ventana import filas_historial


def _entrada(fecha: str, texto: str) -> dict:
    return {"fecha": fecha, "duracion_segundos": 2.0, "crudo": texto, "texto": texto}


def test_filas_mas_recientes_primero():
    filas = filas_historial(
        [
            _entrada("2026-07-03T09:00:00", "primero"),
            _entrada("2026-07-03T13:45:10", "último"),
        ]
    )
    assert filas[0] == ("07-03 13:45", "último")
    assert filas[1] == ("07-03 09:00", "primero")


def test_saltos_de_linea_se_aplanan_para_la_tabla():
    filas = filas_historial([_entrada("2026-07-03T10:00:00", "uno.\n\ndos.")])
    assert filas[0][1] == "uno.  dos."


def test_entradas_sin_texto_se_omiten():
    filas = filas_historial(
        [
            _entrada("2026-07-03T10:00:00", ""),
            _entrada("2026-07-03T11:00:00", "válido"),
        ]
    )
    assert len(filas) == 1
    assert filas[0][1] == "válido"


def test_fecha_malformada_no_truena():
    filas = filas_historial([{"fecha": "raro", "texto": "hola"}])
    assert filas[0] == ("raro", "hola")


def test_historial_vacio_da_lista_vacia():
    assert filas_historial([]) == []
