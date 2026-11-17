# Dirección de diseño

Aplicación para conducir asambleas de propiedad horizontal (Ley 675 de 2001).
La usan la administración en el escritorio o proyectada en el salón comunal,
la recepción en la mesa de registro y los copropietarios, muchos de ellos
mayores, que votan desde el celular.

## Lectura del diseño
El trabajo central es saber, en cualquier momento, si la asamblea puede
decidir. Por eso el elemento memorable es el **medidor de quórum**: una barra
gruesa con la marca legal del 50 % y la cifra grande en números tabulares.
Todo lo demás es tranquilo y ordenado, como un libro de actas.

## Diales
| Dial | Valor | Motivo |
|---|---|---|
| ENERGY | 1 | Herramienta de trabajo durante una reunión; no debe distraer. |
| RHYTHM | 2 | Las pantallas varían según el contenido: el panel de quórum rompe la uniformidad. |
| MOTION | 2 | Transición suave entre páginas (la barra lateral queda quieta), entrada y salida de los diálogos, la barra de quórum cuando cambia el dato y el punto que late mientras se espera. Con `prefers-reduced-motion` todo queda en un fundido corto o desaparece. |

## Color
| Token | Hex | Uso |
|---|---|---|
| `--tinta` | `#1E4D3F` | Color principal: verde de libro de actas. Botones, encabezado del panel de quórum. |
| `--sello` | `#C8901A` | Único acento: relleno del medidor de quórum, pestaña activa, foco del teclado. |
| `--ladrillo` | `#9E3A2C` | Acciones destructivas, votos en contra, estados negativos. |
| `--papel` | `#F2F3EF` | Fondo. Gris verdoso frío, no crema. |
| `--grafito` | `#1C2622` | Texto. |

Neutros: `--linea #D6DAD3`, `--tenue #56615C`, `--mesa #E7EBE5`.

## Tipografía
- **Atkinson Hyperlegible** (interfaz): diseñada por el Braille Institute para
  baja visión; distingue 1/l/I y 0/O, clave al leer coeficientes y documentos.
- **Source Serif 4** (solo el acta y el texto de bienvenida): el acta es un
  documento legal, no interfaz, y se lee como tal.
- Monoespaciada solo para el hash SHA-256, donde cada carácter importa.
Fuentes autoalojadas en `presentation/static/fuentes` (licencia SIL OFL),
porque la CSP de la app solo permite recursos propios.

## Forma
- Radios: 4 px en controles y estados, 8 px en paneles. Sin píldoras.
- Sombra solo en el encabezado fijo (elevación real). Paneles sin sombra.
- Formularios sobre fondo `--mesa`; tablas sobre blanco. La diferencia indica
  "aquí se escribe" frente a "aquí se consulta".

## Panel de la asamblea
Barra de estado (programada, convocada, en curso, finalizada, acta), un recuadro de *Siguiente
paso* con la única acción que toca, indicadores y la tabla de participantes (cuenta, enlace a la
sala, ingreso y voto).

## Estructura
Barra lateral verde fija en escritorio (marca, menú, cuenta). En pantallas angostas el mismo elemento
es un cajón que se desliza con el dedo; la página actual se marca con la barra ocre del medidor.

## Tema
Solo claro: la app se proyecta en salones iluminados, sus actas se imprimen y así se pidió.

## Tipografía de títulos
Los títulos de página (`h1`), el punto en votación y los diálogos usan Source Serif 4: la app es el
libro de actas de la copropiedad. La interfaz sigue en Atkinson Hyperlegible.

## Reglas de texto
Sin rayas (em dash) en el texto de la interfaz, sin etiquetas en mayúsculas
sostenidas, botones con el nombre exacto de la acción.

## Prácticas de plataforma (modern-web-guidance)
- Validación con `:user-invalid`: el error aparece después de interactuar, con texto que dice cómo
  corregirlo, `aria-invalid` sincronizado y una sola región `aria-live` para anunciarlo.
- Formularios de acceso con `autocomplete` correcto (`username`, `current-password`, `new-password`)
  y botón para mostrar la contraseña.
- Tablas: región desplazable con teclado, encabezado fijo y tarjetas con `@container` cuando son angostas.
- `<meta name="text-scale">`, tamaños en `rem` y cortes en `em` para respetar la escala de texto del sistema.
- Acciones irreversibles (cerrar votación, finalizar asamblea, cerrar orden del día) piden confirmación
  en un `<dialog>` modal con el foco en Cancelar.
- Selects con la marca (`appearance: base-select`) solo con puntero fino; en táctiles queda el nativo.
- `accent-color`, `scrollbar-color` y `::selection` con la paleta.
- Comportamiento común en `presentation/static/app.js`; sin JavaScript todo sigue funcionando.
