# Biblia de personajes · No Entiendo a los Mayores

Dos niños intentan entender el mundo de los adultos. No son más listos que los mayores ni más tontos: aplican la lógica tal cual y se encuentran las contradicciones que los adultos ya no ven.

Los diseños son los de las hojas de Chiño (`assets/characters/source/`). `tools/prepare_characters.py` los convierte en las capas que se animan (`assets/characters/e|r/`).

## 1. Los dos

| | **Edu** (E) | **Rubén** (R) |
|---|---|---|
| Papel habitual | Personaje B: cree entender el mundo adulto y lo explica con seguridad | Personaje A: lógica literal, pregunta corto, no acepta contradicciones |
| Carácter (hoja) | Curioso, divertido, impulsivo, creativo, "siempre tiene una idea" | Tranquilo, reflexivo, responsable, aventurero, "siempre cuida de E" |
| Color de marca | Rojo `#D7322E` (sudadera) | Azul `#1F6FE0` (sudadera) |
| Silueta | Pelo castaño rizado y alborotado, más ancho arriba | Pelo rubio corto y en punta, cabeza más redonda |
| Ropa | Sudadera roja con capucha, vaqueros, zapatillas blancas con rayas de colores | Sudadera azul con capucha, camiseta blanca, vaqueros oscuros, zapatillas blancas **lisas** |
| Voz | `es-ES-XimenaNeural`, +8 % velocidad, +28 Hz: rápida y brillante | `es-ES-ElviraNeural`, −3 % velocidad, +14 Hz: más pausada y grave |
| En pantalla | Siempre a la izquierda | Siempre a la derecha |
| Cara al hablar | `convencido` | `curioso` |
| Cara al escuchar | `sonrisa` | `neutral` |
| Frase tipo | "Fácil. Lo pagas con la tarjeta." | "¿Y quién paga la tarjeta?" |

Edu **no** es el listo ni Rubén el tonto (ni al revés). Edu sabe la mitad de las cosas y las cuenta enteras; Rubén no sabe nada y por eso pregunta lo que importa. A veces Edu acierta y es Rubén quien se lía.

**Intercambio de papeles.** En uno de cada cinco o seis episodios Edu pregunta y Rubén explica (en los 30 primeros: 002, 008, 013, 019, 026). El validador avisa si baja del 15 %. Cada guion declara `"roles": { "pregunta": "e"|"r" }`.

**Originalidad.** La identidad visual es propia. Las zapatillas de R llevaban en la hoja un logotipo parecido al de una marca deportiva: `prepare_characters.py` lo borra (las zapatillas quedan lisas) y no se debe volver a dibujar ningún logotipo de marca, en la ropa ni en los decorados.

**Límites (no negociables).** Son niños: nunca se sexualizan, nunca aparecen en situaciones impropias, no beben, no apuestan, no insultan. El humor es familiar e inocente y apto para cualquier plataforma. Los temas de pareja (bodas, citas...) se tratan desde fuera, como algo que los niños observan en los mayores. El validador bloquea vocabulario impropio.

## 2. Reglas de diálogo

- **Frases cortas.** Máximo 90 caracteres por línea; lo normal son 3 a 9 palabras. Rubén suele hablar menos que Edu.
- **Una línea, una voz.** Si los dos dicen algo a la vez, es una línea `"ambos"` (casi siempre el cierre).
- **Turnos.** Pregunta → respuesta segura → pregunta que desmonta → respuesta que empeora... Un personaje puede encadenar dos líneas si la segunda es el giro.
- **Rubén desmonta con una sola pregunta.** "¿Y quién paga la tarjeta?" vale más que una explicación.
- **Edu responde seguro, aunque no sepa.** "Fácil.", "Claro.", "Exacto." son sus muletillas; cuando se da cuenta de que no lo sabe, lo reconoce: "Eso no lo sabe nadie."
- **Nada de chistes contados.** El humor sale de la lógica literal, de las contradicciones, de las conclusiones absurdas y de las reacciones.
- **Español de España claro**, sin localismos que no se entiendan en otros países (nada de "guay", "mola", "coger", "chuches"... la lista está en `tools/validate.mjs`).

## 3. Reacciones silenciosas

Una pausa es un gesto, no relleno: máximo 2 s cada una y 3,5 s por episodio.

| Reacción | Qué hacen | Cuándo |
|---|---|---|
| `mirada` | los dos miran a cámara | después de la conclusión absurda: "¿lo estás viendo?" |
| `silencio` | se miran entre ellos, suenan grillos | cuando la respuesta no tiene respuesta |
| `parpadeo` | parpadeo lento, con dos "tic" | incredulidad |
| `giro` | se miran y luego miran a cámara | cuando uno cae en la cuenta |
| `arriba` | miran hacia arriba, pensando | antes de una idea |

## 4. Expresiones, gestos y emotes

**Caras** (`src/puppets.js`, `EXPR`): `neutral`, `feliz`, `sonrisa`, `convencido`, `curioso`, `sorprendido`, `asombrado`, `serio`, `dudoso`, `pensativo`, `confundido`, `resignado`, `triste`, `picaro`, `enfadado`, `ilusionado`. Cada una mueve cejas (altura e inclinación), párpados y boca; la boca se abre con la voz (lip-sync) desde la forma de cada expresión.

**Gestos** (`src/director.mjs`, `GESTURES`): `salto`, `bota`, `asiente`, `niega`, `inclina`, `endereza`, `acerca`, `aparta`, `vuelve`, `encoge`. Con las manos en los bolsillos (como en las hojas), el cuerpo actúa con la cabeza, la postura y el peso.

**Emotes** sobre la cabeza: `?`, `??`, `!`, `...`, `bombilla`, `gota`, `corazon`, `lio`, `brillo`.

**Vida.** Encima de los fotogramas clave hay una capa de animación (heredada de ZERO): respiración, cambio de peso, cabeza que nunca está quieta, anticipación y rebote en los movimientos, parpadeo cada ~4 s (cada niño a su ritmo), asentimientos al hablar.

## 5. Voces y otros idiomas

Las voces viven en `src/voice.mjs` por idioma (`VOICES.es.e`, `VOICES.es.r`). Para añadir un idioma: voces en ese bloque, nombres en `content/personajes.json` (`"nombre": { "es": "Edu", "en": "..." }`), textos de marca en `content/i18n.json`, etiquetas de serie en `content/series.json` y los guiones en `content/guiones/<idioma>/`. El motor no tiene ningún texto escrito a fuego.
