---
name: nombre-de-la-skill
description: >-
  EN TERCERA PERSONA: qué hace la skill y CUÁNDO usarla (disparadores concretos),
  más una frase "NO la uses cuando…". Máximo 1024 caracteres. Este texto es lo
  único que el modelo ve para decidir si activarla: que sea específico.
metadata:
  # --- Dos ejes de clasificación (taxonomía del despacho) ---
  rol: fase                 # transversal | fase | cliente | output | input | procesado
  naturaleza: atomica       # atomica | orquestadora
  # --- Identidad ---
  jurisdiction: ES
  area: [civil]             # lista: civil, mercantil, consumo, procesal…
  version: "1.0"            # semver SIEMPRE entre comillas
  author: "Nikolai Tyukhay"
  organization: "Tyukhay Legal"
  contact: "nikolai.tyukhay@tyukhay.legal"
  status: vigente           # vigente | deprecada | experimental
  # --- Mapa de relaciones (derivable y validable; rellena solo lo que aplique) ---
  orchestrates: []          # skills que esta invoca (si naturaleza: orquestadora)
  requires: []              # skills o recursos que necesita
license: "Proprietary — Tyukhay Legal (todos los derechos reservados)"
---

# nombre-de-la-skill

> Plantilla del despacho. Copia esta carpeta, renómbrala, rellena el frontmatter
> y este cuerpo, y borra los comentarios guía. Revisa `_LEEME.md` para saber qué
> **módulos** añadir según el `rol`/`naturaleza` de la skill.

## Cuándo se activa

Disparadores concretos (frases del usuario, referencias, tipos de documento) y los
falsos amigos por los que **NO** debe activarse.

## Qué produce

Entregables y dónde se guardan (rutas con `/`). Si produce outputs en expediente,
incluye el **módulo OPERACIÓN** (ver `_LEEME.md`).

## Procedimiento

Pasos como procedimiento, no como menú de opciones. Defaults claros. Solo lo que
el modelo no sabe ya; mantén el `SKILL.md` por debajo de 500 líneas y mueve el
detalle a `references/` cargado bajo demanda (progressive disclosure).

<!-- Estilo de la casa + verificación (módulo ESTILO + VERIFICACIÓN, ver _LEEME.md):
     - Si esta skill REDACTA texto (escritos, comunicaciones): cita el contrato
       `data/_estilo/contrato_estilo.md` (capa 1) en tu fase de redacción y pasa el
       borrador por `pase-de-estilo` (capa 2).
     - Si MANEJA hechos, cifras o citas: encadena con `verificacion-anclada-fuente`
       (source-locked); no inventes ni rellenes huecos.
     - Declara los que apliquen en `metadata.requires`.
     Borra este comentario si la skill no redacta ni cita. -->


## Gotchas

Avisos no obvios y validation loops para las partes frágiles.
