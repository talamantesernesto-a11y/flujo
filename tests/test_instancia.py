"""Pruebas del candado de instancia única."""
import os
import subprocess

from flujo import instancia


def test_adquirir_reclama_y_escribe_nuestro_pid():
    assert instancia.adquirir() is None
    assert instancia._ruta_pid().read_text("utf-8") == str(os.getpid())


def test_proceso_vivo_bloquea_la_segunda_instancia():
    ruta = instancia._ruta_pid()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text("1", "utf-8")  # PID 1 (launchd) siempre existe y no es nuestro
    assert instancia.adquirir() == 1


def test_pid_muerto_se_reclama():
    proceso = subprocess.Popen(["true"])
    proceso.wait()
    ruta = instancia._ruta_pid()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text(str(proceso.pid), "utf-8")
    assert instancia.adquirir() is None
    assert ruta.read_text("utf-8") == str(os.getpid())


def test_archivo_corrupto_se_reclama():
    ruta = instancia._ruta_pid()
    ruta.parent.mkdir(parents=True, exist_ok=True)
    ruta.write_text("esto no es un pid", "utf-8")
    assert instancia.adquirir() is None


def test_liberar_solo_borra_lo_propio():
    instancia.adquirir()
    instancia.liberar()
    assert not instancia._ruta_pid().exists()

    ruta = instancia._ruta_pid()
    ruta.write_text("1", "utf-8")  # PID ajeno: no se toca
    instancia.liberar()
    assert ruta.exists()
