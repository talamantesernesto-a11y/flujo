# 🎙️ Flujo — dictado por voz 100% local, en español

Mantienes una tecla, hablas en español, la sueltas… y el texto aparece formateado en la
app que tengas activa. Todo corre **enteramente en tu Mac**: ni el audio ni el texto salen
de tu máquina, no hay suscripción y no gasta tokens de ninguna API.

## Por qué existe

Las apps comerciales de dictado con IA funcionan en la nube: tu voz viaja a servidores de
terceros para transcribirse, a veces acompañada de metadatos de la app activa. Flujo ofrece
la misma experiencia con modelos abiertos corriendo en tu propio chip:

| Etapa | Dictado en la nube | Flujo (tu Mac) |
|---|---|---|
| Tecla de dictado | Tecla global (hold) | Option derecha (configurable) |
| Transcripción | ASR en servidores | Whisper large-v3-turbo vía MLX (GPU del chip M) |
| Formateo | LLMs en la nube | Reglas locales + pulido opcional con Ollama |
| Inserción | Portapapeles + Cmd+V | Igual (y restaura tu portapapeles) |
| Diccionario personal | En servidores ajenos | `~/.flujo/config.json` |
| Historial | Sincronizado a la nube | `~/.flujo/historial.jsonl` |

## Instalación

En una Mac nueva (Apple Silicon), un solo comando deja todo listo:

```bash
cd flujo
./instalar.sh    # instala uv si falta, dependencias, y prepara Flujo.app
./flujo.sh       # arranca la app de barra de menús
```

La primera vez descarga el modelo (~1.6 GB) desde Hugging Face; después todo es offline.
(Instalación manual: `uv sync` y `./flujo.sh doctor`.)

### Permisos de macOS (solo la primera vez)

En **Ajustes del Sistema → Privacidad y seguridad**, autoriza a tu terminal (o a la app
con la que corras Flujo):

1. **Micrófono** — para grabar tu voz
2. **Accesibilidad** — para la tecla global y el Cmd+V simulado
3. **Monitoreo de entrada** — para detectar cuándo mantienes la tecla

macOS te los pedirá al primer uso; si algo no funciona, corre `./flujo.sh doctor`.

## Uso

1. Arranca Flujo: aparece 🎙️ en la barra de menús.
2. **Mantén presionada la tecla Option derecha (⌥)** y habla en español.
3. Suéltala: 🔴 → ✍️ → el texto se pega donde esté tu cursor.

Comandos de dictado: di **"punto y aparte"** para párrafo nuevo, **"nueva línea"** para salto.

### Ventana de Flujo

Menú 🎙️ → **"Abrir Flujo…"** abre una ventana con:
- Interruptor de **sonidos** (se guarda en la configuración al instante).
- Los **últimos 30 dictados**: doble clic en cualquiera (o "Copiar seleccionado")
  y queda en el portapapeles, por si el pegado no cayó donde querías.

### CLI

```bash
./flujo.sh probar --segundos 5   # graba del micrófono y muestra la transcripción
./flujo.sh archivo nota.m4a      # transcribe cualquier archivo de audio
./flujo.sh doctor                # revisa chip, modelo, micrófono, Ollama
./flujo.sh config                # muestra la configuración actual
```

## Configuración (`~/.flujo/config.json`)

```jsonc
{
  "idioma": "es",
  "motor": "whisper",              // "whisper" (mejor puntuación) o "parakeet" (más veloz)
  "modelo": "mlx-community/whisper-large-v3-turbo",
  "tecla": "alt_r",                // alt_l, cmd_r, ctrl_r, f13…
  "modo": "mantener",              // "mantener" (push-to-talk) o "alternar" (toggle)
  "insercion": "pegar",            // "pegar" (Cmd+V) o "teclear" (no toca el portapapeles)
  "sonidos": true,
  "comandos_dictado": true,
  "quitar_muletillas": false,      // quita "eh", "em", "mmm" si lo activas
  "diccionario": {                 // lo que Whisper oye → cómo debe escribirse
    "obra kit": "ObraKit",
    "su pavase": "Supabase"
  },
  "vocabulario": ["Lanzza", "GuardIA"],  // términos extra que el motor debe conocer
  "pulido": {                      // LLM local opcional (requiere Ollama)
    "activado": false,
    "modelo": "qwen2.5:7b"
  }
}
```

Edítalo desde el menú de Flujo → "Editar configuración" y reinicia la app.

### ¿"Aprende" mi vocabulario?

El modelo no se reentrena con tu voz, pero tu vocabulario entra al motor por dos vías:

1. **Glosario**: los valores del `diccionario` y la lista `vocabulario` se inyectan a
   Whisper como contexto en cada dictado, para que escriba "ObraKit" o "Supabase"
   bien a la primera.
2. **Corrección**: si aun así oye mal un término (p. ej. "su pavase"), agrégalo al
   `diccionario` con la forma correcta y quedará arreglado para siempre. Revisa el
   campo `"crudo"` del historial para ver qué oyó exactamente.

### Pulido con LLM local (opcional)

Para un formateo más inteligente (quitar muletillas con contexto, corregir
autocorrecciones habladas), instala [Ollama](https://ollama.com):

```bash
brew install ollama
ollama pull qwen2.5:7b     # el mejor español en tamaño chico; gemma3:4b si tienes poca RAM
```

y pon `"pulido": {"activado": true}` en la config. Si Ollama falla o tarda, Flujo usa el
texto sin pulir: el dictado nunca se pierde.

### Motor Parakeet (opcional, casi instantáneo)

NVIDIA Parakeet TDT v3 transcribe español (WER ~5.4%) en ~0.2 s, con puntuación más simple:

```bash
uv add parakeet-mlx
# y en config.json: "motor": "parakeet"
```

## Pruebas

```bash
uv run pytest                    # 41 pruebas unitarias (< 1 s)
uv run pytest -m integracion -s  # E2E: voz sintética es_MX → Whisper → texto
```

La prueba E2E no necesita micrófono: genera la frase con `say -v Paulina`, la convierte a
WAV 16 kHz y la pasa por el pipeline completo.

## Correr sin Terminal y arrancar solo al iniciar sesión

El proyecto incluye **`Flujo.app`**, un lanzador nativo de macOS:

1. Ábrelo con doble clic en Finder (o `open Flujo.app`). Aparece 🎙️ sin ninguna Terminal.
2. La primera vez, la app tiene identidad propia ("Flujo") y necesita sus propios
   permisos, separados de los de Terminal: el de **Micrófono** te lo pide solo, y
   **Accesibilidad** se agrega a mano (Ajustes → Privacidad y seguridad →
   Accesibilidad → **+** → navega a la carpeta del proyecto → Flujo.app → enciende
   el interruptor). Sal de Flujo (menú 🎙️ → Salir) y ábrelo otra vez.
3. Para que arranque al prender la Mac: **Ajustes del Sistema → General →
   Elementos de inicio → +** → selecciona `Flujo.app`.

Solo corre una instancia a la vez: si lo abres dos veces (o también lo lanzas desde
la Terminal), la segunda se cierra sola sin duplicar nada.

## Compartir con alguien más

El proyecto sin `.venv` pesa menos de 1 MB; el modelo NO se envía (se descarga solo
en la Mac de la otra persona la primera vez).

- **Por GitHub** (recomendado): sube el repo y la otra persona hace
  `git clone … && cd flujo && ./instalar.sh`.
- **Por ZIP** (AirDrop/WhatsApp): comprime la carpeta **sin** `.venv`
  (`zip -r flujo.zip flujo -x "flujo/.venv/*"`). La otra persona descomprime y corre
  `./instalar.sh` — el script quita la cuarentena de macOS y re-firma la app.

Requisitos del receptor: Mac con chip M (Apple Silicon) y ~4 GB libres de disco.

## Arquitectura

```
tecla global (pynput) ──▶ grabadora 16 kHz (sounddevice)
                                   │ al soltar
                                   ▼
                    motor local (mlx-whisper / parakeet-mlx)
                                   │ texto crudo
                                   ▼
        formato local (diccionario, comandos, muletillas, puntuación)
                                   │
                                   ▼ (opcional)
                    pulido LLM local (Ollama, qwen2.5:7b)
                                   │
                                   ▼
   pegado en la app activa (portapapeles + Cmd+V, restaura el portapapeles)
                                   │
                                   ▼
                historial local (~/.flujo/historial.jsonl)
```

Módulos en `src/flujo/`: `config` · `hotkey` · `audio` · `engine` · `formatter` ·
`polish` · `paster` · `history` · `sounds` · `app` (barra de menús) · `__main__` (CLI).
