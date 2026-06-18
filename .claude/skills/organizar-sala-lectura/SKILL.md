---
name: organizar-sala-lectura
description: >-
  Organiza el intake de Drive de un expediente FeesDefender en una "sala de
  lectura" legible: lee 00_Input/01_Drive EV, clasifica cada fichero en las
  carpetas canónicas de Engel & Völkers (activación, ofertas, arras, facturación,
  PBC, reclamaciones, fotos, pendiente de clasificar), presenta una propuesta para
  tu visto bueno y, tras aprobarla, los copia con nombre canónico
  fecha_descripcion a 01_Procesado/Sala lectura Drive EV, sin tocar el crudo,
  más INDICE.md, CRONOLOGIA.md y _MANIFIESTO.md. Úsala cuando el usuario diga
  "organiza esta carpeta", "ordena el intake", "monta la sala de lectura",
  "prepara los ficheros para leer" de un caso. NO valora viabilidad (eso es
  triaje-viabilidad) NI genera el informe formal (eso es viabilidad-prerelleno) NI
  mueve/borra el crudo.
metadata:
  rol: output
  naturaleza: atomica
  jurisdiction: ES
  area: [civil, procesal]
  version: "1.2"
  author: "Nikolai Tyukhay"
  organization: "Tyukhay Legal"
  contact: "nikolai.tyukhay@tyukhay.legal"
  status: experimental
  requires: []
license: "Proprietary — Tyukhay Legal (todos los derechos reservados)"
---

# organizar-sala-lectura

Convierte el intake de Drive de un expediente FeesDefender (desordenado) en una
**sala de lectura** legible: documentos clasificados por las carpetas canónicas de
E&V, con nombre canónico, más índices de navegación. Versión **prompt-driven** del
primer paso de la sala de lectura del motor local (misma taxonomía, mismos nombres),
para correr en claude.ai/Cowork sin instalar nada. **No destructivo: copia, nunca
mueve ni borra el crudo.** Presenta **una propuesta para tu visto bueno** antes de
copiar nada.

## Cuándo se activa

- Disparadores: «organiza esta carpeta», «ordena el intake», «monta la sala de
  lectura», «prepara los ficheros para leer», «esta carpeta de Drive está hecha un lío».

**NO se activa cuando:**

- Hay que **valorar la viabilidad** del caso → `triaje-viabilidad`.
- Hay que producir el **informe formal de viabilidad** → `viabilidad-prerelleno`.

## Entrada y montaje

- Trabaja sobre el **expediente en el Drive del despacho** (no el de Engel).
- **Lee** de `00_Input/01_Drive EV/`. Las demás fuentes (`04_Manual`, `05_CRM`, etc.)
  quedan **fuera de alcance**.
- **Escribe** en `01_Procesado/Sala lectura Drive EV/`. Cowork debe tener montada la
  **raíz del expediente** (la salida vive fuera de `00_Input`).

## Por qué fuera de 00_Input

`00_Input/` es zona de intake: el pipeline local la escanea entera y los re-pulls del
Drive de Engel la sobrescriben. Si la sala viviera ahí, las copias se re-ingerirían
como intake nuevo (duplicados, re-OCR) y un re-pull las pisaría. Por eso la salida va
a `01_Procesado/`, igual que el motor local.

## Qué produce

```
<Expediente (Drive del despacho)>/
├── 00_Input/01_Drive EV/         ← crudo, nombres originales, NO se toca
└── 01_Procesado/
    └── Sala lectura Drive EV/
        ├── INDICE.md · CRONOLOGIA.md · _MANIFIESTO.md
        └── <carpetas canónicas E&V>/   (ver references/taxonomia_ev.md)
```

## Autonomía y gate único

La skill **no inserta preguntas de aclaración** ni pide permiso fichero a fichero.
Tiene **un solo gate humano**: la propuesta del Paso 2.5. Tras tu OK, ejecuta todo de
una pasada **sin más preguntas**. Por defecto asume autorización para crear y copiar
en `01_Procesado/Sala lectura Drive EV/` (el crudo de `00_Input` no se toca ni se
borra; siempre **copia** server-side). El diálogo de permiso por-llamada del conector
es ajuste del **cliente Cowork** ("Permitir siempre" en el conector de Drive), no de
la skill.

## Procedimiento

1. **Lista** `00_Input/01_Drive EV/` con el conector de Drive.
2. **Clasifica cada fichero** leyendo su contenido: **tipo** (una de las 8 categorías
   de `references/taxonomia_ev.md`; la **identidad/PBC se enruta POR PARTE** —vendedor
   → `01. ACTIVACIÓN`, con los Anexos 1 y 2 del vendedor a `06. PBC`; comprador →
   `03. OFERTAS`, con subcarpeta por oferta si hay varias—; lo ambiguo o ilegible →
   `08. PENDIENTE DE CLASIFICAR`, **nunca se fuerza**), **fecha** (del contenido;
   subsidiariamente del nombre; si no consta, `0000-00-00`) y **sha256** (calculado de
   los bytes). No copies nada todavía.
3. **(Paso 2.5 — GATE) Presenta la propuesta y ESPERA.** Renderiza la propuesta
   visual (ver abajo) y **espera confirmación**. Si piden ajustes, reclasifica y vuelve
   a presentar. **Solo con OK explícito** pasas al paso 4.
4. **(tras OK) Ejecuta de una pasada:** crea las carpetas canónicas y **copia** cada
   fichero a `01_Procesado/Sala lectura Drive EV/<tipo>/` (o a la subcarpeta de oferta)
   con **nombre canónico** `AAAA-MM-DD_descripcion.ext` (`descripcion` ≤50 car.,
   **sin PII**). Sin más preguntas.
5. **Escribe los índices** en `01_Procesado/Sala lectura Drive EV/`:
   - `INDICE.md` — por tipo; cada entrada enlaza a la **copia canónica** + mapeo a
     nombre original.
   - `CRONOLOGIA.md` — por fecha ascendente, `s/f` al final.
   - `_MANIFIESTO.md` — por documento: **sha256** · ruta original
     (`00_Input/01_Drive EV/…`) · nombre canónico · tipo · fecha. El `sha256` se
     calcula de los bytes (el `md5` de Drive NO sirve: la traza del caso llavea por
     sha256; ese hash deja abierto el puente con el catálogo).
   Los tres con cabecera `<!-- GENERADO — NO EDITAR A MANO -->`.
6. **Reporta:** nº por categoría, nº a `08. PENDIENTE DE CLASIFICAR`, duplicados.

## Propuesta visual (Paso 2.5)

Tarjeta visual (artefacto HTML; *fallback* markdown compacto), **no un muro de texto**:

a. **Cabecera:** caso + origen (`01_Drive EV`) + aviso «nada copiado aún».
b. **Contadores** por categoría con su nº.
c. **Panel "Requiere tu visto bueno":** SOLO decisiones a revisar — reclasificaciones
   no obvias, identidad/PBC enrutada por parte (y Anexos 1/2 → `06. PBC`), duplicados
   sha256, ficheros sin fecha (`0000-00-00`), docs a `08. PENDIENTE` con motivo,
   doc(s) destacado(s). 1 línea/icono.
d. **Por categoría:** una línea por documento `fecha · nombre-canónico`, agrupando
   repetitivos. **Cada fila enlaza al ORIGINAL** en Drive (`viewUrl` de
   `00_Input/01_Drive EV/…`) para revisar antes de aprobar.
e. **Botones:** «Aprobar y ejecutar» / «Quiero ajustar algo».

Regla de enlaces: en la **propuesta** se enlaza al **original**; en los **índices**
(tras ejecutar) se enlaza a la **copia canónica**.

## Re-aplicación (solo añade; nunca borra)

La skill se re-corre cada vez que entran documentos nuevos del Drive (p. ej. antes de
preparar la demanda). En cada re-corrida:

- **Solo añade.** Compara por **sha256**: lo ya copiado se salta; solo se clasifican y
  copian los documentos **nuevos**. Reporta qué saltó.
- **Conserva la clasificación previa** de los documentos ya conocidos (por sha256,
  según el `_MANIFIESTO.md`): NO los re-clasifica, para que la sala no "baile" entre
  corridas por la varianza del modelo.
- **Nunca borra.** No elimina copias antiguas ni nada de la sala (riesgo en Drive
  compartido + el conector puede no soportar borrado). El crudo de `00_Input` jamás se
  toca.
- **Cambio de reglas de clasificación** (p. ej. nueva taxonomía): es el ÚNICO caso que
  deja copias en carpetas obsoletas. **No se automatiza** — vacía a mano
  `01_Procesado/Sala lectura Drive EV/` (el crudo está intacto) y re-corre desde cero.

## Gotchas

- **Identidad/PBC por parte:** no mandes la identidad a `06. PBC` por defecto;
  vendedor → `01. ACTIVACIÓN`, comprador → `03. OFERTAS`. `06. PBC` sobrevive **solo**
  para los Anexos 1 y 2 del vendedor. La parte se decide **leyendo** el documento.
- **sha256, no md5:** el `_MANIFIESTO.md` guarda el sha256 de los bytes (el conector da
  md5, que no casa con la traza del caso).
- **Sin PII en nombres:** revisa la `descripcion` antes de copiar.
- **Solo `01_Drive EV`:** no proceses `04_Manual` ni otras fuentes en esta corrida.
- **Colisión con el motor local:** el pipeline escribe `01_Procesado/Sala lectura/`
  (por fuente); esta skill usa `Sala lectura Drive EV/` (por tipo): no se pisan. No
  corras el motor sobre el mismo caso a la vez.
- **Carpeta enorme:** avisa y procesa por lotes; deja constancia de lo cubierto.
