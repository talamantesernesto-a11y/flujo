"""Pruebas del state machine de la tecla global (sin pynput ni permisos).

Los handlers _al_presionar/_al_soltar no tocan pynput, así que se prueban
directamente inyectando una tecla falsa como objetivo.
"""
from __future__ import annotations

from flujo.hotkey import EscuchaTecla


class _TeclaFalsa:
    """Objeto tecla simulado; _coincide compara por identidad."""


class _AppFalsa:
    """Simula la app: acepta o rechaza iniciar según su estado."""

    def __init__(self, acepta_iniciar: bool = True) -> None:
        self.acepta_iniciar = acepta_iniciar
        self.inicios = 0
        self.paradas = 0

    def iniciar(self) -> bool:
        if not self.acepta_iniciar:
            return False
        self.inicios += 1
        return True

    def detener(self) -> bool:
        self.paradas += 1
        return True


def _preparar(modo: str, app: _AppFalsa) -> tuple[EscuchaTecla, _TeclaFalsa]:
    escucha = EscuchaTecla("alt_r", modo, app.iniciar, app.detener)
    tecla = _TeclaFalsa()
    escucha._objetivo = tecla  # evita importar pynput en las pruebas
    return escucha, tecla


def test_mantener_graba_mientras_se_presiona():
    app = _AppFalsa()
    escucha, tecla = _preparar("mantener", app)
    escucha._al_presionar(tecla)
    assert app.inicios == 1
    escucha._al_soltar(tecla)
    assert app.paradas == 1


def test_mantener_ignora_repeticiones_de_macos():
    app = _AppFalsa()
    escucha, tecla = _preparar("mantener", app)
    for _ in range(5):  # macOS repite key-down mientras se mantiene
        escucha._al_presionar(tecla)
    assert app.inicios == 1
    escucha._al_soltar(tecla)
    assert app.paradas == 1


def test_mantener_no_detiene_si_el_inicio_fue_rechazado():
    app = _AppFalsa(acepta_iniciar=False)
    escucha, tecla = _preparar("mantener", app)
    escucha._al_presionar(tecla)
    escucha._al_soltar(tecla)
    assert app.inicios == 0
    assert app.paradas == 0


def test_alternar_enciende_y_apaga():
    app = _AppFalsa()
    escucha, tecla = _preparar("alternar", app)
    escucha._al_presionar(tecla)
    escucha._al_soltar(tecla)
    assert (app.inicios, app.paradas) == (1, 0)
    escucha._al_presionar(tecla)
    escucha._al_soltar(tecla)
    assert (app.inicios, app.paradas) == (1, 1)


def test_alternar_no_se_desincroniza_si_la_app_rechaza_el_inicio():
    """El bug clásico: tocar la tecla mientras aún se transcribe no debe
    dejar la escucha creyendo que grabamos cuando no es así."""
    app = _AppFalsa()
    escucha, tecla = _preparar("alternar", app)

    # ciclo normal: enciende y apaga
    escucha._al_presionar(tecla)
    escucha._al_soltar(tecla)
    escucha._al_presionar(tecla)
    escucha._al_soltar(tecla)
    assert (app.inicios, app.paradas) == (1, 1)

    # la app está "procesando" y rechaza el inicio
    app.acepta_iniciar = False
    escucha._al_presionar(tecla)
    escucha._al_soltar(tecla)
    assert app.inicios == 1  # no arrancó nada

    # la app vuelve a estar lista: el siguiente toque debe INICIAR, no apagar
    app.acepta_iniciar = True
    escucha._al_presionar(tecla)
    escucha._al_soltar(tecla)
    assert (app.inicios, app.paradas) == (2, 1)


def test_callback_que_truena_cuenta_como_rechazo():
    def iniciar_roto():
        raise RuntimeError("micrófono ocupado")

    paradas = []
    escucha = EscuchaTecla("alt_r", "alternar", iniciar_roto, lambda: paradas.append(1))
    tecla = _TeclaFalsa()
    escucha._objetivo = tecla
    escucha._al_presionar(tecla)
    escucha._al_soltar(tecla)
    # el fallo no debe dejar la escucha "activa": el siguiente toque reintenta
    escucha._al_presionar(tecla)
    assert not paradas


def test_teclas_ajenas_se_ignoran():
    app = _AppFalsa()
    escucha, tecla = _preparar("mantener", app)
    escucha._al_presionar(_TeclaFalsa())
    escucha._al_soltar(_TeclaFalsa())
    assert (app.inicios, app.paradas) == (0, 0)
