---
name: exportar-correos-etiqueta
description: >-
  Exporta TODOS los mensajes de una etiqueta Gmail de un caso a su expediente como
  .eml fieles (cualquier tamaño) + adjuntos extraídos, organizados cronológicamente
  con la nomenclatura del despacho (AAAA-MM-DD_descripcion) en un lote de entrega
  nuevo 00_Input/AAAA-MM-DD_email_NN/ por corrida, con índices cross-lote en
  01_Procesado/Emails/. Corre el motor local (core.email_export / scripts.export_label_emails), que
  reutiliza el OAuth de gmail_source (tokens ~/.gmail-mcp/) — se ejecuta en el PC,
  no en Cowork. Úsala cuando el usuario diga "exporta los correos de la etiqueta X",
  "baja la etiqueta del caso W-XXXXX a su expediente", "vuelca todos los emails de
  un caso al expediente" o "quiero todos los correos de esta etiqueta como .eml". NO
  la uses para subir ficheros sueltos (eso es intake-expediente), ni para montar la
  sala de lectura (organizar-sala-lectura), ni para leer/resumir un correo concreto.
  Requiere ejecución local (token + acceso a G:); desde Cowork solo planifica.
metadata:
  rol: input
  naturaleza: atomica
  jurisdiction: ES
  area: [civil, procesal]
  version: "1.2"
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

El motor escribe en un **lote de entrega nuevo por corrida**,
`…/<EXPEDIENTE>/00_Input/<AAAA-MM-DD>_email_<NN>/` (`NN` siguiente al mayor lote
`email` ya existente ese día; resuelto desde la ref del caso — la `ref` acepta el
case_id canónico o el **W-code** `id_go`, que se resuelve al nombre de carpeta real):
- Un `.eml` fiel por mensaje, nombre `AAAA-MM-DD_descripcion.eml`, **plano** en la
  raíz del lote (el `.eml` ya contiene sus adjuntos embebidos).
- Opcional (`--extraer-adjuntos` / checkbox): los mensajes con adjuntos van en
  **subcarpeta fechada** `AAAA-MM-DD_descripcion/` con el `.eml` + los adjuntos
  extraídos (PDF/imágenes) como ficheros reales.
- `_manifiesto.yaml` del lote (`fuente: email`, `tipo_contenido` por ítem). Si la
  corrida no escribe nada nuevo, el lote se borra (no queda vacío).
- **`INDICE.md` y `CRONOLOGIA.md` CROSS-LOTE** en `01_Procesado/Emails/`: recorren
  TODOS los lotes `email` de `00_Input/` más el cajón legacy `03_Email/` (casos
  antiguos no migrados), con el prefijo de lote/cajón en cada ruta. Se regeneran
  enteros en cada corrida (artefacto derivado, no crudo).
- **Idempotente:** re-ejecutar no duplica (dedup por `Message-ID`, cross-lote).
- **Traza forense:** registra el SHA-256 de cada `.eml` en el `IntakeManifest` y
  emite el evento `upload_email` en `_intake_log.jsonl` (mapeo Message-ID→sha→ruta).

## Procedimiento

1. Reúne: **cuenta** (por defecto la del despacho que tenga la etiqueta, p. ej.
   `nikolai.tyukhay@engelvoelkers.com`), **etiqueta** (ruta completa) y **ref** del
   caso (`W-XXXXX`).
2. Ejecuta el CLI en local (Claude Code / PowerShell):
   `python -m scripts.export_label_emails --ref W-XXXXX --account <cuenta> --label "<ruta/etiqueta>"`
   El destino lo resuelve `core.email_export.email_dest_dir(case_id)`: reserva un lote
   `00_Input/<AAAA-MM-DD>_email_<NN>/` nuevo (no reutiliza lotes de corridas anteriores).
3. Verifica el recuento que reporta el CLI (mensajes en la etiqueta = `.eml` escritos +
   ya existentes) y revisa `INDICE.md`/`CRONOLOGIA.md` en `01_Procesado/Emails/` (cross-lote,
   no dentro del lote de esta corrida).
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
