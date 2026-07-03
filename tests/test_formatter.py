"""Pruebas del pipeline de formato local (el "AI formatting" sin nube)."""
import dataclasses

from flujo.config import Config
from flujo import formatter


CONFIG = Config()


def test_texto_vacio_devuelve_vacio():
    assert formatter.formatear("", CONFIG) == ""
    assert formatter.formatear("   \n  ", CONFIG) == ""


def test_colapsa_espacios_y_capitaliza():
    assert formatter.formatear("  hola   mundo  ", CONFIG) == "Hola mundo."


def test_respeta_puntuacion_existente():
    assert formatter.formatear("¿cómo estás?", CONFIG) == "¿Cómo estás?"


def test_agrega_punto_final():
    assert formatter.formatear("ya terminé la obra", CONFIG).endswith("obra.")


def test_coma_final_se_convierte_en_punto():
    assert formatter.formatear("hasta mañana,", CONFIG) == "Hasta mañana."


def test_diccionario_reemplaza_sin_mayusculas():
    texto = formatter.formatear("hay que revisar obra kit y supabase", CONFIG)
    assert "ObraKit" in texto
    assert "Supabase" in texto


def test_diccionario_no_toca_palabras_parciales():
    assert formatter.aplicar_diccionario("whatsappero", {"whatsapp": "WhatsApp"}) == (
        "whatsappero"
    )


def test_diccionario_prefiere_terminos_largos():
    diccionario = {"obra": "Obra", "obra kit": "ObraKit"}
    assert formatter.aplicar_diccionario("uso obra kit", diccionario) == "uso ObraKit"


def test_comando_punto_y_aparte():
    texto = formatter.formatear(
        "primero el presupuesto, punto y aparte, luego el contrato", CONFIG
    )
    assert texto == "Primero el presupuesto.\n\nLuego el contrato."


def test_punto_y_aparte_no_duplica_signos():
    texto = formatter.formatear("¿quedó claro? punto y aparte seguimos mañana", CONFIG)
    assert "?." not in texto
    assert texto == "¿Quedó claro?\n\nSeguimos mañana."


def test_comando_nueva_linea():
    texto = formatter.formatear("lista de pendientes, nueva línea, comprar cemento", CONFIG)
    assert "\n" in texto
    assert "nueva línea" not in texto.lower()


def test_comandos_se_pueden_apagar():
    config = dataclasses.replace(CONFIG, comandos_dictado=False)
    texto = formatter.formatear("uno punto y aparte dos", config)
    assert "punto y aparte" in texto.lower()


def test_muletillas_apagadas_por_defecto():
    texto = formatter.formatear("eh bueno el proyecto va bien", CONFIG)
    assert texto.lower().startswith("eh")


def test_muletillas_se_quitan_si_se_activa():
    config = dataclasses.replace(CONFIG, quitar_muletillas=True)
    texto = formatter.formatear("eh, el proyecto eh va bien", config)
    assert "eh" not in texto.lower()
    assert texto == "El proyecto va bien."


def test_muletilla_no_rompe_palabras_que_la_contienen():
    config = dataclasses.replace(CONFIG, quitar_muletillas=True, muletillas=("eh",))
    texto = formatter.formatear("compré un vehículo", config)
    assert "vehículo" in texto


def test_capitaliza_despues_de_parrafo_nuevo():
    texto = formatter.formatear("hola punto y aparte adiós", CONFIG)
    lineas = [linea for linea in texto.split("\n") if linea]
    assert all(linea[0].isupper() or not linea[0].isalpha() for linea in lineas)
