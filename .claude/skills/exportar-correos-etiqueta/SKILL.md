---
name: exportar-correos-etiqueta
description: >-
  Exporta TODOS los mensajes de una etiqueta Gmail de un caso a su expediente como
  .eml fieles (cualquier tamaño) + adjuntos extraídos, organizados cronológicamente
  con la nomenclatura del despacho (AAAA-MM-DD_descripcion) en 00_Input/03_Email/.
  Corre el motor local (core.email_export / scripts.export_label_emails), que
  reutiliza el OAuth de gmail_source (tokens ~/.gmail-mcp/) — se ejecuta en el PC,
  no en Cowork. Úsala cuando el usuario diga "exporta los correos de la etiqueta X",
  "baja la etiqueta del caso W-XXXXX a su expediente", "vuelca todos los emails de
  <caso> al expediente" o "quiero todos los correos de esta etiqueta como .eml". NO
  la uses para subir ficheros sueltos (eso es intake-expediente), ni para montar la
  sala de lectura (organizar-sala-lectura), ni para leer/resumir un correo concreto.
  Requiere ejecución local (token + acceso a G:); desde Cowork solo planifica.
metadata:
  rol: input
  naturaleza: atomica
  jurisdiction: ES
  area: [civil, procesal]
  version: "1.0"
  author: "Nikolai Tyukhay"
  organization: "Tyukhay Legal"
  contact: "nikolai.tyukhay@tyukhay.legal"
  status: experimental
  orchestrates: []
  requires: []
license: "Proprietary — Tyukhay Legal (todos los derechos reservados)"
---

# exportar-correos-etiqueta

Vuelca **todos** los mensajes de una etiqueta Gmail de un caso a su expediente como
`.eml` fieles, con los adjuntos extraídos, ordenados cronológicamente y nombrados con
la convención del despacho. El trabajo pesado (descarga `format=raw`, escritura en
`G:`) lo hace el **motor local** `core/email_export.py`; esta skill solo lo orquesta.

## Cuándo se activa

Disparadores: «exporta los correos de la etiqueta …», «baja la etiqueta del caso
W-XXXXX a su expediente», «vuelca todos los emails de <caso/etiqueta> al expediente»,
«quiero todos los correos de esta etiqueta como `.eml`».

Falsos amigos (NO activar):
- Subir ficheros sueltos ya descargados a `00_Input/` → `intake-expediente`.
- Clasificar/montar la sala de lectura → `organizar-sala-lectura`.
- Leer, resumir o citar un correo concreto → lectura directa por el conector Gmail.

## Qué produce

En `…/<EXPEDIENTE>/00_Input/03_Email/` (resuelto desde la ref del caso):
- Un `.eml` fiel por mensaje, nombre `AAAA-MM-DD_descripcion.eml`.
- Los mensajes con adjuntos van en **subcarpeta fechada** `AAAA-MM-DD_descripcion/`
  con el `.eml` y los adjuntos extraídos (PDF/imágenes) como ficheros reales.
- `INDICE.md` y `CRONOLOGIA.md` del conjunto.
- **Idempotente:** re-ejecutar no duplica (dedup por `Message-ID`).

## Procedimiento

1. Reúne: **cuenta** (por defecto la del despacho que tenga la etiqueta, p. ej.
   `nikolai.tyukhay@engelvoelkers.com`), **etiqueta** (ruta completa) y **ref** del
   caso (`W-XXXXX`).
2. Ejecuta el CLI en local (Claude Code / PowerShell):
   `python -m scripts.export_label_emails --ref W-XXXXX --account <cuenta> --label "<ruta/etiqueta>"`
   El destino se resuelve con `core.casos.case_locator.path_for(ref)` → `00_Input/03_Email/`.
3. Verifica el recuento que reporta el CLI (mensajes en la etiqueta = `.eml` escritos +
   ya existentes) y revisa `INDICE.md`.
4. Para **Paola y Ana**: el mismo motor está expuesto como **botón en Streamlit**
   («Exportar correos por etiqueta»); eligen caso + etiqueta y pulsan. No usan CLI.

## Gotchas

- **Ejecución local obligatoria.** Necesita el token OAuth en `~/.gmail-mcp/tokens/
  <cuenta>.json` y acceso de escritura a `G:`. Desde Cowork (sandbox) NO corre: ahí
  solo se planifica o se delega.
- **Cuenta correcta.** Las etiquetas del despacho viven en la cuenta `@engelvoelkers`
  para los casos E&V; confirma la cuenta antes de listar (un `labels().list` en la
  cuenta equivocada da vacío).
- **Etiqueta anidada con espacios/acentos.** Resuelve el `labelId` con `labels().list`
  y filtra por `labelIds=[…]`; NO confíes en `q="label:…"` con la ruta literal (el
  parser de Gmail la transforma y suele devolver vacío).
- **Solo lectura.** No marca mensajes como leídos ni modifica Gmail.
- **Idempotencia.** El motor salta los `Message-ID` ya presentes; seguro re-ejecutar
  tras una interrupción.
