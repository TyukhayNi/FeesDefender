---
name: triaje-viabilidad
description: >-
  Check BÁSICO de viabilidad de una reclamación de honorarios de mediación
  inmobiliaria (cliente Engel & Völkers), antes del análisis formal. Lee
  directamente `00_Input/` del expediente (todas las fuentes) y devuelve un
  semáforo verde/amarillo/rojo con los factores nucleares (hoja de encargo
  firmada, nexo causal con la operación cerrada, obligado al pago, prueba de la
  intermediación, importe y base de cálculo, prescripción), anclando cada
  conclusión a documento y marcando lo que falta. No requiere haber corrido
  `organizar-sala-lectura` antes. Úsala cuando el usuario diga "haz un triaje de
  viabilidad", "¿este caso se aguanta?", "check rápido de viabilidad", "¿cogemos
  este caso?". NO sustituye el informe formal de viabilidad (viabilidad-prerelleno)
  NI organiza ficheros (organizar-sala-lectura).
metadata:
  rol: fase
  naturaleza: atomica
  jurisdiction: ES
  area: [civil, mercantil, consumo]
  version: "1.1"
  author: "Nikolai Tyukhay"
  organization: "Tyukhay Legal"
  contact: "nikolai.tyukhay@tyukhay.legal"
  status: experimental
  requires: [verificacion-anclada-fuente]
license: "Proprietary — Tyukhay Legal (todos los derechos reservados)"
---

# triaje-viabilidad

Check **básico** de viabilidad de una reclamación de honorarios de mediación
inmobiliaria (E&V), antes del análisis formal. Lee **`00_Input/` directo** del
expediente y devuelve un semáforo 🟢/🟡/🔴 con los factores nucleares, cada uno
anclado a documento o marcado como faltante. Orienta la decisión de coger el caso;
**no la toma ni sustituye el informe formal**.

## Cuándo se activa

- Disparadores: «triaje de viabilidad», «¿se aguanta este caso?», «check rápido de
  viabilidad», «¿cogemos el caso?».

**NO se activa cuando:**

- Hay que producir el **informe formal** de viabilidad → `viabilidad-prerelleno`.
- Hay que **organizar los ficheros** de la carpeta → `organizar-sala-lectura`.

## Entrada

Lee `00_Input/` del expediente (todas las fuentes), igual que `viabilidad-prerelleno`.
La fuente de verdad es el crudo: el triaje localiza sus factores leyendo el contenido,
sin depender de la clasificación de la sala de lectura. **Opcional:** si existe
`01_Procesado/Sala lectura/INDICE.md`, úsalo solo como **pista de navegación** (atajo para
encontrar candidatos), pero verifica siempre contra `00_Input`. NO requiere haber corrido
`organizar-sala-lectura` antes.

## Reglas de oro (innegociables)

1. **No inventar.** Cada conclusión se ancla a `[doc: <fichero>]` + cita. Lo no
   acreditado se marca como **falta**, no se infiere. Hereda la disciplina de
   `verificacion-anclada-fuente`.
2. **Terminología:** propietario / buscador (nunca vendedor/comprador), aun cuando
   el documento diga otra cosa.
3. **Es un triaje, no el informe.** No puntúa hitos, no rellena el `.xlsx`, no decide
   por el letrado: orienta.

## Factores

Ver `references/criterios_triaje.md` (cárgalo al empezar): los 8 factores, cuáles son
**nucleares** vs **accesorios**, y las reglas del semáforo.

## Procedimiento

1. **Detecta el tipo de caso** (BAD_DEBT, NEGATIVA_*, VUELTA, etc. — lista en
   `references/criterios_triaje.md`); orienta qué factores pesan.
2. **Evalúa cada factor:** busca en la sala el documento que lo acredita y márcalo
   **acreditado** (con cita), **débil** (existe pero con problema: firma sin cotejar,
   copia, ilegible) o **falta**.
3. **Calcula el semáforo** según las reglas de `references/criterios_triaje.md`.
4. **Redacta** el veredicto corto + **qué documentación pedir** para cerrar huecos.

## Qué produce

`_TRIAJE_VIABILIDAD.docx` (vía skill `docx`), guardado en la carpeta del caso del
**Drive del despacho** (es work product interno; OK ahí porque E&V no accede al Drive
del despacho). Contenido: semáforo · tabla factor·estado·cita/falta · veredicto ·
documentación a recabar.

## Gotchas

- **Semáforo conservador:** si falta un factor **nuclear**, es 🔴 aunque el resto
  esté acreditado.
- **Sala casi vacía:** no rellenes el veredicto a la fuerza; di que falta
  documentación para poder triar.
- **No es el informe formal:** para el `.xlsx` de viabilidad, los 14 hitos y el
  recuadro CFO, encadena con `viabilidad-prerelleno`.
