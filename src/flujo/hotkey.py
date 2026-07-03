"""Tecla global de dictado (push-to-talk).

Modo "mantener": presiona para grabar, suelta para transcribir.
Modo "alternar": un toque enciende, otro apaga.
Requiere permisos de Accesibilidad y Monitoreo de Entrada.

Los callbacks pueden devolver False para rechazar la transición (p. ej. si la
app todavía está transcribiendo); en ese caso el estado interno no cambia y
el siguiente toque vuelve a intentar lo mismo, sin desincronizarse.
"""
from __future__ import annotations

import logging
import threading
from typing import Callable

log = logging.getLogger(__name__)


class ErrorTecla(RuntimeError):
    """La tecla configurada no existe o el listener no pudo arrancar."""


def _resolver_tecla(nombre: str):
    from pynput.keyboard import Key, KeyCode

    tecla = getattr(Key, nombre, None)
    if tecla is not None:
        return tecla
    if len(nombre) == 1:
        return KeyCode.from_char(nombre)
    raise ErrorTecla(
        f"No conozco la tecla '{nombre}'. Usa nombres de pynput como "
        "'alt_r', 'alt_l', 'cmd_r', 'ctrl_r', 'f13', o un carácter."
    )


def proceso_confiable() -> bool:
    """True si macOS ya dio el permiso de Accesibilidad a este proceso.

    Sin ese permiso, pynput arranca sin error pero nunca entrega eventos:
    hay que avisarle al usuario en vez de fallar en silencio.
    """
    try:
        import HIServices

        return bool(HIServices.AXIsProcessTrusted())
    except Exception:  # si no se puede comprobar, no alarmar de más
        return True


class EscuchaTecla:
    """Escucha global de la tecla de dictado."""

    def __init__(
        self,
        tecla: str,
        modo: str,
        al_iniciar: Callable[[], bool | None],
        al_detener: Callable[[], bool | None],
    ) -> None:
        self._nombre_tecla = tecla
        self._modo = modo
        self._al_iniciar = al_iniciar
        self._al_detener = al_detener
        self._objetivo = None
        self._listener = None
        self._activa = False
        self._presionada = False
        self._candado = threading.Lock()

    def iniciar(self) -> None:
        from pynput import keyboard

        self._objetivo = _resolver_tecla(self._nombre_tecla)
        self._listener = keyboard.Listener(
            on_press=self._al_presionar, on_release=self._al_soltar
        )
        self._listener.start()

    def detener(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None

    def _coincide(self, tecla) -> bool:
        if tecla == self._objetivo:
            return True
        # pynput a veces entrega KeyCode con el mismo carácter pero otro objeto.
        char = getattr(tecla, "char", None)
        objetivo_char = getattr(self._objetivo, "char", None)
        return char is not None and char == objetivo_char

    def _invocar(self, callback: Callable[[], bool | None]) -> bool:
        """Ejecuta el callback; None cuenta como aceptado, False como rechazo."""
        try:
            resultado = callback()
        except Exception:
            log.exception("Error en el callback de dictado")
            return False
        return resultado is not False

    def _al_presionar(self, tecla) -> None:
        if not self._coincide(tecla):
            return
        with self._candado:
            if self._presionada:  # macOS repite el evento mientras se mantiene
                return
            self._presionada = True
            activa = self._activa
        if not activa:
            if self._invocar(self._al_iniciar):
                with self._candado:
                    self._activa = True
        elif self._modo == "alternar":
            if self._invocar(self._al_detener):
                with self._candado:
                    self._activa = False

    def _al_soltar(self, tecla) -> None:
        if not self._coincide(tecla):
            return
        with self._candado:
            self._presionada = False
            if self._modo != "mantener" or not self._activa:
                return
            # En "mantener", soltar siempre termina el dictado, acepte o no el
            # callback: así el estado se auto-corrige en el siguiente intento.
            self._activa = False
        self._invocar(self._al_detener)
