# Publicación · Instagram, Facebook y YouTube

El mismo camino que Planet in Numbers: GitHub Actions renderiza y deja el vídeo en GitHub Pages; Make lo publica.

```
publish.yml (40 min antes) ──render──> gh-pages/media/<fecha>-<franja>-<id>/short.mp4 + cover.jpg + post.json
      │  espera a la hora
      ├── POST {status:"reel", ...}    ──> Make ──> Instagram Reel @noentiendoalosmayores
      │                                        └──> Facebook Reel · página "No Entiendo a los Mayores"
      └── POST {status:"youtube", ...} ──> Make ──> YouTube Short @noentiendoalosmayores
```

## Lo que hay que preparar una vez

**Secretos del repositorio** (Settings → Secrets and variables → Actions):

| Secreto | Para qué |
|---|---|
| `MAKE_WEBHOOK_URL` | Webhook del escenario de Make de este canal |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Previews y aviso diario de salud (pueden ser los mismos que en los otros canales). Para comprobarlos: Actions → *Telegram test* → Run workflow; si solo está el token, lista los chats que le han escrito al bot |
| `IG_ACCESS_TOKEN`, `IG_USER_ID` | Solo para el chequeo diario del token de Instagram |

**Variable** `PUBLICAR` = `si` cuando se quiera empezar (ver [calendario](calendario.md)).

**Escenario de Make** "No Entiendo a los Mayores · Publicar" (se puede duplicar el de Planet in Numbers y cambiar las cuentas):

1. Webhook personalizado → su URL va en `MAKE_WEBHOOK_URL`.
2. Router por `status`:
   - `reel`: Instagram for Business → *Create a Reel* con `video_url`, `caption` y la portada (`cover_ms` o `cover_url`); Facebook Pages → *Upload a Reel* en la página "No Entiendo a los Mayores" con el mismo `video_url` y `caption`.
   - `youtube`: YouTube → *Upload a Video* en el canal @noentiendoalosmayores, descargando `video_url` (HTTP → Get a file) con `title`, `caption` como descripción, `tags`, categoría Comedia (23). La casilla "made for kids" la decides tú: el público son adultos (los temas son hipotecas, impuestos, trabajo), aunque los protagonistas sean niños animados; YouTube y la ley (COPPA) miran a quién va dirigido.
   - `error`: aviso (Telegram o correo) con `run_url`.

Campos del payload: `status`, `channel` (`noentiendoalosmayores`), `video_url`, `cover_url`, `cover_ms`, `caption`, `title`, y en YouTube además `tags`.

## TikTok

Igual que en Planet in Numbers: cada vídeo llega a Telegram con su texto, listo para subirlo a mano.

## Comprobaciones

- `health.yml` (cada mañana a las 07:45 de Madrid, en el bot @noentiendoalosmayores_bot): la lógica compartida de `zero-understands/.github/workflows/health.yml`. Antes de activar la publicación solo mira las ejecuciones fallidas; con `PUBLICAR = si` también el token de Instagram y GitHub Pages.
- Si algo falla en una publicación real, Make recibe `status: "error"` con el enlace a la ejecución.
