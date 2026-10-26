# Guía editorial · No Entiendo a los Mayores

## 1. La idea

Dos niños, Edu y Rubén ([biblia](biblia-personajes.md)), intentan comprender conceptos, costumbres y contradicciones del mundo adulto. Cada Short desarrolla **una sola idea** y combina seis cosas: curiosidad, contradicción, humor, un pequeño aprendizaje, que el adulto que lo ve se reconozca, y un remate memorable.

El cierre de marca es **"Cosas de mayores."**: hablado (por uno o por los dos, con variaciones: "Cosas de mayores, Rubén."), escrito (sello tras la última reacción) o como reacción final (miran a cámara y cae el sello). El sello aparece siempre; lo que varía es cómo se llega a él.

## 2. Estructura (orientativa, no una plantilla)

| Tiempo | Qué pasa |
|---|---|
| 0-2 s | Gancho: una pregunta o una afirmación desconcertante. Ya está escrita en pantalla desde el primer fotograma. |
| 2-8 s | Primera respuesta, aparentemente lógica. |
| 8-18 s | El otro descubre una contradicción. |
| 18-28 s | Intentan resolverla y la explicación se vuelve más absurda. |
| 28-35 s | Remate: silencio, mirada, reacción o "Cosas de mayores". |

**Estructuras** (`formato` del guion; el validador avisa si el catálogo usa menos de 6): `pregunta-respuesta`, `malentendido`, `definicion-absurda`, `comparacion`, `situacion-cotidiana`, `mini-historia`, `deduccion-logica`, `correccion`, `ambos-equivocados`, `ambos-descubren`, `nadie-sabe`, `instrucciones`.

**Duración.** 28-35 s por defecto. Si el guion lo necesita, `"duracion": "corta"` (20-25 s) o `"larga"` (40-50 s). Nunca se alarga un vídeo para llegar a una duración: no hay relleno, las pausas tienen tope y la duración sale de lo que dura la voz.

## 3. Series

| Serie (`serie`) | Qué es |
|---|---|
| `por-que` · ¿Por qué los mayores...? | Una costumbre adulta, preguntada en serio |
| `diccionario` · Diccionario de mayores | Un concepto por episodio (hipoteca, comisión, networking...) |
| `cuando-sea-mayor` · Cuando sea mayor... | Imaginan la vida adulta y chocan con la realidad |
| `quien-invento` · ¿Quién inventó esto? | El origen (inventado) de algo que nadie soporta |
| `ocho-anos` · Explícamelo como si tuviera ocho años | Un concepto económico, laboral o tecnológico explicado en el diálogo |
| `manual` · Manual para ser adulto | Instrucciones "prácticas" que retratan lo absurdo |

La serie aparece como distintivo de color sobre la pregunta del gancho (`content/series.json`). Dos episodios seguidos no deberían ser de la misma serie (el validador avisa).

## 4. Pilares temáticos

`content/pilares.json` tiene la taxonomía ampliable: dinero y finanzas, trabajo, vida adulta, relaciones y comunicación, tecnología y contradicciones cotidianas, cada uno con su reserva de temas. **Cada tema se usa una sola vez** (el validador lo bloquea). Para un tema nuevo, se añade a su pilar.

## 5. Tono y lenguaje

- Español de España natural, ágil y claro; nada demasiado local (lista de palabras a evitar en `tools/validate.mjs`). Si un concepto es solo de España (Bizum, ITV), se explica en la propia frase.
- Familiar e inocente, apto para plataformas generalistas. Sin insultos, sin alcohol ni apuestas, sin dobles sentidos.
- El dato del aprendizaje tiene que ser correcto. Va en el texto del post (📚) y, cuando cabe, en el diálogo.

## 6. Cómo se escribe un guion

Un archivo por episodio en `content/guiones/es/NNN-tema.json`. El director (`src/director.mjs`) decide los planos, las miradas por defecto, cuándo entra cada tarjeta y cómo se cierra, así que el guionista solo escribe qué pasa.

```json
{
  "id": "011-tarjeta-de-credito", "idioma": "es",
  "serie": "ocho-anos", "pilar": "dinero", "tema": "tarjeta de crédito",
  "formato": "pregunta-respuesta", "escenario": "salon",
  "roles": { "pregunta": "r", "explica": "e" },
  "titulo": "Si no tienes dinero, ¿por qué lo compras?",
  "cierre": { "tipo": "hablado" },
  "aprendizaje": "Una tarjeta de crédito te adelanta el dinero; si no lo devuelves a tiempo, pagas intereses.",
  "hashtags": ["#tarjetadecredito", "#deudas"],
  "lineas": [
    {"r": "Pero si no tienes dinero, ¿por qué lo compras?", "cara": "dudoso"},
    {"e": "Lo pagas con la tarjeta.", "tarjeta": {"icono": "tarjeta", "texto": "TARJETA"}},
    {"r": "¿Y quién paga la tarjeta?"},
    {"pausa": 1.0, "reaccion": "silencio", "caras": {"r": "asombrado"}},
    {"ambos": "Cosas de mayores."}
  ]
}
```

Campos de una línea: el personaje (`"e"`, `"r"` o `"ambos"`) con su texto; `cara` (de quien habla), `otro` (cara del que escucha), `gesto` / `gesto_otro`, `emote` / `emote_otro`, `mira` (`camara`, `arriba`), `tarjeta` (`icono` + `texto` de hasta 16 caracteres), `plano` (`dos`, `medio`, `cerca`) si se quiere forzar.
Una pausa: `{"pausa": segundos, "reaccion": "...", "caras": {...}, "emote": {"e": "?"}}`.
Escenarios: `dormitorio`, `salon`, `parque`, `cocina`, `cole`, `calle`. Iconos de tarjeta: los de `ICONS` en `src/puppets.js` (casa, tarjeta, moneda, billetes, movil, reloj, calendario, pesa, cafe, nube, candado, grafica, carrito, factura, coche, galleta, like, maleta, despertador, wifi, banco, oferta, tarta, mensaje, robot, maletin, portatil, tele, hucha, escudo, anillo, llave, bocadillo, lunes, reunion, ticket).

## 7. Control de calidad

`node tools/validate.mjs` comprueba antes de renderizar: campos obligatorios, serie / pilar / tema / estructura / escenario válidos, tema no repetido, los dos hablan, líneas cortas, palabras a evitar, caras, gestos, emotes e iconos que existen, pausas con tope, cierre de marca presente, aprendizaje presente, duración estimada en rango, variedad del catálogo (series, estructuras, intercambio de papeles, series seguidas) y el calendario. Después de un render con voz, `node tools/validate.mjs --timing out/*/timing.json` comprueba la duración real.
