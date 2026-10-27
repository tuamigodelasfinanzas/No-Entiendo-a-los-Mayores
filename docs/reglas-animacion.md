# Reglas de animación y voz (aprobadas por Chiño)

Lo que Chiño ha pedido o corregido, para que todos los vídeos salgan igual. El código que las cumple está en
`tools/escena_rig.py` (escenas con el rig por piezas) y, para el vídeo diario, en `src/` (director, escenario y voces).

## Personajes
- **Caras**: siempre exactamente las ilustraciones de Chiño. Nada redibujado, estirado ni deformado. Solo se mueve la
  cabeza entera (giros pequeños), parpadean (`blink.png`) y, al hablar, baja la parte de debajo del labio (`jaw.png`).
- **Alturas**: R es más alto que E. E mide un 87 % de lo que mide R (foto de los dos). Se escala el niño entero, nunca
  una parte (`HEIGHT` en `tools/escena_rig.py`, `altura` en `content/personajes.json`).
- **Nombres**: los niños **nunca se llaman por su nombre**, ni en los diálogos ni en los textos del vídeo. E y R son
  solo nombres internos. `tools/validate.mjs` lo comprueba en cada guion.
- **Posición**: E normalmente a la izquierda y R a la derecha.

## Movimiento
- **Bocas**: siguen las sílabas con suavidad: se abren rápido (unos 40 ms), se cierran algo más despacio (unos 65 ms) y
  casi nunca se abren del todo. Nada de abrir y cerrar de golpe, porque parece robótico (`envelope()`; en el vídeo
  diario, `syllables()` de `src/stage.js`).
- **Brazos al subir**: primero se dobla el codo y la mano sube por delante del pecho, luego se estira el brazo. Al
  llegar arriba hay un pequeño rebote. Al bajar, la mano va detrás (`mix_arm`, `settle`).
- **Manos**: nada de señalar con el dedo. Los brazos arriba van **siempre con la mano abierta**.
- **Muñecas**: la mano sale de dentro de la manga. Entra unos píxeles en el puño de la manga (`SINK`) y se dibuja
  por delante de la abertura oscura, mientras el puño de la sudadera queda por delante de la mano (`over_opening`).
  Si queda algún hueco, se rellena por debajo con piel del color de la mano (`wrist_join`), sin pintar nunca encima
  de la mano.
- **Hombros**: curva suave, sin bulto. La parte de arriba de la manga queda corta y se estrecha hacia el hombro (`CAP_EXT`, `SHOULDER_TAPER`). Donde la manga se junta con la sudadera no puede quedar escalón: el contorno se cierra en una curva continua y se vuelve a dibujar la línea (`shoulder_fill`).
- **De pie, la cadera no sube ni baja** (doblaría las rodillas hacia fuera). La vida está en la cabeza y los parpadeos.
- Los gestos con la mano en la cara se ven mal de cerca. Rascarse la cabeza se hace con la mano detrás de la cabeza.
  "Pensar" se hace con el puño bajo la barbilla, sin tapar la cara.

## Voz
- Las voces de edge-tts tal cual: `es-ES-XimenaNeural` para E (+4 % de velocidad, +12 Hz) y `es-ES-ElviraNeural`
  para R (−2 %, +6 Hz). **Ningún procesado de tono ni de formantes después** (asetrate, Rubber Band...): suena
  metálico (`src/voice.mjs`, `tools/presentacion_voces.py`).
- El contenedor de Claude no llega al servicio de voz. Las voces de un vídeo especial las genera GitHub Actions
  (`.github/workflows/presentacion-voces.yml`) y las sube a la rama.

## Texto en pantalla
- Subtítulos grandes, uno cada vez y sin etiqueta E/R. El color del borde (rojo para E, azul para R) indica quién habla.
- Cierre del canal: "Cosas de mayores."

## Revisión
- Para revisar un cambio, basta con una escena corta (`TRAMO=3,7.2 python3 tools/presentacion.py out.mp4`) y una
  imagen de detalle. El vídeo completo se renderiza cuando Chiño da el visto bueno.
- No se publica nada hasta que Chiño diga "publica".

## Fondos
- Cada vídeo tiene su propio fondo, colorido y con vida, a juego con el tema (`tools/fondos.py`). El tema sale solo
  del guion (tema, título, hashtags e iconos de las tarjetas); un guion puede fijarlo con `"fondo": "<tema>"`
  (casa, dinero, tiempo, tecnologia, trabajo, comida, deporte, viaje, coche, amigos, fiesta). El sitio sale de
  `escenario` (salon, cocina, dormitorio, cole, calle, parque).
- Lo que se mueve (motivos flotando, destellos, agujas de reloj) va por encima de la cabeza o a los lados, nunca
  sobre las caras, y hay una luz suave detrás de los niños para que destaquen. Todo dibujado por código: gratis.
- `FONDO=liso` vuelve a la pared lisa de antes; `FONDO=<tema>` fuerza un tema.
