"""App de barra de menús: une tecla global, grabadora, motor, formato y pegado."""
from __future__ import annotations

import logging
import subprocess
import threading

import rumps

import dataclasses

from . import history, sounds
from .audio import ErrorAudio, Grabadora, duracion_segundos
from .config import Config, guardar, ruta_base, ruta_config
from .engine import ErrorMotor, crear_motor
from .formatter import formatear
from .hotkey import ErrorTecla, EscuchaTecla, proceso_confiable
from .paster import ErrorInsercion, insertar
from .polish import ollama_disponible, pulir
from .ventana import VentanaFlujo

log = logging.getLogger(__name__)

_ICONOS = {
    "cargando": "⏳",
    "listo": "🎙️",
    "grabando": "🔴",
    "procesando": "✍️",
    "error": "⚠️",
}
_TEXTO_ESTADO = {
    "cargando": "Cargando modelo…",
    "listo": "Listo para dictar",
    "grabando": "Grabando…",
    "procesando": "Transcribiendo…",
    "error": "Error (ver menú)",
}
# Por debajo de esto se considera un toque accidental de la tecla.
_DURACION_MINIMA_SEGUNDOS = 0.3


def _notificar(titulo: str, mensaje: str) -> None:
    guion = (
        f'display notification "{mensaje.replace(chr(34), chr(39))}" '
        f'with title "{titulo.replace(chr(34), chr(39))}"'
    )
    try:
        subprocess.run(["osascript", "-e", guion], capture_output=True, timeout=5)
    except OSError as exc:
        log.debug("No pude mostrar la notificación: %s", exc)


class AppFlujo(rumps.App):
    def __init__(self, config: Config) -> None:
        super().__init__("Flujo", title=_ICONOS["cargando"], quit_button=None)
        self._config = config
        self._estado = "cargando"
        self._candado = threading.Lock()
        self._grabadora = Grabadora()
        # La app degrada a estado "error" en vez de morir: así el ícono de la
        # barra de menús aparece siempre y el usuario ve qué corregir.
        try:
            self._motor = crear_motor(config)
        except ErrorMotor as exc:
            self._motor = None
            self._estado = "error"
            log.error("Motor no disponible: %s", exc)
            _notificar("Flujo", str(exc))
        self._escucha = EscuchaTecla(
            config.tecla, config.modo, self._al_iniciar_dictado, self._al_detener_dictado
        )
        self._pulido_activo = config.pulido.activado and ollama_disponible(
            config.pulido.url
        )
        if config.pulido.activado and not self._pulido_activo:
            log.warning("Pulido activado en config pero Ollama no responde; sigo sin él")

        self._item_estado = rumps.MenuItem(_TEXTO_ESTADO["cargando"])
        motor_texto = self._motor.nombre if self._motor else "no disponible"
        pulido_texto = (
            f"Pulido: {config.pulido.modelo}" if self._pulido_activo else "Pulido: apagado"
        )
        self._ventana = VentanaFlujo(
            leer_sonidos=lambda: self._config.sonidos,
            al_cambiar_sonidos=self._cambiar_sonidos,
        )
        self.menu = [
            rumps.MenuItem("Abrir Flujo…", callback=self._abrir_ventana),
            None,
            self._item_estado,
            rumps.MenuItem(f"Tecla: {config.tecla} · modo {config.modo}"),
            rumps.MenuItem(f"Motor: {motor_texto}"),
            rumps.MenuItem(pulido_texto),
            None,
            rumps.MenuItem("Ver historial", callback=self._abrir_historial),
            rumps.MenuItem("Editar configuración", callback=self._abrir_config),
            None,
            rumps.MenuItem("Salir", callback=self._salir),
        ]
        rumps.Timer(self._refrescar_titulo, 0.3).start()
        if self._motor is not None:
            threading.Thread(target=self._precargar_modelo, daemon=True).start()
        try:
            self._escucha.iniciar()
        except ErrorTecla as exc:
            self._estado = "error"
            log.error("Tecla inválida: %s", exc)
            _notificar("Flujo", str(exc))
        if not proceso_confiable():
            log.warning("Sin permiso de Accesibilidad: la tecla global no funcionará")
            _notificar(
                "Flujo",
                "Falta el permiso de Accesibilidad: activa tu terminal en Ajustes "
                "→ Privacidad y seguridad → Accesibilidad y reinicia Flujo.",
            )

    # --- estado -----------------------------------------------------------
    def _fijar_estado(self, estado: str) -> None:
        with self._candado:
            self._estado = estado

    def _leer_estado(self) -> str:
        with self._candado:
            return self._estado

    def _refrescar_titulo(self, _temporizador) -> None:
        estado = self._leer_estado()
        self.title = _ICONOS.get(estado, "🎙️")
        self._item_estado.title = _TEXTO_ESTADO.get(estado, estado)

    # --- ciclo de dictado ---------------------------------------------------
    def _precargar_modelo(self) -> None:
        try:
            self._motor.cargar()
            self._fijar_estado("listo")
            log.info("Modelo listo: %s", self._motor.nombre)
        except Exception as exc:
            log.exception("No pude cargar el modelo")
            self._fijar_estado("error")
            _notificar("Flujo", f"No pude cargar el modelo: {exc}")

    def _al_iniciar_dictado(self) -> bool:
        """Devuelve False si no se pudo empezar: la tecla no cambia de estado."""
        if self._leer_estado() != "listo":
            sounds.reproducir("error", self._config.sonidos)
            return False
        try:
            self._grabadora.iniciar()
        except ErrorAudio as exc:
            self._fijar_estado("error")
            _notificar("Flujo", str(exc))
            return False
        self._fijar_estado("grabando")
        sounds.reproducir("inicio", self._config.sonidos)
        return True

    def _al_detener_dictado(self) -> bool:
        if not self._grabadora.grabando:
            return False
        audio = self._grabadora.detener()
        self._fijar_estado("procesando")
        threading.Thread(target=self._procesar, args=(audio,), daemon=True).start()
        return True

    def _procesar(self, audio) -> None:
        duracion = duracion_segundos(audio)
        try:
            if duracion < _DURACION_MINIMA_SEGUNDOS:
                self._fijar_estado("listo")
                return
            crudo = self._motor.transcribir(audio)
            texto = formatear(crudo, self._config)
            if texto and self._pulido_activo:
                texto = pulir(texto, self._config.pulido)
            if texto:
                insertar(texto, self._config)
                history.registrar(crudo, texto, duracion, self._config.historial_max)
                sounds.reproducir("listo", self._config.sonidos)
            self._fijar_estado("listo")
        except ErrorInsercion as exc:
            log.warning("Inserción falló: %s", exc)
            self._fijar_estado("listo")
            sounds.reproducir("error", self._config.sonidos)
            _notificar("Flujo", str(exc))
        except Exception as exc:
            log.exception("Falló el procesamiento del dictado")
            self._fijar_estado("listo")
            sounds.reproducir("error", self._config.sonidos)
            _notificar("Flujo", f"Error al transcribir: {exc}")

    # --- menú y ventana -------------------------------------------------------
    def _abrir_ventana(self, _item) -> None:
        try:
            self._ventana.mostrar()
        except Exception as exc:
            log.exception("No pude abrir la ventana")
            _notificar("Flujo", f"No pude abrir la ventana: {exc}")

    def _cambiar_sonidos(self, activado: bool) -> None:
        self._config = dataclasses.replace(self._config, sonidos=activado)
        guardar(self._config)
        log.info("Sonidos %s", "activados" if activado else "desactivados")

    def _abrir_historial(self, _item) -> None:
        ruta = history.ruta_historial()
        ruta.parent.mkdir(parents=True, exist_ok=True)
        ruta.touch(exist_ok=True)
        subprocess.run(["open", "-t", str(ruta)])

    def _abrir_config(self, _item) -> None:
        subprocess.run(["open", "-t", str(ruta_config())])

    def _salir(self, _item) -> None:
        self._escucha.detener()
        if self._grabadora.grabando:
            self._grabadora.detener()
        rumps.quit_application()
