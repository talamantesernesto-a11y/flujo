"""Ventana de Flujo: sonidos on/off y últimos dictados.

Es un panel nativo de AppKit que vive dentro del mismo proceso de la app de
barra de menús. Doble clic en un dictado (o el botón Copiar) lo deja en el
portapapeles, por si el pegado automático no cayó donde querías.
Todo aquí debe ejecutarse en el hilo principal (los callbacks de rumps lo son).
"""
from __future__ import annotations

import logging
from typing import Callable

log = logging.getLogger(__name__)

MAX_FILAS = 30


def filas_historial(entradas: list[dict]) -> list[tuple[str, str]]:
    """Convierte el historial en filas (cuándo, texto), de lo más reciente a lo más viejo."""
    filas: list[tuple[str, str]] = []
    for entrada in reversed(entradas):
        texto = str(entrada.get("texto", "")).replace("\n", " ").strip()
        if not texto:
            continue
        fecha = str(entrada.get("fecha", ""))
        # "2026-07-03T13:45:10" → "03 jul · 13:45" simplificado a "07-03 13:45"
        cuando = f"{fecha[5:10]} {fecha[11:16]}" if len(fecha) >= 16 else fecha
        filas.append((cuando, texto))
    return filas


_clase_controlador = None


def _obtener_clase_controlador():
    """Define (una sola vez) la clase Objective-C que maneja la tabla y acciones."""
    global _clase_controlador
    if _clase_controlador is not None:
        return _clase_controlador

    import Foundation

    class _ControladorFlujo(Foundation.NSObject):
        # -- datasource de la tabla --------------------------------------
        def numberOfRowsInTableView_(self, _tabla):
            return len(self.filas)

        def tableView_objectValueForTableColumn_row_(self, _tabla, columna, fila):
            cuando, texto = self.filas[fila]
            return cuando if columna.identifier() == "cuando" else texto

        # -- acciones ------------------------------------------------------
        def copiar_(self, _boton):
            self._copiarFila_(self.tabla.selectedRow())

        def dobleClic_(self, _tabla):
            self._copiarFila_(self.tabla.clickedRow())

        def alternarSonidos_(self, interruptor):
            try:
                self.al_cambiar_sonidos(bool(interruptor.state()))
            except Exception:
                log.exception("No pude guardar el cambio de sonidos")

        def _copiarFila_(self, fila):
            if fila < 0 or fila >= len(self.filas):
                self.estado.setStringValue_("Selecciona un dictado primero")
                return
            from .paster import poner_portapapeles

            try:
                poner_portapapeles(self.filas[fila][1])
                self.estado.setStringValue_("Copiado ✓  pégalo con Cmd+V")
            except Exception:
                log.exception("No pude copiar el dictado")
                self.estado.setStringValue_("No pude copiar, revisa el registro")

    _clase_controlador = _ControladorFlujo
    return _clase_controlador


class VentanaFlujo:
    """Crea (perezosamente) y muestra la ventana; se reutiliza al cerrarla."""

    def __init__(
        self,
        leer_sonidos: Callable[[], bool],
        al_cambiar_sonidos: Callable[[bool], None],
    ) -> None:
        self._leer_sonidos = leer_sonidos
        self._al_cambiar_sonidos = al_cambiar_sonidos
        self._ventana = None
        self._controlador = None

    def mostrar(self) -> None:
        import AppKit

        from . import history

        if self._ventana is None:
            self._construir()
        self._controlador.filas = filas_historial(history.leer(MAX_FILAS))
        self._controlador.tabla.reloadData()
        self._controlador.interruptor.setState_(1 if self._leer_sonidos() else 0)
        self._controlador.estado.setStringValue_("")
        self._ventana.makeKeyAndOrderFront_(None)
        AppKit.NSApp.activateIgnoringOtherApps_(True)

    def _construir(self) -> None:
        import AppKit

        controlador = _obtener_clase_controlador().alloc().init()
        controlador.filas = []
        controlador.al_cambiar_sonidos = self._al_cambiar_sonidos

        estilo = (
            AppKit.NSWindowStyleMaskTitled
            | AppKit.NSWindowStyleMaskClosable
            | AppKit.NSWindowStyleMaskMiniaturizable
        )
        ventana = AppKit.NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            AppKit.NSMakeRect(0, 0, 540, 440), estilo, AppKit.NSBackingStoreBuffered, False
        )
        ventana.setTitle_("Flujo — dictado local")
        ventana.setReleasedWhenClosed_(False)
        ventana.center()
        contenido = ventana.contentView()

        interruptor = AppKit.NSButton.alloc().initWithFrame_(
            AppKit.NSMakeRect(20, 398, 320, 24)
        )
        interruptor.setButtonType_(AppKit.NSButtonTypeSwitch)
        interruptor.setTitle_("Reproducir sonidos al dictar")
        interruptor.setTarget_(controlador)
        interruptor.setAction_("alternarSonidos:")
        contenido.addSubview_(interruptor)

        etiqueta = AppKit.NSTextField.labelWithString_(
            "Últimos dictados — doble clic para copiar:"
        )
        etiqueta.setFrame_(AppKit.NSMakeRect(20, 368, 500, 20))
        contenido.addSubview_(etiqueta)

        tabla = AppKit.NSTableView.alloc().initWithFrame_(
            AppKit.NSMakeRect(0, 0, 500, 260)
        )
        columna_cuando = AppKit.NSTableColumn.alloc().initWithIdentifier_("cuando")
        columna_cuando.setTitle_("Cuándo")
        columna_cuando.setWidth_(90)
        columna_texto = AppKit.NSTableColumn.alloc().initWithIdentifier_("texto")
        columna_texto.setTitle_("Texto")
        columna_texto.setWidth_(390)
        tabla.addTableColumn_(columna_cuando)
        tabla.addTableColumn_(columna_texto)
        tabla.setDataSource_(controlador)
        tabla.setTarget_(controlador)
        tabla.setDoubleAction_("dobleClic:")
        tabla.setUsesAlternatingRowBackgroundColors_(True)

        panel = AppKit.NSScrollView.alloc().initWithFrame_(
            AppKit.NSMakeRect(20, 94, 500, 264)
        )
        panel.setHasVerticalScroller_(True)
        panel.setBorderType_(AppKit.NSBezelBorder)
        panel.setDocumentView_(tabla)
        contenido.addSubview_(panel)

        boton = AppKit.NSButton.buttonWithTitle_target_action_(
            "Copiar seleccionado", controlador, "copiar:"
        )
        boton.setFrame_(AppKit.NSMakeRect(20, 52, 180, 30))
        contenido.addSubview_(boton)

        estado = AppKit.NSTextField.labelWithString_("")
        estado.setFrame_(AppKit.NSMakeRect(212, 58, 310, 20))
        estado.setTextColor_(AppKit.NSColor.secondaryLabelColor())
        contenido.addSubview_(estado)

        controlador.tabla = tabla
        controlador.estado = estado
        controlador.interruptor = interruptor
        self._controlador = controlador
        self._ventana = ventana
