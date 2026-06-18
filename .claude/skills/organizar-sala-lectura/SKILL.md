---
name: organizar-sala-lectura
description: >-
  Organiza el intake de Drive de un expediente FeesDefender en una "sala de
  lectura" legible: lee 00_Input/01_Drive EV, clasifica cada fichero en las
  carpetas canónicas de Engel & Völkers (activación, ofertas, arras, facturación,
  PBC, reclamaciones, fotos, pendiente de clasificar) y los copia con nombre
  canónico fecha_tipo_descripcion a 01_Procesado/Sala lectura Drive EV, sin tocar
  el crudo, más INDICE.md, CRONOLOGIA.md y _MANIFIESTO.md. Úsala cuando el usuario
  diga "organiza esta carpeta", "ordena el intake", "monta la sala de lectura",
  "prepara los ficheros para leer" de un caso. NO valora viabilidad (eso es
  triaje-viabilidad) NI genera el informe formal (eso es viabilidad-prerelleno) NI
  mueve/borra el crudo.
metadata:
  rol: output
  naturaleza: atomica
  jurisdiction: ES
  area: [civil, procesal]
  version: "1.0"
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
E&V, con nombre canónico, más índices de navegación. Es la versión **prompt-driven**
del primer paso de la sala de lectura del motor local (misma taxonomía, mismos
nombres), pensada para que cualquier abogado la corra en claude.ai/Cowork sin
instalar nada. **No destructivo: copia, nunca mueve ni borra el crudo.**

## Cuándo se activa

- Disparadores: «organiza esta carpeta», «ordena el intake», «monta la sala de
  lectura», «prepara los ficheros para leer», «esta carpeta de Drive está hecha un lío».

**NO se activa cuando:**

- Hay que **valorar la viabilidad** del caso → `triaje-viabilidad`.
- Hay que producir el **informe formal de viabilidad** → `viabilidad-prerelleno`.

## Entrada y montaje

- Trabaja sobre el **expediente en el Drive del despacho** (no el de Engel).
- **Lee** de `00_Input/01_Drive EV/` (el intake bajado del Drive de Engel). Las demás
  fuentes (`04_Manual`, `05_CRM`, etc.) quedan **fuera de alcance** de esta skill.
- **Escribe** en `01_Procesado/Sala lectura Drive EV/`. Por eso Cowork debe tener
  montada la **raíz del expediente** (o al menos `01_Procesado`), no solo
  `01_Drive EV`: la salida vive fuera de `00_Input`.

## Por qué fuera de 00_Input

`00_Input/` es zona de intake: el pipeline local la escanea entera y los re-pulls del
Drive de Engel la sobrescriben. Si la sala viviera ahí, las copias organizadas se
**re-ingerirían como intake nuevo** (duplicados, re-OCR) y un re-pull las pisaría. Por
eso la salida va a `01_Procesado/` (zona de output), igual que el motor local.

## Qué produce

```
<Expediente (Drive del despacho)>/
├── 00_Input/01_Drive EV/         ← crudo, nombres originales, NO se toca
└── 01_Procesado/
    └── Sala lectura Drive EV/
        ├── INDICE.md · CRONOLOGIA.md · _MANIFIESTO.md
        └── <carpetas canónicas E&V>/   (ver references/taxonomia_ev.md)
```

## Procedimiento

1. **Lista** el contenido de `00_Input/01_Drive EV/` con el conector de Drive.
2. **Clasifica cada fichero:** lee su contenido (vía conector) y decide el **tipo**
   —una de las 8 categorías de `references/taxonomia_ev.md`; lo ambiguo o ilegible
   va a `08. PENDIENTE DE CLASIFICAR`, **nunca se fuerza**— y la **fecha** (del
   contenido; subsidiariamente del nombre; si no consta, `0000-00-00`).
3. **Copia (no mueve)** cada fichero a
   `01_Procesado/Sala lectura Drive EV/<tipo>/` con **nombre canónico**
   `AAAA-MM-DD_tipo_descripcion.ext` (reglas en `references/taxonomia_ev.md`). La
   `descripcion` es un slug ≤50 car. **sin PII** (ni nombres de personas, ni
   DNI/NIE, ni direcciones).
4. **Escribe los índices** en `01_Procesado/Sala lectura Drive EV/`:
   - `INDICE.md` — agrupado por tipo; cada entrada con enlace y mapeo nombre
     original ↔ canónico.
   - `CRONOLOGIA.md` — por fecha ascendente, los `s/f` al final.
   - `_MANIFIESTO.md` — tabla: original · canónico · tipo · fecha · checksum (si el
     conector lo expone).
   Los tres con cabecera `<!-- GENERADO — NO EDITAR A MANO -->`.
5. **Reporta** al usuario: nº por categoría, nº a `08. PENDIENTE DE CLASIFICAR`,
   duplicados detectados.

## Idempotencia

Si `01_Procesado/Sala lectura Drive EV/` ya existe, **no re-dupliques**: compara por
nombre canónico (y por checksum si el conector lo expone), salta lo ya copiado y
reporta qué saltó.

## Gotchas

- **Mover vs copiar:** el conector de Drive puede no soportar *mover* (reparent). El
  default seguro es **copiar** el crudo de `00_Input/01_Drive EV/` a la sala. **Nunca
  borres el crudo.**
- **Sin PII en nombres:** es el delator más fácil; revisa la `descripcion` antes de
  copiar.
- **Solo `01_Drive EV`:** no proceses `04_Manual` ni otras fuentes en esta corrida
  (decisión de alcance). Si el caso las necesita, es otra decisión, no esta skill.
- **Colisión con el motor local:** el pipeline local escribe su propia sala en
  `01_Procesado/Sala lectura/` (por fuente). Esta skill usa una carpeta distinta
  (`Sala lectura Drive EV/`, por tipo): no se pisan. No corras el motor local sobre
  el mismo caso a la vez.
- **Carpeta enorme:** avisa y procesa por lotes; deja constancia de lo cubierto, sin
  truncado silencioso.
