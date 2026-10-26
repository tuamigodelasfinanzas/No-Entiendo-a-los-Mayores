# Dirección visual

**Formato:** 1080 × 1920, 30 fps, H.264 + AAC. Todo lo importante dentro de la zona segura de Reels / Shorts / Facebook: texto entre y = 190 y y = 1560, sin pegarse a los 130 px de la derecha (botones).

## Capas de cada fotograma (de atrás adelante)

1. **Escenario** (`dormitorio`, `salon`, `parque`, `cocina`, `cole`, `calle`): vectorial, colores suaves y poco contraste para que los niños destaquen. Se mueve un poco menos que los personajes con la cámara (paralaje).
2. **E y R**: las capas cuerpo / cabeza sacadas de las hojas de personaje, con la cara del dibujo original; solo se animan el parpadeo y la boca al hablar, con trozos del propio dibujo (`src/puppets.js`, `face()`). E siempre a la izquierda, R a la derecha, de pie sobre el suelo y mirándose.
3. **Gancho**: la pregunta del episodio en una tarjeta blanca con el distintivo de la serie. Grande desde el primer fotograma; cuando termina la primera frase se encoge y queda arriba como recordatorio del tema.
4. **Tarjetas**: un icono y una palabra o cifra ("30 AÑOS", "−2 €") que entran con un pop mientras se dice esa línea, sobre las cabezas.
5. **Bocadillo**: los subtítulos son un bocadillo blanco bajo el que habla, con la cola hacia su boca (una cola a cada uno si hablan los dos) y la palabra que se está diciendo en su color (rojo E, azul R). Sin etiqueta de nombre.
6. **Sello final**: "Cosas de mayores." estampado en rojo, con el @ del canal debajo.

## Planos (los decide `src/director.mjs`)

| Plano | Cuándo |
|---|---|
| `dos` (los dos de cuerpo entero) | el gancho, las frases de los dos, las pausas y el final |
| `medio` (quien habla, centrado, x1,5) | la mayoría de las líneas |
| `cerca` (la cara, x2) | frases muy cortas justo antes de una pausa: el remate |

Corte seco entre planos y un empuje lento (2,5 %) durante cada línea, para que ningún plano esté muerto. En las pausas, plano de los dos con un empuje del 6 %.

## Sonido

Voces (edge-tts), efectos y música originales generados por `tools/make_audio.py` (el mismo generador que ZERO, con los sonidos propios del canal: `sello`, `grillos`, `ding`, y las músicas `juguete` y `pensar`). La música baja sola cuando alguien habla (`tools/mix.py`, el mismo mezclador que ZERO).
