---
name: organizar-sala-lectura
description: >-
  Organiza una carpeta de intake desordenada del Drive del despacho en una "sala
  de lectura" legible: clasifica cada fichero en las carpetas canónicas de Engel &
  Völkers (activación, ofertas, arras, facturación, PBC, reclamaciones, fotos),
  los copia con nombre canónico fecha_tipo_descripcion a 02_Sala lectura/ dejando
  el crudo intacto en 01_Raw/, y genera INDICE.md, CRONOLOGIA.md y un manifiesto.
  Úsala cuando el usuario diga "organiza esta carpeta", "ordena el intake", "monta
  la sala de lectura", "prepara los ficheros para leer" sobre una carpeta de Drive
  de un caso. NO valora viabilidad (eso es triaje-viabilidad) NI genera el informe
  formal (eso es viabilidad-prerelleno) NI mueve/borra el crudo.
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

Convierte una carpeta de intake desordenada del **Drive del despacho** en una
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
- Se trabaja el **expediente local de FeesDefender** (`00_Input`/`01_Procesado`) →
  eso es el motor `core/` en Claude Code, no esta skill.

## Entrada

El usuario indica la **carpeta del caso en el Drive del despacho**. Antes de tocar
nada, confirma que es el Drive del despacho (no el de Engel): aquí se copia y
reorganiza con libertad porque es la copia de trabajo del despacho.

## Qué produce

```
<Carpeta del caso>/
├── 01_Raw/                      ← crudo, nombres originales, NO se toca
└── 02_Sala lectura/
    ├── INDICE.md · CRONOLOGIA.md · _MANIFIESTO.md
    └── <carpetas canónicas E&V>/   (ver references/taxonomia_ev.md)
```

## Procedimiento

1. **Lista** el contenido de la carpeta con el conector de Drive. Si el crudo está
   suelto en la raíz, trátalo como `01_Raw` (ver Gotcha «mover vs copiar»).
2. **Clasifica cada fichero:** lee su contenido (vía conector) y decide el **tipo**
   —una de las 8 categorías de `references/taxonomia_ev.md`; lo ambiguo o ilegible
   va a `08. PENDIENTE`, **nunca se fuerza**— y la **fecha** (del contenido;
   subsidiariamente del nombre; si no consta, `0000-00-00`).
3. **Copia (no mueve)** cada fichero a `02_Sala lectura/<tipo>/` con **nombre
   canónico** `AAAA-MM-DD_tipo_descripcion.ext` (reglas en
   `references/taxonomia_ev.md`). La `descripcion` es un slug ≤50 car. **sin PII**
   (ni nombres de personas, ni DNI/NIE, ni direcciones).
4. **Escribe los índices:**
   - `INDICE.md` — agrupado por tipo; cada entrada con enlace y mapeo nombre
     original ↔ canónico.
   - `CRONOLOGIA.md` — por fecha ascendente, los `s/f` al final.
   - `_MANIFIESTO.md` — tabla: original · canónico · tipo · fecha · checksum (si el
     conector lo expone).
   Los tres con cabecera `<!-- GENERADO — NO EDITAR A MANO -->`.
5. **Reporta** al usuario: nº por categoría, nº a `08. PENDIENTE`, duplicados
   detectados.

## Idempotencia

Si `02_Sala lectura/` ya existe, **no re-dupliques**: compara por nombre canónico (y
por checksum si el conector lo expone), salta lo ya copiado y reporta qué saltó.

## Gotchas

- **Mover vs copiar:** el conector de Drive puede no soportar *mover* (reparent). El
  default seguro es **construir `02_Sala lectura` por copia** y dejar el crudo donde
  esté (o en `01_Raw` si se puede mover sin duplicar). **Nunca borres el crudo.**
- **Sin PII en nombres:** es el delator más fácil; revisa la `descripcion` antes de
  copiar.
- **No es el motor local:** esta skill no toca `00_Input` ni `01_Procesado` del
  expediente FeesDefender; opera solo sobre la carpeta de Drive indicada.
- **Carpeta enorme:** avisa y procesa por lotes; deja constancia de lo cubierto, sin
  truncado silencioso.
