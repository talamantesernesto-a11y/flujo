"""Punto de entrada: `python -m flujo [comando]`.

Comandos:
  correr    (predeterminado) arranca la app de barra de menús
  archivo   transcribe un archivo de audio y lo imprime
  probar    graba unos segundos del micrófono y muestra la transcripción
  doctor    diagnostica el entorno (chip, modelo, micrófono, Ollama)
  config    muestra la ruta y el contenido de la configuración
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from dataclasses import asdict
from pathlib import Path

from . import __version__
from .config import Config, ErrorConfig, cargar, ruta_base, ruta_config

log = logging.getLogger(__name__)


def _configurar_registro() -> None:
    ruta_base().mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(ruta_base() / "flujo.log", encoding="utf-8"),
            logging.StreamHandler(),
        ],
    )


def _cargar_config_o_salir() -> Config:
    try:
        return cargar()
    except ErrorConfig as exc:
        print(f"⚠️  {exc}", file=sys.stderr)
        print(f"Corrige {ruta_config()} o bórralo para regenerarlo.", file=sys.stderr)
        raise SystemExit(2)


def comando_correr(_args) -> None:
    import atexit

    from .instancia import adquirir, liberar

    config = _cargar_config_o_salir()
    otro = adquirir()
    if otro is not None:
        print(f"Flujo ya está corriendo (PID {otro}); no arranco otra instancia.")
        log.info("Instancia duplicada evitada; la activa es el PID %s", otro)
        return
    atexit.register(liberar)
    from .hotkey import proceso_confiable

    if not proceso_confiable():
        print("⚠️  Falta el permiso de Accesibilidad: la tecla de dictado no funcionará.")
        print("   Actívalo para tu terminal en Ajustes del Sistema → Privacidad y")
        print("   seguridad → Accesibilidad, y vuelve a arrancar Flujo.")
    from .app import AppFlujo

    print("Flujo corriendo en la barra de menús. 🎙️  = listo para dictar.")
    print(f"Mantén '{config.tecla}' para hablar; suéltala para pegar el texto.")
    try:
        AppFlujo(config).run()
    except Exception as exc:
        log.exception("Flujo terminó con un error inesperado")
        print(f"⚠️  Flujo terminó con un error: {exc}", file=sys.stderr)
        raise SystemExit(1)


def comando_archivo(args) -> None:
    config = _cargar_config_o_salir()
    from .engine import crear_motor
    from .formatter import formatear

    ruta = Path(args.ruta)
    if not ruta.exists():
        print(f"No existe el archivo: {ruta}", file=sys.stderr)
        raise SystemExit(2)
    motor = crear_motor(config)
    inicio = time.monotonic()
    crudo = motor.transcribir(str(ruta))
    segundos = time.monotonic() - inicio
    print(f"— Crudo ({motor.nombre}, {segundos:.1f}s):\n{crudo}\n")
    print(f"— Formateado:\n{formatear(crudo, config)}")


def comando_probar(args) -> None:
    config = _cargar_config_o_salir()
    from .audio import Grabadora
    from .engine import crear_motor
    from .formatter import formatear

    motor = crear_motor(config)
    print(f"Cargando modelo ({motor.nombre})…")
    motor.cargar()
    grabadora = Grabadora()
    print(f"🔴 Grabando {args.segundos}s… habla en español ahora.")
    grabadora.iniciar()
    time.sleep(args.segundos)
    audio = grabadora.detener()
    print("✍️  Transcribiendo…")
    inicio = time.monotonic()
    crudo = motor.transcribir(audio)
    segundos = time.monotonic() - inicio
    print(f"— Crudo ({segundos:.1f}s):\n{crudo}\n")
    print(f"— Formateado:\n{formatear(crudo, config)}")


def comando_doctor(_args) -> None:
    import platform

    config = _cargar_config_o_salir()
    marcas: list[tuple[bool, str]] = []

    marcas.append(
        (platform.machine() == "arm64", f"Chip Apple Silicon ({platform.machine()})")
    )
    try:
        import mlx_whisper  # noqa: F401

        marcas.append((True, "mlx-whisper instalado"))
    except ImportError:
        marcas.append((False, "mlx-whisper NO instalado (corre `uv sync`)"))
    try:
        import sounddevice as sd

        entrada = sd.query_devices(kind="input")
        marcas.append((True, f"Micrófono por defecto: {entrada['name']}"))
    except Exception as exc:
        marcas.append((False, f"Sin acceso al micrófono: {exc}"))

    cache = Path.home() / ".cache" / "huggingface" / "hub"
    nombre_modelo = config.modelo.replace("/", "--")
    descargado = cache.exists() and any(
        nombre_modelo in ruta.name for ruta in cache.iterdir()
    )
    marcas.append(
        (
            descargado,
            f"Modelo {config.modelo} {'descargado' if descargado else 'aún no descargado (se baja en el primer uso)'}",
        )
    )

    from .polish import ollama_disponible

    hay_ollama = ollama_disponible(config.pulido.url)
    detalle = "disponible" if hay_ollama else "no instalado (el pulido LLM es opcional)"
    marcas.append((hay_ollama or not config.pulido.activado, f"Ollama: {detalle}"))

    from .hotkey import proceso_confiable

    marcas.append(
        (
            proceso_confiable(),
            "Permiso de Accesibilidad para este proceso (tecla global y pegado)",
        )
    )

    for bien, mensaje in marcas:
        print(("✅" if bien else "❌"), mensaje)

    print("\nPermisos de macOS (revísalos en Ajustes → Privacidad y seguridad):")
    print("  • Micrófono: la terminal (o app) que corre Flujo")
    print("  • Accesibilidad: necesaria para la tecla global y el pegado")
    print("  • Monitoreo de entrada: necesaria para detectar la tecla")


def comando_config(_args) -> None:
    config = _cargar_config_o_salir()
    print(f"Archivo: {ruta_config()}\n")
    print(json.dumps(asdict(config), indent=2, ensure_ascii=False))


def principal(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="flujo",
        description="Dictado por voz 100% local para macOS, en español.",
    )
    parser.add_argument("--version", action="version", version=f"flujo {__version__}")
    sub = parser.add_subparsers(dest="comando")
    sub.add_parser("correr", help="arranca la app de barra de menús (predeterminado)")
    parser_archivo = sub.add_parser("archivo", help="transcribe un archivo de audio")
    parser_archivo.add_argument("ruta", help="ruta al archivo (wav, mp3, m4a…)")
    parser_probar = sub.add_parser("probar", help="graba del micrófono y transcribe")
    parser_probar.add_argument(
        "--segundos", type=int, default=5, help="duración de la grabación (5 por defecto)"
    )
    sub.add_parser("doctor", help="diagnostica el entorno")
    sub.add_parser("config", help="muestra la configuración actual")

    args = parser.parse_args(argv)
    _configurar_registro()
    comandos = {
        None: comando_correr,
        "correr": comando_correr,
        "archivo": comando_archivo,
        "probar": comando_probar,
        "doctor": comando_doctor,
        "config": comando_config,
    }
    comandos[args.comando](args)


if __name__ == "__main__":
    principal()
