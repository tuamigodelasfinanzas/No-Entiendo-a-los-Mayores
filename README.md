# No Entiendo a los Mayores (@noentiendoalosmayores)

Shorts animados y totalmente automatizados en castellano: dos niños, **Edu** y **Rubén**, intentan entender el mundo de los adultos... y terminan en **"Cosas de mayores."**

Instagram Reels y YouTube Shorts: @noentiendoalosmayores · Facebook: página "No Entiendo a los Mayores" · 2 vídeos al día, 13:30 y 20:30 (hora de Madrid).

Es el cuarto canal del conjunto y reutiliza lo que ya funciona en los otros:

| Pieza | Viene de |
|---|---|
| Motor de animación por fotogramas clave, cámara, transiciones y capa de "vida" (`src/stage.js`) | ZERO (`zero-understands/src/stage.js`) |
| Render con Chromium + ffmpeg, voces con edge-tts, mezclador con ducking (`src/render.mjs`, `src/voice.mjs`, `tools/mix.py`) | ZERO |
| Efectos y música originales (`tools/make_audio.py`) | ZERO, más los sonidos propios del canal |
| GitHub Pages + webhook de Make que publica en Instagram, Facebook y YouTube; Telegram para TikTok (`publish.yml`, `src/telegram.mjs`) | Planet in Numbers |
| Semáforo de salud diario (`health.yml`) | El workflow compartido de `zero-understands` |

## Cómo funciona

1. **Guiones** en `content/guiones/es/*.json` (30 para empezar). Cada uno es una idea: serie, pilar, tema, estructura, escenario, líneas, pausas y cierre. Ver la [guía editorial](docs/guia-editorial.md) y la [biblia de personajes](docs/biblia-personajes.md).
2. **Director** (`src/director.mjs`): convierte el guion en un episodio: planos, miradas, gestos, tarjetas, pausas y sello final.
3. **Render** (`src/render.mjs`): voz de cada línea → fotogramas → efectos y música → `short.mp4` (1080×1920, 30 fps) + `cover.jpg` + `post.json` (textos de cada red).
4. **Publicación** (`.github/workflows/publish.yml`): 40 minutos antes de cada franja renderiza el siguiente guion, lo sube a GitHub Pages, espera a la hora exacta y llama a Make ([publicación](docs/publicacion.md), [calendario](docs/calendario.md)). **No publica nada** hasta que `PUBLICAR = si` y haya fecha de `inicio`.
5. **Previews** (`.github/workflows/previews.yml`): en cada pull request valida todo y renderiza tres vídeos con voz (con fotogramas de inicio, centro y final) como artefacto.

## En local

```bash
npm install
python3 tools/prepare_characters.py          # capas de los personajes desde assets/characters/source (ya están hechas)
python3 tools/make_audio.py                  # efectos y música (ya están hechos)
node tools/validate.mjs                      # comprueba los 30 guiones y el calendario
CDM_VOICE=false CDM_FPS=10 CDM_FRAMES="0.4,50%,-0.4" node src/render.mjs content/guiones/es/001-hipoteca.json out/001
```

`CDM_VOICE=false` renderiza sin voz (duraciones estimadas) cuando no hay acceso al servicio de voz; `CDM_STILLS=1` guarda un fotograma por segundo en `out/<id>/work`.

## Estructura

```
assets/characters/   hojas originales (source/) y capas animables de E y R
assets/sfx, music/   sonidos y músicas originales
content/             guiones/, series.json, pilares.json, personajes.json, calendario.json, i18n.json
docs/                biblia-personajes, guia-editorial, direccion, calendario, publicacion
src/                 director, stage, puppets, render, voice, post, plan, telegram
tools/               validate, prepare_characters.py, make_audio.py, mix.py
```
