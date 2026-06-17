---
name: pase-de-estilo
description: >-
  Revisa y reescribe un borrador (escrito procesal, contrato, email, memo, carta
  a cliente o a Engel & Völkers) para que sea claro, persuasivo y no parezca
  generado por IA, con la voz del despacho. Detecta y corrige frases-río, pasiva e
  impersonal que ocultan al agente, nominalizaciones, muletillas y perífrasis,
  adjetivación y adverbios vacíos, presente continuo evitable, redundancias y
  marcas delatoras de IA (em dash, tríadas, meta-comentario, vocabulario-marca);
  propone (no impone) reordenación argumentativa. Úsala cuando el usuario pegue un
  borrador y pida revisarlo, "humanizarlo", aclararlo, hacerlo más persuasivo,
  pulir el estilo o quitarle el tono de IA, y como paso final antes de
  guardar/firmar un escrito o comunicación. NO toca fondo, datos, cifras ni citas
  (eso es verificacion-anclada-fuente) ni el formato Sala 1ª TS; NO la uses para
  generar un escrito desde cero (eso es escritos-judiciales citando el contrato de
  estilo).
metadata:
  rol: transversal
  naturaleza: atomica
  jurisdiction: ES
  area: [civil]
  version: "1.0"
  author: "Nikolai Tyukhay"
  organization: "Tyukhay Legal"
  contact: "nikolai.tyukhay@tyukhay.legal"
  status: vigente
  requires: [verificacion-anclada-fuente]
license: "Proprietary — Tyukhay Legal (todos los derechos reservados)"
---

# pase-de-estilo

Linter de estilo del despacho: la **capa 2** del estilo de la casa. Revisa un
borrador ya escrito y lo devuelve claro, persuasivo y sin marcas de IA, con la voz
del despacho, **sin tocar el fondo**. La capa 1 es el contrato canónico
[`data/_estilo/contrato_estilo.md`](../../../data/_estilo/contrato_estilo.md), que
las skills productoras citan al redactar para que el borrador nazca en estilo; esta
skill caza lo que sobrevive y **certifica** que se respetó.

## Cuándo se activa

- El usuario pega un borrador (propio, de un tercero o de otra herramienta) y pide
  **revisarlo, reescribirlo, «humanizarlo», aclararlo, pulir el estilo, hacerlo más
  persuasivo o quitarle el tono de IA**.
- Como **paso final** del flujo de generación de un escrito o comunicación, antes
  de guardar en el expediente o de la firma.
- Triggers: «pásale el estilo», «revisa el estilo», «esto suena a IA», «humaniza
  esto», «hazlo más claro / más persuasivo», «pule este borrador».

**NO se activa cuando:**

- Hay que **generar un escrito desde cero** → `escritos-judiciales` (que cita el
  contrato de estilo al redactar). Esta skill solo revisa lo ya escrito.
- Lo que falla es el **fondo**: hechos, cifras, fechas, citas, encaje jurídico →
  `verificacion-anclada-fuente`. El estilo no es el problema.
- Se pide montar el expediente o decidir estrategia → `preparacion-litigio-civil`.

## Qué produce

Tres entregables, en este orden, en el chat (no escribe en el expediente):

1. **Versión final** reescrita, lista para pegar.
2. **Tabla de cambios:** una fila por corrección.

   | Fragmento original | Capa | Motivo | Corrección |
   |---|---|---|---|
   | «…texto…» | claridad / persuasión / no-IA | tic o vicio concreto | «…texto…» |

3. **Traza** (3-5 líneas): qué se corrigió por capa, qué se dejó intacto y por qué,
   y las banderas levantadas (citas vagas remitidas, reordenación propuesta). Diseñada
   para auditoría futura tipo «El Auditor».

Si el usuario solo quiere la versión final, dale las tres de todos modos: la tabla y
la traza son el control de calidad, no un extra.

## Procedimiento

1. **Identifica el registro** (tabla §5 del contrato): procesal · requerimiento ·
   alegato · carta a cliente (ruso por defecto) · comunicación E&V · memo. Calibra
   la intensidad de poda según el registro; no podes una carta como un escrito.
2. **Carga el contrato** `data/_estilo/contrato_estilo.md` (resumen operativo) y, para
   el detalle, los inventarios de `references/` bajo demanda (ver tabla abajo).
3. **Pasada por capas, en este orden:**
   - **Fondo primero (no es tuyo):** localiza datos, cifras, fechas, nombres,
     citas y terminología técnica. **Márcalos como zona intocable** antes de tocar
     nada. Si una cita es vaga o no está anclada, **no la corrijas ni la inventes**:
     levanta bandera y remite a `verificacion-anclada-fuente`.
   - **Claridad** (`references/claridad_es.md`): economía, frase ≤20 con variación,
     activa/afirmativa, párrafo=una idea, concreción, sin pose.
   - **Persuasión** (`references/persuasion_es.md`): marco no resumen, orden por
     fuerza, ejemplo concreto, paralelismo, citar con bisturí, cierre con
     idea-fuerza. La reestructuración **se propone, no se impone** (ver Guardarraíles).
   - **No-IA** (`references/tics_ia_es.md`): busca **racimos** de tics, no tics
     aislados. Quédate dentro del argumento (§7), recupera «ser», rompe tríadas,
     fuera el relleno y el em dash. **Escaneo final: cero rayas (—).**
4. **Auditoría de repetición:** un buen arreglo repetido tres párrafos después se
   vuelve tic; varía las sustituciones.
5. **Entrega** versión final + tabla + traza.

| Necesitas… | Lee |
|---|---|
| Reglas de claridad + calibración por registro | `references/claridad_es.md` |
| Inventario exhaustivo de tics de IA (81 patrones, §7 legal-analítico) | `references/tics_ia_es.md` |
| Arquitectura y craft persuasivos (apertura, secuencia, ejemplos, voz) | `references/persuasion_es.md` |
| Voz real del despacho (antes/después por registro) | `references/registros.md` |

## Guardarraíles — la línea que NUNCA se cruza

El estilo opera **dentro** del fondo y del formato, no los sustituye. **Nunca**
toques, alteres ni «mejores»:

- La **tesis jurídica** ni el **orden lógico** de los argumentos (salvo proponerlo
  aparte, ver abajo).
- **Datos, cifras, fechas, nombres, importes, plazos.**
- **Citas literales y referencias normativas/jurisprudenciales** ya verificadas.
- **Terminología técnica precisa** (regla de oro: claridad ⟂ precisión; gana la
  precisión). No cambies «dolo», «saneamiento», «litisconsorcio» por sinónimos.
- La **estructura procesal** y el **formato Sala 1ª TS** (TNR 12, citas 10 pt,
  párrafos numerados, jerarquía, márgenes, ≤25 págs.).

**Reordenación: distingue la frase del esqueleto.**

- *Permitido (es claridad/persuasión), y se declara en la traza:* reordenar
  frases o incisos **dentro** de un mismo párrafo o fundamento (abrir con la
  tesis, subir el dato al frente, cerrar con la consecuencia).
- *Solo se PROPONE, nunca se aplica en silencio:* cambiar el orden de los
  **fundamentos, argumentos, hechos o el petitum**, o mover contenido entre
  secciones. Añade una nota aparte («Sugerencia de reordenación: …») y deja la
  decisión al letrado. No reescribas el esqueleto del argumento por tu cuenta.

**Cita vaga o sin anclar:** márcala en la traza y remite a
`verificacion-anclada-fuente`. **No la inventes ni la concretes tú.**

**No sobre-corrijas (guardarraíles de detección):**

- Busca **racimos** de tics, no aislados. Un em dash suelto, un conector común o un
  cultismo *técnico* no delatan nada.
- **Preserva las señales humanas:** detalle específico y raro, tensión sin
  resolver, inciso genuino, variación de longitud de frase. Sobre-editar las mata.
- **Reescribe, no amputes.** Cubre todo lo que cubría el original: si tenía cinco
  párrafos, la versión final tiene cinco. Limpiar IA no es vaciar argumento.

## Calibración por registro

La intensidad de la poda y lo que se conserva cambian por registro (tabla §5 del
contrato y §10/§8 de los inventarios). En **carta a cliente ruso/ex-URSS**: redacta
en **ruso por defecto** salvo indicación contraria, y permite primera persona y
calidez. En **E&V**: registro corporativo premium, sobrio, con nombre de marca, sin
grandilocuencia. En **escrito procesal**: interpelación dosificada, sin voz
literaria, formato Sala 1ª intacto.

## Voz del despacho

`references/registros.md` recoge muestras reales anotadas (antes/después) por
registro. Cuando existan, **replica** ese patrón al reescribir. **A falta de
muestra, no inventes la voz**: usa el comportamiento por defecto del registro.

## Gotchas

- El **fondo se marca antes de tocar nada.** El error caro es «mejorar» una cifra,
  una fecha o una cita al fluidificar la frase. Si dudas si algo es dato o estilo,
  trátalo como dato.
- **Em dash:** el escaneo final de cero rayas (—/–) es obligatorio; es el delator
  de IA más fiable y se cuela al reescribir.
- **No conviertas la tabla de cambios en ruido:** agrupa correcciones idénticas
  («5× supresión de "conviene señalar"») en vez de una fila por cada una.
- Esta skill **no escribe en el expediente** ni genera `.docx`: entrega texto en el
  chat. El guardado lo hace la skill productora o el letrado.
