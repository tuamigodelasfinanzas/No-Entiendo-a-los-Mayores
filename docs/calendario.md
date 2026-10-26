# Calendario · 2 vídeos al día

| Franja | Hora (Madrid) | Por qué |
|---|---|---|
| **A** | **13:30** | Pausa de la comida en España (13:30-15:30 es uno de los picos de consumo de vídeo corto). En México son las 6:30 y en Buenos Aires las 9:30 (invierno de España): el vídeo ya está cuando América se despierta y sigue sumando por la mañana allí. |
| **B** | **20:30** | Pico de la tarde-noche en España (20:00-23:00, después de cenar o antes). En América es mediodía o primera hora de la tarde (13:30 CDMX, 16:30 Buenos Aires). |

Las dos horas caen en huecos libres de los otros canales (Planet in Numbers publica a las 6:00, 11:00 y 18:00; ZERO sube a YouTube a las 17:00 y sale a las 20:00), así que las ejecuciones de Make no se pisan y cada canal tiene su propio momento en las notificaciones de quien siga a varios.

Instagram, Facebook y YouTube reciben el mismo vídeo a la misma hora. Revisa las estadísticas tras 2-3 semanas: si la audiencia resulta ser mayoritariamente latinoamericana, la franja A puede pasar a las 15:00 (8:00 en CDMX) cambiando solo `content/calendario.json`.

## Cómo funciona

- `content/calendario.json`: las dos franjas, la zona horaria y `inicio` (primer día de publicación; `null` = no se ha empezado).
- Los guiones salen **en orden de id** (001, 002...), saltando los ya publicados. La memoria está en la rama `gh-pages`: `state/published.json`. Así, si un día falla, el siguiente no se pierde: sale en la franja siguiente.
- 30 guiones = 15 días. El workflow avisa cuando quedan 6 o menos.
- `.github/workflows/publish.yml` arranca unos 40 minutos antes de cada franja, renderiza, sube el vídeo a GitHub Pages, **espera a la hora exacta** y llama al webhook de Make.

## Activar la publicación

Dos llaves, para que nada salga por error:

1. Variable del repositorio `PUBLICAR` = `si` (Settings → Secrets and variables → Actions → Variables).
2. `"inicio": "AAAA-MM-DD"` en `content/calendario.json`.

Sin las dos, el workflow programado no hace nada; lanzado a mano, solo hace una vista previa y la manda a Telegram.
